from __future__ import annotations

import csv
import gzip
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

from .reports import export_run, write_csv, write_json


def compress_file(path):
    with path.open("rb") as source, path.with_suffix(path.suffix + ".gz").open("wb") as target:
        with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as compressed:
            while chunk := source.read(1024 * 1024):
                compressed.write(chunk)
    path.unlink()


def export_annual(s, destination):
    dest = Path(destination)
    export_run(s, dest)
    write_json(dest / "experiment.json", s.experiment)
    write_json(dest / "initial_accounts.json", s.ledger.initial_balances)
    write_json(dest / "visitors.json", s.visitor_history)
    write_csv(dest / "household_daily.csv", s.household_daily)
    monthly = []
    for start in range(0, len(s.daily), 30):
        group = s.daily[start:start + 30]
        monthly.append({
            "month": start // 30 + 1, "day_start": group[0]["day"], "day_end": group[-1]["day"],
            "food_access": sum(r["food_units_served"] for r in group) / max(1, sum(r["active_population"] * 2 for r in group)),
            "paid_employment": statistics.mean(r["paid_employment_rate"] for r in group),
            "city_income_cents": sum(r["city_income_cents"] for r in group),
            "city_spending_cents": sum(r["city_spending_cents"] for r in group),
            "city_cash_final_cents": group[-1]["city_cash_cents"], "unhoused_final": group[-1]["unhoused"],
            "cash_gini_final": group[-1]["cash_gini_residents"], "asset_gini_final": group[-1]["asset_gini_residents"],
        })
    write_csv(dest / "monthly.csv", monthly)
    cohorts = defaultdict(list)
    for h in s.profiles():
        if h["household"] in s.tourists:
            continue
        group = "PNJ initiaux" if h["household"].startswith("npc") else f"arrivants J{h['arrival_day']}" if h["household"].startswith("new") else "joueurs initiaux"
        cohorts[group].append(h)
    write_csv(dest / "cohorts.csv", [{
        "cohort": name, "households": len(group),
        "cash_median_cents": statistics.median(h["cash_final_cents"] for h in group),
        "cash_min_cents": min(h["cash_final_cents"] for h in group),
        "food_missing_units": sum(h["food_missing_units"] for h in group),
        "unhoused": sum(not h["housed"] for h in group),
        "housing_wait_median_days": statistics.median(h["days_to_housing"] for h in group if h["days_to_housing"] is not None) if any(h["days_to_housing"] is not None for h in group) else None,
        "essential_to_income_median": statistics.median(h["essential_to_income_ratio"] for h in group if h["essential_to_income_ratio"] is not None) if any(h["essential_to_income_ratio"] is not None for h in group) else None,
    } for name, group in cohorts.items()])
    firms = list(csv.DictReader((dest / "businesses.csv").open(encoding="utf-8")))
    for row in firms:
        row["cash_initial_cents"] = s.starting_firm_cash[row["id"]]
        row["cash_change_cents"] = int(row["cash_final_cents"]) - s.starting_firm_cash[row["id"]]
    write_csv(dest / "businesses.csv", firms)
    write_json(dest / "flows.json", dict(s.ledger.reason_totals))
    for name in ("ledger.csv", "hourly.csv", "household_daily.csv"):
        compress_file(dest / name)
    write_json(dest / "manifest.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir()) if p.is_file() and p.name != "manifest.json"})


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["policy"], row["scenario"])].append(row)
    result = []
    metrics = ["food_access_rate", "paid_employment_last30", "cash_gini_final", "asset_gini_final", "city_final_cash_cents",
               "unhoused_final", "critical_food_gap_max_days", "municipal_unpaid_wages_cents", "external_cash_final_cents"]
    for (policy, scenario), group in groups.items():
        out = {"policy": policy, "scenario": scenario, "runs": len(group), "all_criteria_met_runs": sum(r["all_criteria_met"] for r in group)}
        for key in metrics:
            values = [r[key] for r in group]
            out.update({key + "_mean": statistics.mean(values), key + "_minimum": min(values), key + "_maximum": max(values)})
        result.append(out)
    return result


def paired_results(rows, experiment):
    indexed = {(r["policy"], r["scenario"], r["seed"]): r for r in rows}
    comparisons = []
    for scenario in experiment["scenarios"]:
        seeds = sorted(seed for policy, name, seed in indexed if policy == "legacy" and name == scenario)
        group = []
        for seed in seeds:
            a, b = indexed[("legacy", scenario, seed)], indexed[("balanced", scenario, seed)]
            group.append({"seed": seed, "food_delta": b["food_access_rate"] - a["food_access_rate"],
                          "employment_delta": b["paid_employment_last30"] - a["paid_employment_last30"],
                          "cash_gini_delta": b["cash_gini_final"] - a["cash_gini_final"],
                          "city_cash_delta_cents": b["city_final_cash_cents"] - a["city_final_cash_cents"]})
        if group:
            comparisons.append({"scenario": scenario, "paired_runs": len(group), **{
                key + suffix: fn(r[key] for r in group) for key in ("food_delta", "employment_delta", "cash_gini_delta", "city_cash_delta_cents")
                for suffix, fn in (("_mean", statistics.mean), ("_minimum", min), ("_maximum", max))}})
    return comparisons


def format_money(cents):
    return f"{cents / 100:,.2f}".replace(",", " ")


def write_report(destination, suite, rows):
    dest = Path(destination)
    groups = aggregate(rows)
    write_csv(dest / "comparison.csv", groups)
    paired = paired_results(rows, suite["experiment"])
    write_csv(dest / "paired_comparison.csv", paired)
    seed = suite["experiment"]["seed"]
    detailed = {(r["policy"], r["scenario"]): r for r in rows if r["seed"] == seed}
    a, b = detailed[("legacy", "reference")], detailed[("balanced", "reference")]
    experiment = suite["experiment"]
    lines = ["# City — simulation annuelle approfondie", "",
             f"{experiment['days']} jours, pas horaire, {len(experiment['scenarios'])} scénarios, deux ensembles de règles et cinq comparaisons de mécanismes isolés sur la référence. **{len(rows)} expériences**, **{suite['total_hourly_checks']:,} contrôles horaires**, graine détaillée {seed} et {suite['additional_seeds']} graines supplémentaires par cas.", "",
             "La première simulation de 90 jours est conservée dans `results/first-simulation`. Ici, `legacy` reprend ses règles dans un monde enrichi par les saisons, les visiteurs, les achats d'aménagement et une stratégie opportuniste bornée. `balanced` teste des changements de règles sur le même modèle annuel. Comparer directement les chiffres v1 et v2 confondrait ces changements de périmètre.", "",
             "## Résultat principal", "",
             f"Sur la graine détaillée, la référence `legacy` sert {a['food_access_rate']:.2%} des besoins et accumule {format_money(a['municipal_unpaid_wages_cents'])} de salaires municipaux non versés. L'ensemble `balanced` sert {b['food_access_rate']:.2%}, avec {format_money(b['municipal_unpaid_wages_cents'])} de salaires municipaux non versés, {format_money(b['city_final_cash_cents'])} en mairie, et un Gini des liquidités de {b['cash_gini_final']:.3f}.", "",
             "Les résultats des arrivées et des crises doivent être évalués séparément : construire des logements et ouvrir des postes ne garantit ni la solvabilité des entreprises ni un revenu effectivement payé. Les critères chiffrés ci-dessous sont des hypothèses de cette expérience, pas des objectifs de jeu validés.", "",
             "## Comparaison sur toutes les graines", "", "Les valeurs indiquent moyenne et intervalle minimum–maximum. Les emplois sont mesurés en équivalents de journées effectivement rémunérées pendant les trente derniers jours, divisés par les résidents actifs. Le nombre de postes attribués est exporté séparément.", "",
             "| Scénario | Nourriture legacy | Nourriture balanced | Emploi payé balanced | Sans logement balanced | Critères tous satisfaits balanced |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    indexed = {(g["policy"], g["scenario"]): g for g in groups}
    for name in experiment["scenarios"]:
        old, new = indexed[("legacy", name)], indexed[("balanced", name)]
        lines.append(f"| {name} | {old['food_access_rate_mean']:.2%} | {new['food_access_rate_mean']:.2%} ({new['food_access_rate_minimum']:.2%}–{new['food_access_rate_maximum']:.2%}) | {new['paid_employment_last30_mean']:.1%} | {new['unhoused_final_minimum']:.0f}–{new['unhoused_final_maximum']:.0f} | {new['all_criteria_met_runs']}/{new['runs']} |")
    lines += ["", "![Comparaison des règles](comparison.svg)", "", "## Trajectoires dans l'année", "", "![Trajectoires des principaux scénarios](trajectories.svg)", "", "## Ce qu'apportent les mécanismes isolés", "", "Les cinq variantes n'activent qu'une famille de mécanismes. Leurs effets ne s'additionnent pas nécessairement ; les interactions sont testées par l'ensemble complet.", "", "| Politique, référence | Nourriture moyenne | Emploi payé fin moyen | Mairie finale moyenne | Gini liquidités moyen |", "| --- | ---: | ---: | ---: | ---: |"]
    for policy in experiment["policies"]:
        r = indexed[(policy, "reference")]
        lines.append(f"| {policy} | {r['food_access_rate_mean']:.2%} | {r['paid_employment_last30_mean']:.1%} | {format_money(r['city_final_cash_cents_mean'])} | {r['cash_gini_final_mean']:.3f} |")
    lines += ["", "- **Stockage :** réserve cible d'un jour, pertes municipales divisées par quatre, prestation de conservation payante à sept unités par jour. Si elle n'est pas intégralement payée, la conservation redevient ordinaire.",
              "- **Prix publics :** coût de production et demande visible, stocks agrégés des vendeurs, marge cible de 8 %, variation journalière limitée à 5 % et borne de prix existante. Les coûts du travail et des intrants restent visibles ; la recette 1:1 est conservée.",
              "- **Finances :** volume de contrats extérieurs adapté au déficit observé et à une cible de trésorerie, plafond d'achat extérieur, aide personnelle plafonnée à trente jours et budget municipal de secours. Une subvention ne crée pas de monnaie.",
              "- **Croissance :** priorité aux matériaux des chantiers, financement préalable conservant une réserve salariale, chaînes alimentaires collectives avec capital réellement transféré, deux emplois publics supplémentaires par projet de logement. Les entreprises insolvables peuvent vendre leur stock et reprendre si leur trésorerie le permet.",
              "- **Répartition :** partage hebdomadaire de 30 % du surplus disponible avec les salariés, dividende propriétaire plafonné à 50 % de ce surplus, réserve de travail maintenue, taxe hebdomadaire de 1 % des liquidités au-delà de 2 000 unités, au plus deux entreprises contrôlées initialement par un joueur. Ces réglages restent à comparer avec d'autres distributions.", "",
              "## Incidents, causes et personnes touchées", ""]
    for name in experiment["scenarios"]:
        r = detailed[("balanced", name)]
        folder = dest / "balanced" / name
        events = json.loads((folder / "events.json").read_text())
        closed = [e for e in events if e["type"] == "business_insolvent"]
        failures = [k for k, ok in r["criteria"].items() if not ok]
        desc = f"**{name} :** alimentation {r['food_access_rate']:.2%}, plus longue séquence sous 99 % : {r['critical_food_gap_max_days']} jours ; emploi payé final {r['paid_employment_last30']:.1%}."
        if name in ("arrivals", "combined"):
            desc += f" {r['resident_population_final']} résidents, {r['projects_completed']} projets de logements et {r['growth_bundles_completed']} chaînes alimentaires ouverts ; {r['unhoused_final']} ménages restent sans logement."
        if closed:
            desc += " Arrêts faute de liquidités : " + "; ".join(f"{e['description'].split(' ne peut')[0]} à J{e['day']} ({format_money(e['cash_cents'])})" for e in closed) + "."
        if r["recoveries"]:
            desc += " Récupérations après événement : " + "; ".join(f"{x['kind']} fin J{x['end']} : {str(x['days']) + ' jours' if x['days'] is not None else 'aucune fenêtre de sept jours avec alimentation ≥99 % et emploi payé ≥80 % avant le prochain événement ou la fin'}" for x in r["recoveries"]) + "."
        if name.endswith("abuse"):
            desc += f" {r['rejected_abuses']} opérations abusives refusées avant mutation."
        desc += " Critères non satisfaits : " + (", ".join(failures) if failures else "aucun") + "."
        lines += [desc, ""]
    if (dest / "balanced/arrivals/cohorts.csv").exists():
        lines += ["## Arrivants et anciens, graine détaillée", "", "Les cohortes ne sont pas agrégées en un seul joueur moyen. La part des dépenses essentielles dans le revenu est la médiane des rapports individuels ; elle peut dépasser 100 % quand la dotation initiale finance la consommation.", "", "| Cohorte | Ménages | Liquidités médianes | Liquidités minimales | Portions manquantes cumulées | Sans logement |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for r in csv.DictReader((dest / "balanced/arrivals/cohorts.csv").open(encoding="utf-8")):
            lines.append(f"| {r['cohort']} | {r['households']} | {format_money(float(r['cash_median_cents']))} | {format_money(float(r['cash_min_cents']))} | {r['food_missing_units']} | {r['unhoused']} |")
    lines += ["", "## Comptabilité, dépendance extérieure et critères", "",
              f"La référence `balanced` reçoit {format_money(b['external_net_transfer_to_city_economy_cents'])} nets de l'extérieur sur l'année. Son compte extérieur termine à {format_money(b['external_cash_final_cents'])} ; la monnaie initiale du monde inclut ce compte. Une ville stable grâce à ces échanges n'est pas autonome. Les visiteurs reçoivent un budget transféré, puis rendent les fonds inutilisés ; ni PNJ ni marché ne disposent d'un budget infini.", "",
              f"Critères provisoires : alimentation annuelle ≥{experiment['criteria']['food_access_minimum']:.0%}, pas plus de {experiment['criteria']['food_gap_max_consecutive_days']} jours consécutifs sous 99 %, emploi payé final ≥{experiment['criteria']['paid_employment_last30_minimum']:.0%}, aucun ménage sans logement, aucun salaire municipal non payé, sept jours de réserve salariale municipale, Gini des liquidités ≤{experiment['criteria']['cash_gini_maximum']}. Le Gini élargi ajoute trésorerie et inventaire des entreprises détenues, valorisé aux prix de départ ; il ne valorise pas le foncier ni les bâtiments.", "",
              "Les conservation monétaire et matière sont contrôlées à chaque heure. Les commandes répétés, réservations, bénéficiaires municipaux, budgets et conflits d'intérêt restent contrôlés avant application. Les arrondis du demi-salaire horaire ne sont pas assimilés à des impayés. Les variantes à journal réduit appliquent les mêmes règles ; leur égalité avec une exécution détaillée est testée.", "",
              "## Limites du modèle", "",
              "- Un ménage reste une personne. Les résidents actifs consomment deux portions par jour ; qualité artisanale, santé, vieillissement, familles et relations ne sont pas simulés.",
              "- Les stratégies représentées sont simples : routines, propriété, budget d'aménagement, contribution du coopérateur et tentative de stockage/revente de l'opportuniste. Elles ne prédisent ni coalitions, ni décisions d'une communauté humaine.",
              "- Les élus sont représentés par des approbations programmées, pas des élections. Les tentatives d'abus testent les règles locales ; elles ne constituent pas un audit de sécurité d'un serveur concurrent.",
              "- La modernisation finance une capacité supplémentaire et conserve les emplois et recettes. Elle ne permet pas de conclure sur la disparition de l'artisanat. La crypto reste séparée et n'est pas incluse dans cette expérience.",
              "- Les prix restent plafonnés, le marché expire ses ordres à chaque lot, et l'extérieur conserve une demande limitée. Un déficit durable peut venir de ces choix autant que d'une mauvaise capacité de production.",
              "- Les aides et votes simulés sont visibles, mais une aide personnelle consommée n'est jamais revendable. En sommeil, ni salaire, dividende, partage de profit, aide ni loyer ; les logements sont protégés.",
              "- Les mêmes graines appairent calendrier et météo. Les transactions et pertes peuvent diverger lorsque les règles changent ; les intervalles donnés sont des plages de simulation, pas des intervalles de confiance.", "",
              "## Prochaine expérience utile", "", "Revoir la viabilité des chaînes collectives et le financement du revenu des arrivants, puis comparer ces changements sur les mêmes graines. Ne pas valider un jeu sur la seule référence : utiliser les cohortes, les journées réellement payées, le temps de récupération et les budgets après crise.", "",
              "## Reproduire et lire les exports", "", "```bash", f"python3 -m citysim.annual --config config/extended.json --output results/annual-simulation --seeds {suite['additional_seeds']} --workers {suite['workers']}", "```", "",
              "Chaque dossier `politique/scénario` contient configuration, expérience, séries quotidiennes et mensuelles, cohortes, profils, entreprises, visiteurs, événements, audit et empreintes. Les journaux monétaires, indicateurs horaires et trajectoires individuelles sont des CSV gzip (`*.csv.gz`). `runs.jsonl` contient toutes les graines ; `comparison.csv` et `paired_comparison.csv` comparent les résultats. `verification.json` documente les contrôles indépendants des exports. La vitesse d'exécution du programme ne modifie pas les délais d'absence exprimés en temps réel."]
    (dest / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_results(destination, rows):
    import os
    import tempfile
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "city-matplotlib-cache"))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    dest = Path(destination)
    plt.rcParams.update({"svg.hashsalt": "city-annual", "axes.spines.top": False, "axes.spines.right": False, "font.size": 10})
    groups = {(g["policy"], g["scenario"]): g for g in aggregate(rows)}
    names = [name for policy, name in groups if policy == "legacy"]
    fig, axes = plt.subplots(1, 3, figsize=(18, 9), layout="constrained")
    for ax, metric, title, scale in zip(axes, ("food_access_rate", "paid_employment_last30", "cash_gini_final"),
                                       ("Besoins alimentaires servis", "Emploi effectivement payé, fin", "Inégalité des liquidités"), (100, 100, 1)):
        for policy, shift, color in (("legacy", -.18, "#9d7352"), ("balanced", .18, "#286b83")):
            values = [groups[(policy, name)][metric + "_mean"] * scale for name in names]
            low = [v - groups[(policy, name)][metric + "_minimum"] * scale for v, name in zip(values, names)]
            high = [groups[(policy, name)][metric + "_maximum"] * scale - v for v, name in zip(values, names)]
            ax.barh([i + shift for i in range(len(names))], values, height=.32, color=color, label=policy, xerr=[low, high], error_kw={"elinewidth": 1, "capsize": 2})
        ax.set_yticks(range(len(names)), names)
        ax.set_title(title)
        ax.invert_yaxis()
        ax.set_xlim(0, scale)
        ax.grid(axis="x", alpha=.2)
    fig.suptitle("City — comparaison annuelle, moyennes et plages entre graines", fontsize=16)
    axes[0].legend(loc="lower left")
    for suffix in ("svg", "png"):
        fig.savefig(dest / f"comparison.{suffix}", dpi=140, metadata={"Date": None} if suffix == "svg" else {})
    plt.close(fig)
    selected = ["reference", "arrivals", "combined", "shortage", "transport_breakdown", "external_trade_stop"]
    plots = [("Alimentation servie (%)", "food_access_rate", 100), ("Mairie (monnaie fictive)", "city_cash_cents", .01),
             ("Emploi payé (%)", "paid_employment_rate", 100), ("Résidents sans logement", "unhoused", 1),
             ("Gini des liquidités", "cash_gini_residents", 1), ("Panier proposé (monnaie fictive)", "basket_price_cents", .01)]
    fig, axes = plt.subplots(3, 2, figsize=(15, 13), layout="constrained")
    for name in selected:
        data = list(csv.DictReader((dest / "balanced" / name / "daily.csv").open(encoding="utf-8")))
        for ax, (title, key, scale) in zip(axes.flat, plots):
            ax.plot([int(r["day"]) for r in data], [float(r[key]) * scale for r in data], label=name, linewidth=1.5, alpha=.8)
            ax.set(title=title, xlabel="Jour simulé")
            ax.grid(alpha=.2)
    for ax in axes.flat:
        ax.set_ylim(bottom=0)
    axes.flat[0].set_ylim(0, 105)
    axes.flat[2].set_ylim(0, 105)
    axes.flat[4].set_ylim(0, 1)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncols=3, frameon=False)
    fig.suptitle("City — trajectoires de l'ensemble balanced, graine détaillée", fontsize=16)
    for suffix in ("svg", "png"):
        fig.savefig(dest / f"trajectories.{suffix}", dpi=140, metadata={"Date": None} if suffix == "svg" else {})
    plt.close(fig)
    return True
