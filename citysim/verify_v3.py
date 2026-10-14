"""Independently replay V3 exports and check the paired experiment protocol."""

import argparse
import csv
import gzip
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

from .reports import write_json


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root):
    suite = json.loads((root / "suite.json").read_text())
    rows = [json.loads(line) for line in (root / "runs.jsonl").read_text().splitlines()]
    settings, experiment = suite["settings"], suite["experiment"]
    key = lambda r: (r["horizon"], r["policy"], r["scenario"], r["seed"])
    indexed = {key(r): r for r in rows}
    expected = set()
    annual_cases = [(p, s) for p in settings["main_policies"] for s in experiment["scenarios"]]
    annual_cases += [(p, "reference") for p in settings["policies"] if p not in settings["main_policies"]]
    for p, s in annual_cases:
        expected.update(("annual", p, s, experiment["seed"] + offset) for offset in range(suite["additional_seeds"] + 1))
    for p in settings["main_policies"]:
        for s in settings["long_scenarios"]:
            expected.update(("long", p, s, experiment["seed"] + offset) for offset in range(suite["long_additional_seeds"] + 1))
    assert len(rows) == len(indexed) == suite["total_runs"]
    assert set(indexed) == expected, "Missing, duplicated or unpaired experiment"
    assert sum(r["checks"] for r in rows) == suite["total_hourly_checks"]
    for r in rows:
        assert r["money_error_cents"] == 0
        assert r["money_final_cents"] == r["money_initial_cents"] + r["money_created_cents"] - r["money_removed_cents"]
        assert r["checks"] == 24 * r["days"]
        assert 0 <= r["food_access_rate"] <= 1
        assert r["all_criteria_met"] == all(r["criteria"].values())
        if r["policy"] in settings["main_policies"]:
            other = indexed[(r["horizon"], "v2" if r["policy"] == "v3" else "v3", r["scenario"], r["seed"])]
            for field in ("days", "money_initial_cents", "money_created_cents", "money_removed_cents"):
                assert r[field] == other[field], (key(r), field)

    groups = defaultdict(list)
    for r in rows:
        groups[key(r)[:3]].append(r)
    with (root / "comparison.csv").open() as stream:
        comparisons = list(csv.DictReader(stream))
    assert len(comparisons) == len(groups)
    for item in comparisons:
        group = groups[(item["horizon"], item["policy"], item["scenario"])]
        assert int(item["runs"]) == len(group)
        assert int(item["passed"]) == sum(r["all_criteria_met"] for r in group)
        for field, value in item.items():
            for suffix, aggregate in (("_mean", statistics.mean), ("_min", min), ("_max", max)):
                if field.endswith(suffix):
                    assert abs(float(value) - aggregate(r[field[:-len(suffix)]] for r in group)) < 1e-8

    transactions = files = 0
    detailed = suite["detailed_summaries"]
    assert {key(r) for r in detailed} == {key(r) for r in rows if r["seed"] == experiment["seed"]}
    for number, summary in enumerate(detailed, 1):
        folder = root / summary["horizon"] / summary["policy"] / summary["scenario"]
        audit = json.loads((folder / "audit.json").read_text())
        balances = defaultdict(int, json.loads((folder / "initial_accounts.json").read_text()))
        assert sum(balances.values()) == audit["money_initial_cents"] == summary["money_initial_cents"]
        assert audit["hourly_checks"] == summary["checks"]
        assert audit["money_created_cents"] == summary["money_created_cents"]
        assert audit["money_removed_cents"] == 0
        assert audit["open_orders"] == 0
        for product, final in audit["stock_final"].items():
            assert final == audit["stock_initial"].get(product, 0) + audit["stock_added"].get(product, 0) - audit["stock_taken"].get(product, 0)
        previous_hour, issuance = -1, 0
        with gzip.open(folder / "ledger.csv.gz", "rt", newline="") as stream:
            for row in csv.DictReader(stream):
                hour, cents = int(row["hour"]), int(row["cents"])
                assert previous_hour <= hour < summary["checks"]
                previous_hour = hour
                assert cents >= 0
                if row["source"] != "issuance":
                    balances[row["source"]] -= cents
                    assert balances[row["source"]] >= 0, row
                else:
                    issuance += cents
                balances[row["target"]] += cents
                transactions += 1
        assert issuance == audit["money_created_cents"]
        assert {k: v for k, v in balances.items() if v} == {k: v for k, v in audit["accounts_final"].items() if v}
        assert sum(balances.values()) == summary["money_final_cents"]
        for filename, digest in json.loads((folder / "manifest.json").read_text()).items():
            assert sha(folder / filename) == digest, folder / filename
            files += 1
        with (folder / "daily.csv").open() as stream:
            assert len(list(csv.DictReader(stream))) == summary["days"]
        with gzip.open(folder / "hourly.csv.gz", "rt") as stream:
            assert sum(1 for _ in csv.DictReader(stream)) == summary["checks"]
        with (folder / "newcomers.csv").open() as stream:
            cohort_rows = list(csv.DictReader(stream))
        assert len(cohort_rows) == len(summary["newcomer_cohorts"])
        for exported, original in zip(cohort_rows, summary["newcomer_cohorts"]):
            assert all(abs(float(exported[k]) - value) < 1e-9 for k, value in original.items())
        histories = defaultdict(list)
        with gzip.open(folder / "household_daily.csv.gz", "rt") as stream:
            for row in csv.DictReader(stream):
                if row["household"].startswith("new"):
                    histories[row["household"]].append(row)
        with (folder / "profiles.csv").open() as stream:
            profiles = {r["household"]: r for r in csv.DictReader(stream)}
        reconstructed = defaultdict(list)
        for household, history in histories.items():
            arrival = int(history[0]["arrival_day"])
            first, last = history[:30], history[-30:]
            income = sum(int(r["income_cents"]) for r in last)
            spent = sum(int(r["essential_spending_cents"]) for r in last)
            paid = [int(r["day"]) for r in history if int(r["paid_wages_cents"])]
            profile = profiles[household]
            wait = int(profile["days_to_housing"]) if profile["housed"] == "True" else summary["days"] - arrival + 1
            reconstructed[arrival].append({
                "cash": balances[household], "cover": income / spent if spent else 0,
                "initial_cover": sum(int(r["income_cents"]) for r in first) / max(1, sum(int(r["essential_spending_cents"]) for r in first)),
                "food": 1 - sum(int(r["food_missing_units"]) for r in history) / max(1, 2 * sum(r["mode"] != "sleep" for r in history)),
                "reserve": balances[household] / max(1, spent / len(last)),
                "first_wage_wait": (min(paid) if paid else summary["days"] + 1) - arrival,
                "housing_wait": wait,
            })
        for cohort in summary["newcomer_cohorts"]:
            group = reconstructed[cohort["arrival_day"]]
            recomputed = {"households": len(group), "cash_median_cents": statistics.median(r["cash"] for r in group),
                          "essential_cover_median": statistics.median(r["cover"] for r in group),
                          "initial_cover_median": statistics.median(r["initial_cover"] for r in group),
                          "food_access_minimum": min(r["food"] for r in group),
                          "reserve_days_median": statistics.median(r["reserve"] for r in group),
                          "first_wage_wait_max_days": max(r["first_wage_wait"] for r in group),
                          "housing_wait_max_days": max(r["housing_wait"] for r in group)}
            assert all(abs(value - cohort[field]) < 1e-9 for field, value in recomputed.items()), (folder, cohort)
        print(f"Exports V3 vérifiés : {number}/{len(detailed)} ({transactions:,} écritures rejouées)", flush=True)

    for name, digest in suite["source_sha256"].items():
        assert sha(Path(__file__).parent / name) == digest, name
    historical = {}
    for prior in ("first-simulation", "annual-simulation"):
        count = 0
        for manifest in (root.parent / prior).glob("**/manifest.json"):
            for filename, digest in json.loads(manifest.read_text()).items():
                assert sha(manifest.parent / filename) == digest, manifest.parent / filename
                count += 1
        assert count > 0
        historical[prior] = count
    result = {"all_run_summaries_verified": len(rows), "paired_protocol_verified": True,
              "aggregate_table_verified": True, "newcomer_cohorts_recomputed": True, "detailed_exports_verified": len(detailed),
              "hourly_checks": suite["total_hourly_checks"], "ledger_transactions_replayed": transactions,
              "export_files_hash_verified": files, "historical_export_files_hash_verified": historical,
              "money_and_stock_audits_closed": True, "source_hashes_match": True,
              "report_and_plot_sha256": {name: sha(root / name) for name in ("report.md", "comparison.csv", "comparison.svg", "comparison.png") if (root / name).exists()},
              "verification_source_sha256": sha(Path(__file__))}
    write_json(root / "verification.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description="Vérifier les comparaisons économiques V3 et leurs exports")
    parser.add_argument("--results", type=Path, default=Path("results/v3-simulation"))
    print(json.dumps(verify(parser.parse_args().results), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
