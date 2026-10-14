"""Attribute executed escrow payments to their payer and explain company cash flows."""

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from .reports import write_csv, write_json


def analyze_case(folder):
    businesses = {r["id"]: r for r in csv.DictReader((folder / "businesses.csv").open(encoding="utf-8"))}
    events = json.loads((folder / "events.json").read_text(encoding="utf-8"))
    first_failure = {e["description"].split(" ne peut")[0]: e["day"] for e in events if e["type"] == "business_insolvent"}
    annual = defaultdict(Counter)
    initial_accounts = json.loads((folder / "initial_accounts.json").read_text(encoding="utf-8"))
    before_failure = defaultdict(Counter)
    monthly = defaultdict(Counter)
    escrow_owner, escrow_cash = {}, Counter()
    with gzip.open(folder / "ledger.csv.gz", "rt", encoding="utf-8", newline="") as stream:
        for r in csv.DictReader(stream):
            cents = int(r["cents"])
            source, target, reason = r["source"], r["target"], r["reason"]
            day = int(r["hour"]) // 24 + 1
            if reason == "order_reservation":
                escrow_owner[target] = source
                escrow_cash[target] += cents
                continue
            payer = escrow_owner.get(source, source)
            if source in escrow_owner:
                escrow_cash[source] -= cents
                assert escrow_cash[source] >= 0
                if escrow_cash[source] == 0:
                    del escrow_owner[source]
                    del escrow_cash[source]
            if reason == "order_refund":
                continue
            entries = []
            if target in businesses:
                key = "revenue" if reason.startswith("market:") or reason in ("material_export", "construction_materials", "growth_materials") else "capital_received" if reason == "business_starting_capital" else "other_incoming"
                entries.append((target, key))
            if payer in businesses:
                key = "input_purchases" if reason.startswith("market:") else {
                    "wage": "wages", "sales_tax": "taxes", "business_maintenance": "maintenance", "delivery": "delivery",
                    "dividend": "owner_dividends", "worker_profit_share": "worker_profit_share", "technology_investment": "technology_investment",
                }.get(reason, "other_outgoing")
                entries.append((payer, key))
            for business, key in entries:
                annual[business][key] += cents
                monthly[(business, (day - 1) // 30 + 1)][key] += cents
                if business in first_failure and first_failure[business] - 30 <= day < first_failure[business]:
                    before_failure[business][key] += cents
    assert not escrow_owner
    rows = []
    fields = ("revenue", "capital_received", "other_incoming", "input_purchases", "wages", "taxes", "maintenance", "delivery", "owner_dividends", "worker_profit_share", "technology_investment", "other_outgoing")
    for id, b in businesses.items():
        flow = annual[id]
        incoming = sum(flow[k] for k in ("revenue", "capital_received", "other_incoming"))
        outgoing = sum(flow[k] for k in fields if k not in ("revenue", "capital_received", "other_incoming"))
        assert initial_accounts.get(id, 0) + incoming - outgoing == int(b["cash_final_cents"]), id
        for period, flow in [("year", annual[id]), ("30_days_before_first_failure", before_failure[id])] + [(f"month_{month}", values) for (business, month), values in sorted(monthly.items()) if business == id]:
            if period == "30_days_before_first_failure" and id not in first_failure:
                continue
            operating_costs = sum(flow[k] for k in ("input_purchases", "wages", "taxes", "maintenance", "delivery", "other_outgoing"))
            rows.append({"business": id, "product": b["product"], "period": period,
                         "first_failure_day": first_failure.get(id), "cash_final_cents": int(b["cash_final_cents"]),
                         "operating_margin_cents": flow["revenue"] - operating_costs,
                         **{k + "_cents": flow[k] for k in fields}})
    return rows


def main():
    parser = argparse.ArgumentParser(description="Analyser les recettes, charges et réserves des entreprises City")
    parser.add_argument("--results", type=Path, default=Path("results/annual-simulation"))
    parser.add_argument("--append-report", action="store_true", help="Ajouter les diagnostics au rapport existant")
    args = parser.parse_args()
    cases = [("balanced", name) for name in ("reference", "arrivals", "combined", "absence")] + [("legacy", "arrivals")]
    rows = []
    for policy, scenario in cases:
        folder = args.results / policy / scenario
        rows += [{"policy": policy, "scenario": scenario, **r} for r in analyze_case(folder)]
    write_csv(args.results / "financial_diagnostics.csv", rows)
    lines = ["## Diagnostic financier des entreprises", "",
             "Les paiements réellement exécutés depuis les comptes de réservation sont attribués à leur acheteur. La marge de trésorerie ci-dessous est la recette moins achats d'intrants, salaires, taxes, entretien, livraison et autres charges ordinaires, avant dividendes, partage de profits et investissement technologique. Les apports de capital sont séparés des recettes. Ce bilan utilise les achats de stocks, sans valoriser les variations d'inventaire : il ne constitue pas un compte de résultat comptable complet.", "",
             "| Arrivées, balanced | Premier arrêt | Recettes des 30 jours précédents | Achats d'intrants | Salaires | Autres charges | Marge de trésorerie avant distributions |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    failing = [r for r in rows if r["policy"] == "balanced" and r["scenario"] == "arrivals" and r["period"] == "30_days_before_first_failure"]
    for r in failing:
        other = sum(r[k + "_cents"] for k in ("taxes", "maintenance", "delivery", "other_outgoing"))
        lines.append(f"| {r['business']} | J{r['first_failure_day']} | {r['revenue_cents']/100:.2f} | {r['input_purchases_cents']/100:.2f} | {r['wages_cents']/100:.2f} | {other/100:.2f} | {r['operating_margin_cents']/100:.2f} |")
    losses = sum(r["operating_margin_cents"] < 0 for r in failing)
    lines += ["", f"{losses} des {len(failing)} entreprises qui s'arrêtent dans ce scénario ont une marge de trésorerie négative sur les trente jours précédents. L'ouverture de capacités collectives modifie la répartition des ventes et des coûts ; les effectifs et les plafonds de prix ne s'ajustent pas automatiquement à cette nouvelle concurrence. Les apports initiaux peuvent masquer ce déséquilibre pendant plusieurs semaines.", "",
              "Les causes immédiates d'arrêt restent le financement insuffisant d'une journée de salaires et d'entretien. Ces bilans distinguent recettes, achats de stocks, distributions et investissement ; chaque solde final est vérifié contre les comptes exportés. Ils n'isolent pas à eux seuls l'effet causal d'un paramètre. Les comparaisons de règles et les trajectoires individuelles restent nécessaires.", "",
              "Le fichier `financial_diagnostics.csv` contient aussi les marges mensuelles et annuelles de la référence, des arrivées, des absences et du scénario combiné. Les montants du tableau sont exprimés en monnaie fictive."]
    diagnostic = "\n".join(lines) + "\n"
    (args.results / "financial_diagnostics.md").write_text(diagnostic, encoding="utf-8")
    if args.append_report:
        report = args.results / "report.md"
        text = report.read_text(encoding="utf-8")
        marker = "\n## Diagnostic financier des entreprises\n"
        if marker in text:
            text = text.split(marker, 1)[0].rstrip() + "\n"
        report.write_text(text + "\n" + diagnostic, encoding="utf-8")
    write_json(args.results / "financial_diagnostics_meta.json", {
        "cases": cases, "rows": len(rows), "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "csv_sha256": hashlib.sha256((args.results / "financial_diagnostics.csv").read_bytes()).hexdigest(),
    })
    print(args.results / "financial_diagnostics.md")


if __name__ == "__main__":
    main()
