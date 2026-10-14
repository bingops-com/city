"""Independent replay of exported money ledgers and checks of annual artifacts."""

import argparse
import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from .reports import write_json


def verify(root):
    suite = json.loads((root / "suite.json").read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in (root / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(samples) == suite["total_runs"]
    assert sum(r["checks"] for r in samples) == suite["total_hourly_checks"]
    assert len({(r["scenario"], r["policy"], r["seed"]) for r in samples}) == len(samples)
    for row in samples:
        assert row["money_error_cents"] == 0
        assert row["money_final_cents"] == row["money_initial_cents"] + row["money_created_cents"] - row["money_removed_cents"]
        assert row["checks"] == row["days"] * 24
        assert 0 <= row["food_access_rate"] <= 1
    transactions = files = 0
    for index, summary in enumerate(suite["detailed_summaries"], 1):
        folder = root / summary["policy"] / summary["scenario"]
        audit = json.loads((folder / "audit.json").read_text(encoding="utf-8"))
        balances = defaultdict(int, json.loads((folder / "initial_accounts.json").read_text(encoding="utf-8")))
        assert sum(balances.values()) == audit["money_initial_cents"]
        for product, final in audit["stock_final"].items():
            assert final == audit["stock_initial"].get(product, 0) + audit["stock_added"].get(product, 0) - audit["stock_taken"].get(product, 0)
        previous_hour = -1
        with gzip.open(folder / "ledger.csv.gz", "rt", encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                hour = int(row["hour"])
                assert hour >= previous_hour
                previous_hour = hour
                cents = int(row["cents"])
                assert cents >= 0
                if row["source"] != "issuance":
                    balances[row["source"]] -= cents
                    assert balances[row["source"]] >= 0, row
                balances[row["target"]] += cents
                transactions += 1
        assert {k: v for k, v in balances.items() if v} == {k: v for k, v in audit["accounts_final"].items() if v}
        assert sum(balances.values()) == summary["money_final_cents"]
        assert audit["open_orders"] == 0
        for filename, expected in json.loads((folder / "manifest.json").read_text(encoding="utf-8")).items():
            assert hashlib.sha256((folder / filename).read_bytes()).hexdigest() == expected
            files += 1
        daily = list(csv.DictReader((folder / "daily.csv").open(encoding="utf-8")))
        assert len(daily) == summary["days"]
        with gzip.open(folder / "hourly.csv.gz", "rt", encoding="utf-8") as stream:
            assert sum(1 for _ in csv.DictReader(stream)) == summary["checks"]
        print(f"Exports vérifiés : {index}/{suite['detailed_runs']} ({transactions:,} écritures rejouées)", flush=True)
    for name, expected in suite["source_sha256"].items():
        assert hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest() == expected, name
    diagnostics = root / "financial_diagnostics_meta.json"
    if diagnostics.exists():
        metadata = json.loads(diagnostics.read_text(encoding="utf-8"))
        assert hashlib.sha256((root / "financial_diagnostics.csv").read_bytes()).hexdigest() == metadata["csv_sha256"]
        assert hashlib.sha256((Path(__file__).parent / "financial_diagnostics.py").read_bytes()).hexdigest() == metadata["source_sha256"]
    previous = Path(__file__).resolve().parents[1] / "results/first-simulation"
    historical_files = 0
    for manifest in previous.glob("**/manifest.json"):
        for filename, expected in json.loads(manifest.read_text(encoding="utf-8")).items():
            assert hashlib.sha256((manifest.parent / filename).read_bytes()).hexdigest() == expected
            historical_files += 1
    verification = {"detailed_exports_verified": suite["detailed_runs"], "all_run_summaries_verified": len(samples),
                    "hourly_checks": suite["total_hourly_checks"], "ledger_transactions_replayed": transactions,
                    "export_files_hash_verified": files, "historical_export_files_hash_verified": historical_files,
                    "money_and_stock_audits_closed": True, "source_hashes_match": True,
                    "report_and_plot_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in
                                                ("report.md", "comparison.svg", "comparison.png", "trajectories.svg", "trajectories.png") if (root / name).exists()},
                    "verification_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    write_json(root / "verification.json", verification)
    return verification


def main():
    parser = argparse.ArgumentParser(description="Vérifier les exports de la simulation annuelle de City")
    parser.add_argument("--results", type=Path, default=Path("results/annual-simulation"))
    args = parser.parse_args()
    print(json.dumps(verify(args.results), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
