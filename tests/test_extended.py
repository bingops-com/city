import copy
import json
import unittest
from pathlib import Path

from citysim.extended import ExtendedSimulation


ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT / "config/default.json").read_text())
EXPERIMENT = json.loads((ROOT / "config/extended.json").read_text())


class ExtendedTests(unittest.TestCase):
    def run_case(self, scenario="reference", policy="balanced", days=90, detailed=False, updates=None):
        e = copy.deepcopy(EXPERIMENT)
        e["days"] = days
        if updates:
            e.update(updates)
        return ExtendedSimulation(BASE, e, scenario, policy, detailed=detailed).run()

    def test_all_annual_scenarios_and_policies_conserve_flows(self):
        for scenario in EXPERIMENT["scenarios"]:
            with self.subTest(scenario=scenario):
                s = self.run_case(scenario, days=180)
                s.ledger.check()
                s.stocks.check()
                self.assertEqual(s.checks, 4320)
                self.assertEqual(s.summary()["money_error_cents"], 0)
                self.assertFalse(s.market.orders)
        for policy in EXPERIMENT["policies"]:
            with self.subTest(policy=policy):
                self.run_case(policy=policy, days=45).ledger.check()

    def test_summary_mode_matches_detailed_mode(self):
        detailed = self.run_case("combined", days=150, detailed=True)
        lean = self.run_case("combined", days=150)
        self.assertEqual(detailed.daily, lean.daily)
        self.assertEqual(detailed.summary(), lean.summary())
        self.assertEqual(detailed.ledger.balances, lean.ledger.balances)
        self.assertEqual(detailed.household_daily, lean.household_daily)

    def test_same_seed_reproduces_extended_events_and_balances(self):
        first = self.run_case("arrivals", days=60, detailed=True)
        second = self.run_case("arrivals", days=60, detailed=True)
        self.assertEqual(first.daily, second.daily)
        self.assertEqual(first.events, second.events)
        self.assertEqual(first.ledger.history, second.ledger.history)

    def test_visitors_return_unused_budget_and_leave_no_housing_occupation(self):
        s = self.run_case(days=10)
        self.assertEqual(len(s.tourists), 0)
        self.assertEqual(len(s.residents()), 48)
        self.assertEqual(len(s.visitor_history), 2)
        self.assertTrue(all(s.ledger.balances[h["household"]] == 0 for h in s.visitor_history))
        self.assertEqual(s.ledger.created, 0)
        self.assertEqual(sum(h.housing for h in s.residents()), 48)
        s.stocks.check()

    def test_external_stop_has_no_new_contract_export_or_import(self):
        s = self.run_case("external_trade_stop", days=185, detailed=True)
        illegal = [row for row in s.ledger.history if 119 * 24 <= row[0] < 179 * 24 and row[4] in ("public_service_export", "material_export", "municipal:food_import")]
        self.assertEqual(illegal, [])
        self.assertTrue(any(r[4] == "public_service_export" and r[0] >= 179 * 24 for r in s.ledger.history))

    def test_sleep_protection_blocks_grants_profit_shares_and_salary(self):
        s = self.run_case("absence", days=145, detailed=True)
        for id in ("player02", "player03"):
            start = 37 * 24
            end = 140 * 24
            bad = [r for r in s.ledger.history if start <= r[0] < end and r[2] == id and r[4] in ("wage", "dividend", "worker_profit_share", "subsistence_grant")]
            self.assertEqual(bad, [])
            self.assertTrue(next(h for h in s.residents() if h.id == id).housing)

    def test_live_abuse_probes_are_rejected(self):
        for scenario, count in (("municipal_abuse", 4), ("economic_abuse", 3)):
            s = self.run_case(scenario, days=40)
            self.assertEqual(s.rejected_abuses, count)
            s.ledger.check()
            s.stocks.check()

    def test_growth_capital_is_reserved_then_funded_without_issuance(self):
        s = self.run_case("arrivals", days=75, detailed=True)
        self.assertGreater(s.growth_completed, 0)
        self.assertGreater(s.projects_completed, 0)
        self.assertTrue(any(r[4] == "business_starting_capital" and r[1] == "investment_escrow" for r in s.ledger.history))
        self.assertEqual(s.ledger.created, 20 * BASE["initial_household_cash_cents"])
        self.assertGreater(s.config["public_job_capacity"], BASE["public_job_capacity"])
        s.ledger.check()

    def test_public_jobs_do_not_count_as_paid_when_city_cannot_pay(self):
        s = self.run_case(policy="legacy", days=180)
        self.assertGreater(s.municipal_arrears, 0)
        self.assertLess(s.summary()["paid_employment_last30"], s.summary()["employment_final"])

    def test_connected_presence_is_not_an_economic_multiplier(self):
        normal = self.run_case(days=45)
        low = self.run_case("low_presence", days=45)
        self.assertEqual(normal.ledger.balances, low.ledger.balances)
        self.assertNotEqual([r["connected_players"] for r in normal.daily], [r["connected_players"] for r in low.daily])

    def test_partial_day_rounding_is_not_reported_as_unpaid_salary(self):
        s = self.run_case("absence", days=30)
        self.assertEqual(s.municipal_arrears, 0)
        self.assertEqual(s.private_arrears, 0)


if __name__ == "__main__":
    unittest.main()
