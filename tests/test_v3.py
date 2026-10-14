import copy
import json
import unittest
from pathlib import Path

from citysim.extended import ExtendedSimulation
from citysim.v3 import WelcomingSimulation

ROOT = Path(__file__).resolve().parents[1]
BASE = json.loads((ROOT / "config/default.json").read_text())
EXPERIMENT = json.loads((ROOT / "config/extended.json").read_text())
SETTINGS = json.loads((ROOT / "config/v3.json").read_text())


class V3Tests(unittest.TestCase):
    def run_case(self, scenario="reference", policy="v3", days=90, detailed=False):
        settings = copy.deepcopy(SETTINGS)
        settings["days"] = days
        return WelcomingSimulation(BASE, EXPERIMENT, settings, scenario, policy, detailed=detailed).run()

    def test_v2_control_preserves_original_engine_accounts_and_daily_results(self):
        e = copy.deepcopy(EXPERIMENT)
        e["days"] = 90
        old = ExtendedSimulation(BASE, e, "arrivals", "balanced").run()
        control = self.run_case("arrivals", "v2")
        self.assertEqual(old.daily, control.daily)
        self.assertEqual(old.ledger.balances, control.ledger.balances)

    def test_incremental_days_equal_batch_execution(self):
        settings = copy.deepcopy(SETTINGS)
        settings["days"] = 30
        stepped = WelcomingSimulation(BASE, EXPERIMENT, settings)
        for _ in range(30):
            stepped.step_day()
        batch = self.run_case(days=30)
        self.assertEqual(stepped.daily, batch.daily)
        self.assertEqual(stepped.ledger.balances, batch.ledger.balances)
        with self.assertRaises(ValueError):
            stepped.step_day()

    def test_progressive_expansion_keeps_existing_firms_and_finances_each_position(self):
        s = self.run_case("arrivals", days=100, detailed=True)
        self.assertEqual(len(s.businesses), 8)
        self.assertGreater(s.job_expansions, 0)
        self.assertFalse(any(b.id.startswith("cooperative") for b in s.businesses))
        self.assertTrue(any(row[4] == "progressive_expansion_contract" for row in s.ledger.history))
        self.assertEqual(s.ledger.created, 28 * BASE["initial_household_cash_cents"])
        s.ledger.check()
        s.stocks.check()

    def test_newcomers_receive_real_salary_and_keep_food_reserve(self):
        s = self.run_case("arrivals", days=120)
        for cohort in s.newcomer_cohorts():
            self.assertLessEqual(cohort["first_wage_wait_max_days"], 3)
            self.assertGreaterEqual(cohort["reserve_days_median"], 3)
            self.assertEqual(cohort["food_access_minimum"], 1)

    def test_sleep_delegation_never_pays_the_owner(self):
        s = self.run_case("absence", days=60, detailed=True)
        for id in ("player02", "player03"):
            bad = [r for r in s.ledger.history if r[0] >= 37 * 24 and r[2] == id and r[4] in ("wage", "dividend", "worker_profit_share", "subsistence_grant")]
            self.assertEqual(bad, [])
        self.assertTrue(any(r[4] == "delegated_management" for r in s.ledger.history))
        self.assertTrue(next(b for b in s.businesses if b.id == "bakery_a").workers)

    def test_cooperative_tariffs_do_not_create_goods_or_money(self):
        s = self.run_case("combined", days=150)
        self.assertEqual(s.summary()["money_error_cents"], 0)
        s.stocks.check()
        for product in ("grain", "flour", "bread", "vegetables"):
            quotes = {b.price for b in s.businesses if b.product == product and b.mode == "normal"}
            self.assertLessEqual(len(quotes), 1)

    def test_all_scenarios_conserve_flows_with_new_rules(self):
        for scenario in EXPERIMENT["scenarios"]:
            with self.subTest(scenario=scenario):
                s = self.run_case(scenario, days=180)
                s.ledger.check()
                s.stocks.check()
                self.assertEqual(s.checks, 4320)


if __name__ == "__main__":
    unittest.main()
