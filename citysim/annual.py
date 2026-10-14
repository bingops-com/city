from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import platform
from pathlib import Path

from .annual_reports import export_annual, plot_results, write_report
from .extended import ExtendedSimulation
from .reports import write_json


def run_job(base, experiment, scenario, policy, seed, output):
    sim = ExtendedSimulation(base, experiment, scenario, policy, seed, detailed=output is not None).run()
    result = sim.summary()
    if output is not None:
        export_annual(sim, output)
    return result


def main():
    parser = argparse.ArgumentParser(description="Simulation annuelle approfondie de City")
    parser.add_argument("--config", type=Path, default=Path("config/extended.json"))
    parser.add_argument("--output", type=Path, default=Path("results/annual-simulation"))
    parser.add_argument("--seeds", type=int, help="Graines supplémentaires par cas")
    parser.add_argument("--workers", type=int, help="Processus CPU pour les expériences indépendantes")
    parser.add_argument("--days", type=int, help="Durée alternative pour un essai local")
    args = parser.parse_args()
    try:
        experiment = json.loads(args.config.read_text(encoding="utf-8"))
        base_path = args.config.parent / experiment["base_config"]
        base = json.loads(base_path.read_text(encoding="utf-8"))
        seeds = experiment["additional_seeds"] if args.seeds is None else args.seeds
        workers = experiment["workers"] if args.workers is None else args.workers
        if seeds < 0 or workers < 1 or workers > 16:
            parser.error("Graines ≥0 et processus entre 1 et 16 requis")
        if args.days is not None:
            experiment["days"] = args.days
        ExtendedSimulation(base, experiment)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    args.output.mkdir(parents=True, exist_ok=True)
    historical = Path(__file__).resolve().parents[1] / "results/first-simulation"
    if args.output.resolve() == historical:
        parser.error("Choisir une autre destination pour conserver la première expérience")
    source_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))}
    cases = [(policy, scenario) for policy in experiment["main_policies"] for scenario in experiment["scenarios"]]
    cases += [(policy, "reference") for policy in experiment["policies"] if policy not in experiment["main_policies"]]
    jobs = []
    for policy, scenario in cases:
        jobs.append((policy, scenario, experiment["seed"], str(args.output / policy / scenario)))
    for offset in range(1, seeds + 1):
        jobs.extend((policy, scenario, experiment["seed"] + offset, None) for policy, scenario in cases)
    rows = []
    print(f"{len(cases)} cas × {seeds + 1} graines = {len(jobs)} expériences de {experiment['days']} jours ; {workers} processus CPU", flush=True)
    with (args.output / "runs.jsonl").open("w", encoding="utf-8") as stream:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            pending = {pool.submit(run_job, base, experiment, scenario, policy, seed, output): (policy, scenario, seed) for policy, scenario, seed, output in jobs}
            for future in concurrent.futures.as_completed(pending):
                row = future.result()
                rows.append(row)
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                stream.flush()
                if row["seed"] == experiment["seed"]:
                    print(f"  {row['policy']}/{row['scenario']}: nourriture={row['food_access_rate']:.2%}, emploi payé={row['paid_employment_last30']:.1%}, logement manquant={row['unhoused_final']}", flush=True)
                if len(rows) % 10 == 0 or len(rows) == len(jobs):
                    progress = {"completed": len(rows), "total": len(jobs), "hourly_checks": sum(r["checks"] for r in rows)}
                    write_json(args.output / "progress.json", progress)
                    print(f"Progression : {len(rows)}/{len(jobs)}", flush=True)
    rows.sort(key=lambda r: (r["policy"], r["scenario"], r["seed"]))
    (args.output / "runs.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    suite = {"model": "annual-v2", "date": "2026-10-14", "experiment": experiment, "base_config": base,
             "additional_seeds": seeds, "workers": workers, "python_version": platform.python_version(),
             "total_runs": len(rows), "detailed_runs": len(cases), "total_hourly_checks": sum(r["checks"] for r in rows),
             "source_sha256": source_hashes, "detailed_summaries": [r for r in rows if r["seed"] == experiment["seed"]]}
    write_json(args.output / "suite.json", suite)
    write_report(args.output, suite, rows)
    suite["matplotlib_plots_generated"] = plot_results(args.output, rows)
    write_json(args.output / "suite.json", suite)
    print(f"Rapport : {args.output / 'report.md'}", flush=True)


if __name__ == "__main__":
    main()
