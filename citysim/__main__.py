from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
from pathlib import Path

from .engine import SCENARIOS, RuleError, Simulation
from .reports import export_run, suite_report, write_csv, write_json


def main():
    parser = argparse.ArgumentParser(description="Première simulation économique de City, sans dépendance externe")
    parser.add_argument("--config", type=Path, default=Path("config/default.json"))
    parser.add_argument("--output", type=Path, default=Path("results/first-simulation"))
    parser.add_argument("--scenario", choices=["all", *SCENARIOS], default="all")
    parser.add_argument("--seeds", type=int, default=30, help="Nombre de graines supplémentaires par scénario")
    parser.add_argument("--seed", type=int, help="Remplacer la graine de référence")
    parser.add_argument("--days", type=int, help="Remplacer la durée")
    args = parser.parse_args()
    if args.seeds < 0:
        parser.error("--seeds doit être positif ou nul")
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        if args.seed is not None:
            config["seed"] = args.seed
        if args.days is not None:
            config["days"] = args.days
        Simulation(config)  # Validate before writing any exports.
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    args.output.mkdir(parents=True, exist_ok=True)
    runs, samples, variants = [], [], []
    scenarios = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    for name in scenarios:
        s = Simulation(config, name).run()
        export_run(s, args.output / name)
        runs.append(s)
        print(f"{name}: alimentation={s.summary()['food_access_rate']:.2%}, mairie={s.ledger.balances['city'] / 100:.2f}", flush=True)
        for index in range(args.seeds):
            other = Simulation(config, name, config["seed"] + index + 1, record_hourly=False).run()
            samples.append(other.summary())
            if (index + 1) % 10 == 0:
                print(f"  variabilité : {index + 1}/{args.seeds} graines", flush=True)
    if "reference" in scenarios:
        experiments = [
            ("price_signal", {"price_scarcity_stock_ratio": .25}),
            ("smaller_reserve", {"reserve_target_bread": 48, "reserve_target_vegetables": 48}),
            ("price_and_reserve", {"price_scarcity_stock_ratio": .25, "reserve_target_bread": 48, "reserve_target_vegetables": 48}),
        ]
        for label, changes in experiments:
            variant_config = copy.deepcopy(config)
            variant_config.update(changes)
            s = Simulation(variant_config).run()
            export_run(s, args.output / "variants" / label)
            variants.append((label, changes, s))
            print(f"variante {label}: alimentation={s.summary()['food_access_rate']:.2%}, mairie={s.ledger.balances['city'] / 100:.2f}", flush=True)
    write_csv(args.output / "variability.csv", samples)
    write_json(args.output / "suite.json", {
        "date": "2026-10-14", "config": config, "python_version": platform.python_version(),
        "scenario_descriptions": {name: SCENARIOS[name] for name in scenarios},
        "additional_seeds_per_scenario": args.seeds,
        "detailed_runs": [s.summary() for s in runs],
        "variants": [{"name": label, "changes": changes, "summary": s.summary()} for label, changes, s in variants],
        "total_runs": len(runs) + len(samples) + len(variants),
        "total_hourly_checks": sum(s.checks for s in runs) + sum(s["checks"] for s in samples) + sum(s.checks for _, _, s in variants),
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))},
    })
    suite_report(args.output, runs, samples, variants)
    print(f"Rapport : {args.output / 'report.md'}", flush=True)


if __name__ == "__main__":
    main()
