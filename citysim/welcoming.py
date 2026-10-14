"""Execute V3 comparisons without changing the historical simulation artifacts."""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

from .annual_reports import export_annual
from .reports import write_csv, write_json
from .v3 import WelcomingSimulation


def run_job(base, experiment, settings, scenario, policy, seed, days, destination):
    horizon = "annual" if days == settings["days"] else "long"
    settings = copy.deepcopy(settings)
    settings["days"] = days
    s = WelcomingSimulation(base, experiment, settings, scenario, policy, seed, detailed=destination is not None).run()
    result = s.summary()
    result["horizon"] = horizon
    if destination:
        export_annual(s, destination)
        write_json(Path(destination) / "v3_settings.json", settings)
        write_csv(Path(destination) / "newcomers.csv", s.newcomer_cohorts())
        write_json(Path(destination) / "manifest.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(destination).iterdir()) if p.is_file() and p.name != "manifest.json"})
    return result


def report(root, suite, rows):
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r["horizon"], r["policy"], r["scenario"])].append(r)
    aggregate = []
    for (horizon, policy, scenario), group in grouped.items():
        item = {"horizon": horizon, "policy": policy, "scenario": scenario, "runs": len(group), "passed": sum(r["all_criteria_met"] for r in group)}
        for k in ("food_access_rate", "paid_employment_last30", "cash_gini_final", "existing_businesses_operating", "external_cash_final_cents", "city_final_cash_cents"):
            item[k + "_mean"] = statistics.mean(r[k] for r in group)
            item[k + "_min"] = min(r[k] for r in group)
            item[k + "_max"] = max(r[k] for r in group)
        aggregate.append(item)
    write_csv(root / "comparison.csv", aggregate)
    by_key = {(r["horizon"], r["policy"], r["scenario"]): r for r in aggregate}
    lines = ["# City — accueil V3 et prototype simple", "",
             f"{suite['total_runs']} expériences, {suite['total_hourly_checks']:,} contrôles horaires. Comparaison V2/V3 à monnaie initiale identique, puis quatre variantes isolant adaptation, tarifs, délégation et circulation. Horizon principal de 360 jours ; contrôle de durée sur 1080 jours.", "",
             "Le témoin V2 exécute les règles annuelles antérieures ; un test compare ses comptes et séries à ceux du moteur initial. Les résultats historiques sont conservés. Ces comparaisons éprouvent des hypothèses ; elles ne valident ni le plaisir de jeu ni un serveur multijoueur.", "",
             "## Accueil et résilience, toutes les graines", "",
             "| Scénario | V2 emploi payé | V3 emploi payé | V3 alimentation | Commerces initiaux ouverts V3 | Critères V3 satisfaits |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for scenario in suite["experiment"]["scenarios"]:
        a, b = by_key[("annual", "v2", scenario)], by_key[("annual", "v3", scenario)]
        lines.append(f"| {scenario} | {a['paid_employment_last30_mean']:.1%} | {b['paid_employment_last30_mean']:.1%} | {b['food_access_rate_mean']:.2%} | {b['existing_businesses_operating_min']:.0f}–{b['existing_businesses_operating_max']:.0f}/8 | {b['passed']}/{b['runs']} |")
    lines += ["", "![Comparaison V2 et V3](comparison.svg)", "", "## Effet des mécanismes sur la référence", "", "| Politique | Alimentation | Emploi payé | Gini liquidités | Critères |", "| --- | ---: | ---: | ---: | ---: |"]
    for policy in suite["settings"]["policies"]:
        r = by_key[("annual", policy, "reference")]
        lines.append(f"| {policy} | {r['food_access_rate_mean']:.2%} | {r['paid_employment_last30_mean']:.1%} | {r['cash_gini_final_mean']:.3f} | {r['passed']}/{r['runs']} |")
    lines += ["", "## Trois années simulées", "", "| Scénario | Politique | Alimentation | Emploi payé fin | Fonds extérieurs finaux | Critères |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    for scenario in suite["settings"]["long_scenarios"]:
        for policy in ("v2", "v3"):
            r = by_key[("long", policy, scenario)]
            lines.append(f"| {scenario} | {policy} | {r['food_access_rate_mean']:.2%} | {r['paid_employment_last30_mean']:.1%} | {r['external_cash_final_cents_mean']/100:.2f} | {r['passed']}/{r['runs']} |")
    lines += ["", "Le budget extérieur reste fini et aucun financement implicite n'est ajouté. Les aides, investissements et prélèvements sont des transferts ; seules les dotations des arrivants et injections programmées créent de la monnaie. Le niveau de fonds extérieurs et les réserves des ménages sont à suivre au-delà de l'année favorable.", "",
              "## Nouveaux habitants, graine détaillée", "", "| Arrivée | Ménages | Premier salaire, attente maximale | Logement, attente maximale | Réserve médiane fin | Revenu net / dépenses essentielles fin |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    detailed = next(r for r in rows if r["policy"] == "v3" and r["scenario"] == "arrivals" and r["horizon"] == "annual" and r["seed"] == suite["experiment"]["seed"])
    for c in detailed["newcomer_cohorts"]:
        lines.append(f"| J{c['arrival_day']} | {c['households']} | {c['first_wage_wait_max_days']} jours | {c['housing_wait_max_days']} jours | {c['reserve_days_median']:.1f} jours | {c['essential_cover_median']:.2f} |")
    lines += ["", "## Règles proposées et limites", "",
              "- **Croissance progressive :** un poste financé à la fois dans les commerces existants, effectifs et capacité proportionnés à la population active. Les postes municipaux complètent l'accueil. Le dispositif conserve huit commerces au lieu d'ouvrir systématiquement des chaînes concurrentes.",
              "- **Tarifs coopératifs :** prix communs par produit, calculés depuis coûts, intrants, pertes et marge cible de 2 %. Ils restent bornés et évoluent progressivement. Les commandes, budgets, stocks et livraisons déterminent encore les ventes ; aucun débouché artificiel n'est créé.",
              "- **Délégation consentie dans le modèle :** les commerces alimentaires essentiels restent exploités avec une charge de gestion lorsque leur propriétaire s'absente. Le propriétaire en sommeil ne reçoit ni salaire, ni dividende, ni aide. En jeu, la routine sera annoncée et autorisée lors de l'installation du commerce.",
              "- **Circulation :** prélèvement hebdomadaire de 25 % du surplus d'entreprise restant après distribution et réserve de travail ; prélèvement de 2 % des liquidités au-delà de 500 pièces. Ces seuils sont des hypothèses et restent à discuter ; ils déplacent les fonds vers les services publics sans les détruire.",
              "- **Matériaux :** une réserve locale de 24 unités est prioritaire sur les exports pour permettre les aménagements. Les coûts de construction et de personnel restent financés avant application.", "",
              "Les critères nouveaux distinguent une marge initiale d'au moins 5 % pendant le premier mois et, ensuite, un revenu après prélèvements couvrant les dépenses essentielles, avec au moins trois jours de réserve médiane. Ils ajoutent premier salaire sous trois jours, logement sous quatorze jours, accès alimentaire individuel des arrivants à 99 % et maintien d'au moins six commerces initiaux. Les seuils sont provisoires et ne remplacent pas les budgets les plus défavorables.", "",
              "Les ménages, métiers et préférences restent simplifiés. Les tarifs coopératifs limitent la liberté commerciale de cette expérience. Les emplois municipaux représentent des services agrégés et les contrats extérieurs demeurent programmés. Un résultat satisfaisant dans ce cadre ne prouve pas un équilibre avec des comportements humains ou une demande extérieure différente.", "",
              "## Gameplay simple et prototype", "",
              "Deux choix obligatoires : logement et activité. Travail, courses et loyer suivent une routine ; aucun ordre de marché ou réglage fiscal n'est demandé au joueur. Jardin et banc sont des objectifs facultatifs. La carte permet déplacements au clic, flèches et ZQSD. Le carnet expose portefeuille, budget prévu et bilan groupé de la journée.", "",
              "Le prototype utilise réellement la V3 et des transactions enregistrées dans SQLite, rejouées au redémarrage. Les actions répétées ne sont pas exécutées deux fois. La carte publique n'expose pas les budgets des autres habitants. Le personnage local est préapprouvé ; une véritable whitelist multijoueur reste une étape distincte.", "",
              "Les journées n'avancent que dans un onglet actif, avec pause et avance manuelle. Hors connexion, aucune journée ni charge n'est ajoutée au prototype. Ce tempo d'essai ne représente pas encore le serveur persistant de la ville communautaire.", "",
              "La restriction de l'environnement empêche l'ouverture de ports TCP et le lancement de Chromium. Le parcours a été exécuté avec le vrai script d'interface, un DOM de test, le vrai gestionnaire HTTP, le modèle Python et SQLite. La vérification visuelle de la mise en page dans un navigateur reste à faire sur la machine qui lance le jeu. L'aperçu de carte est rendu à partir des opérations du canvas ; ce n'est pas une capture d'écran du navigateur.", "",
              "![Aperçu du dessin de la carte](../prototype/map-preview.png)", "",
              "## Reproduire", "", "```bash", f"python3 -m citysim.welcoming --config config/v3.json --output results/v3-simulation --seeds {suite['additional_seeds']} --workers {suite['workers']}", "```", "", "```bash", "python3 -m citygame --port 8092", "```", "",
              "Ouvrir `http://127.0.0.1:8092` sur la machine qui exécute la commande. Les sauvegardes locales sont dans `data/prototype.sqlite`, les tests de parcours dans `results/prototype`. Les calculs annuels et de longue durée sont exportés dans des dossiers distincts `annual` et `long`, avec journaux complets compressés pour la graine de référence."]
    (root / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    plot(root, aggregate, suite)


def plot(root, aggregate, suite):
    import os, tempfile
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "city-matplotlib-cache"))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    rows = {(r["policy"], r["scenario"]): r for r in aggregate if r["horizon"] == "annual"}
    names = list(suite["experiment"]["scenarios"])
    fig, axes = plt.subplots(1, 3, figsize=(18, 9), layout="constrained")
    for ax, metric, title, scale in zip(axes, ("food_access_rate", "paid_employment_last30", "existing_businesses_operating"),
                                       ("Besoins alimentaires servis (%)", "Emploi payé en fin d'année (%)", "Commerces initiaux en activité"), (100, 100, 1)):
        for policy, shift, color in (("v2", -.18, "#987457"), ("v3", .18, "#4d7756")):
            values = [rows[(policy, n)][metric + "_mean"] * scale for n in names]
            ax.barh([i + shift for i in range(len(names))], values, height=.32, color=color, label=policy)
        ax.set_yticks(range(len(names)), names)
        ax.invert_yaxis()
        ax.set_title(title)
        ax.set_xlim(0, 8 if metric == "existing_businesses_operating" else 100)
        ax.grid(axis="x", alpha=.2)
    fig.suptitle("City — accueil V3 : nourriture, revenu payé et commerces conservés", fontsize=16)
    axes[0].legend(loc="lower left")
    fig.savefig(root / "comparison.svg", metadata={"Date": None})
    fig.savefig(root / "comparison.png", dpi=140)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="V3 City : accueil, viabilité et gameplay simple")
    parser.add_argument("--config", type=Path, default=Path("config/v3.json"))
    parser.add_argument("--output", type=Path, default=Path("results/v3-simulation"))
    parser.add_argument("--seeds", type=int)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--days", type=int)
    parser.add_argument("--long-seeds", type=int)
    args = parser.parse_args()
    settings = json.loads(args.config.read_text())
    epath = args.config.parent / settings["experiment_config"]
    experiment = json.loads(epath.read_text())
    base = json.loads((epath.parent / experiment["base_config"]).read_text())
    seeds = settings["additional_seeds"] if args.seeds is None else args.seeds
    workers = settings["workers"] if args.workers is None else args.workers
    days = settings["days"] if args.days is None else args.days
    long_seeds = settings["long_additional_seeds"] if args.long_seeds is None else args.long_seeds
    if min(seeds, long_seeds) < 0 or not 1 <= workers <= 16 or days <= 0:
        parser.error("Durée/processus positifs et graines supplémentaires ≥0 requis")
    settings["days"] = days
    args.output.mkdir(parents=True, exist_ok=True)
    jobs = []
    cases = [(p, s) for p in settings["main_policies"] for s in experiment["scenarios"]]
    cases += [(p, "reference") for p in settings["policies"] if p not in settings["main_policies"]]
    for offset in range(seeds + 1):
        jobs.extend((s, p, experiment["seed"] + offset, days, str(args.output / "annual" / p / s) if offset == 0 else None) for p, s in cases)
    long_days = settings["long_days"] if args.days is None else days + 1
    for offset in range(long_seeds + 1):
        jobs.extend((s, p, experiment["seed"] + offset, long_days, str(args.output / "long" / p / s) if offset == 0 else None) for p in settings["main_policies"] for s in settings["long_scenarios"])
    rows = []
    source = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob("*.py")}
    print(f"{len(jobs)} expériences ; {workers} processus ; horizons {days}/{long_days} jours", flush=True)
    with (args.output / "runs.jsonl").open("w", encoding="utf-8") as stream:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(run_job, base, experiment, settings, scenario, policy, seed, duration, dest) for scenario, policy, seed, duration, dest in jobs]
            for future in concurrent.futures.as_completed(futures):
                row = future.result()
                rows.append(row)
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                if row["seed"] == experiment["seed"]:
                    print(f"{row['horizon']}/{row['policy']}/{row['scenario']}: nourriture={row['food_access_rate']:.2%}, emploi={row['paid_employment_last30']:.1%}, critères={row['all_criteria_met']}", flush=True)
                if len(rows) % 10 == 0 or len(rows) == len(jobs):
                    write_json(args.output / "progress.json", {"completed": len(rows), "total": len(jobs)})
                    print(f"Progression : {len(rows)}/{len(jobs)}", flush=True)
    rows.sort(key=lambda r: (r["horizon"], r["policy"], r["scenario"], r["seed"]))
    (args.output / "runs.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    suite = {"model": "welcoming-v3", "settings": settings, "experiment": experiment, "base_config": base,
             "total_runs": len(rows), "total_hourly_checks": sum(r["checks"] for r in rows),
             "additional_seeds": seeds, "long_additional_seeds": long_seeds, "workers": workers,
             "source_sha256": source, "detailed_summaries": [r for r in rows if r["seed"] == experiment["seed"]]}
    write_json(args.output / "suite.json", suite)
    report(args.output, suite, rows)
    print(args.output / "report.md", flush=True)


if __name__ == "__main__":
    main()
