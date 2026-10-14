import copy
import json
import random
import unittest
from pathlib import Path

from citysim.engine import Ledger, Market, RuleError, SCENARIOS, Simulation, Stocks


CONFIG = json.loads((Path(__file__).resolve().parents[1] / "config/default.json").read_text())


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger({"buyer": 1000, "seller": 100, "other": 500, "city": 0})
        self.stocks = Stocks(["bread"])
        self.stocks.initialize("seller", {"bread": 5})
        self.market = Market(self.ledger, self.stocks, random.Random(3), capacity=3, fee=1)

    def test_funds_and_goods_cannot_be_reserved_twice(self):
        self.market.place("buy1", "buyer", "bread", 3, 200, 2, "buy")
        before_cash = dict(self.ledger.balances)
        with self.assertRaises(RuleError):
            self.market.place("buy2", "buyer", "bread", 3, 200, 2, "buy")
        self.assertEqual(before_cash, self.ledger.balances)
        self.market.place("sell1", "seller", "bread", 4, 150, 0, "sell")
        with self.assertRaises(RuleError):
            self.market.place("sell2", "seller", "bread", 2, 150, 0, "sell")
        self.assertEqual(self.stocks.items["seller"]["bread"], 1)
        self.ledger.check()
        self.stocks.check()

    def test_partial_delivery_refunds_all_unspent_reservations(self):
        self.market.place("buy", "buyer", "bread", 4, 200, 2, "buy")
        self.market.place("sell", "seller", "bread", 5, 150, 0, "sell")
        self.market.clear()
        self.assertEqual(self.ledger.balances["buyer"], 1000 - 3 * 152)
        self.assertEqual(self.ledger.balances["seller"], 100 + 3 * 150)
        self.assertEqual(self.ledger.balances["city"], 6)
        self.assertEqual(self.stocks.items["buyer"]["bread"], 3)
        self.assertEqual(self.stocks.items["seller"]["bread"], 2)
        self.assertFalse(self.market.orders)
        self.assertFalse(any(x.startswith("escrow:") for x in self.ledger.balances))
        self.ledger.check()
        self.stocks.check()

    def test_replay_does_not_execute_twice_even_after_expiration(self):
        args = ("buy", "buyer", "bread", 2, 200, 0, "buy")
        self.assertTrue(self.market.place(*args))
        self.assertFalse(self.market.place(*args))
        self.market.place("sell", "seller", "bread", 2, 150, 0, "sell")
        self.market.clear()
        balances = dict(self.ledger.balances)
        self.assertFalse(self.market.place(*args))
        self.market.clear()
        self.assertEqual(balances, self.ledger.balances)
        with self.assertRaises(RuleError):
            self.market.place("buy", "buyer", "bread", 1, 200, 0, "buy")

    def test_transfer_replay_and_overdraft(self):
        self.assertTrue(self.ledger.transfer("buyer", "seller", 500, "test", "cmd"))
        self.assertFalse(self.ledger.transfer("buyer", "seller", 500, "test", "cmd"))
        with self.assertRaises(RuleError):
            self.ledger.transfer("buyer", "other", 500, "test", "cmd")
        before = dict(self.ledger.balances)
        with self.assertRaises(RuleError):
            self.ledger.transfer("buyer", "seller", 501, "test")
        self.assertEqual(before, self.ledger.balances)
        self.ledger.check()

    def test_self_trade_does_not_create_revenue(self):
        self.market.place("selfbuy", "seller", "bread", 1, 50, 0, "buy")
        self.market.place("selfsell", "seller", "bread", 1, 50, 0, "sell")
        self.assertEqual(self.market.clear(), [])
        self.assertEqual(self.ledger.balances["seller"], 100)
        self.assertEqual(self.stocks.items["seller"]["bread"], 5)


class SimulationTests(unittest.TestCase):
    def config(self, days=90):
        config = copy.deepcopy(CONFIG)
        config["days"] = days
        return config

    def test_all_scenarios_conserve_money_and_material_for_full_period(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                s = Simulation(self.config(), scenario, record_hourly=False).run()
                self.assertEqual(s.checks, 2160)
                self.assertEqual(s.summary()["money_error_cents"], 0)
                self.assertTrue(all(x >= 0 for x in s.ledger.balances.values()))
                s.stocks.check()
                self.assertFalse(s.market.orders)

    def test_same_seed_reproduces_transactions_events_and_trajectories(self):
        first = Simulation(self.config(), "combined").run()
        second = Simulation(self.config(), "combined").run()
        self.assertEqual(first.summary(), second.summary())
        self.assertEqual(first.events, second.events)
        self.assertEqual(first.hourly, second.hourly)
        self.assertEqual(first.ledger.history, second.ledger.history)
        self.assertEqual(first.profiles(), second.profiles())

    def test_connected_presence_has_no_economic_bonus(self):
        normal = Simulation(self.config(), "reference").run()
        low = Simulation(self.config(), "low_presence").run()
        self.assertLess(sum(r["connected_players"] for r in low.daily), sum(r["connected_players"] for r in normal.daily))
        self.assertEqual(normal.ledger.history, low.ledger.history)
        self.assertEqual(normal.profiles(), low.profiles())

    def test_sleep_has_neither_wages_nor_rent_nor_dividends(self):
        s = Simulation(self.config(), "absence").run()
        for id in ("player02", "player03"):
            changes = [e for e in s.events if e["type"] == "routine_change" and e["household"] == id and "→ sleep" in e["description"]]
            start = changes[0]["hour"]
            end = (65 - 1) * 24
            illegal = [row for row in s.ledger.history if start <= row[0] < end and (
                row[2] == id and row[4] in ("wage", "dividend") or row[1] == id and row[4] == "rent")]
            self.assertEqual(illegal, [])
            self.assertTrue(next(h for h in s.households if h.id == id).housing)

    def test_absence_duration_uses_real_hours(self):
        for ratio in (3, 6):
            c = self.config()
            c["simulated_hours_per_real_hour"] = ratio
            s = Simulation(c, "absence").run()
            sleep = next(e for e in s.events if e["type"] == "routine_change" and e["household"] == "player02" and "→ sleep" in e["description"])
            self.assertEqual(sleep["hour"] - 19 * 24, CONFIG["absence_sleep_real_hours"] * ratio)
            self.assertEqual(sleep["real_absence_hours"], 72)

    def test_municipal_unauthorized_conflicted_and_overbudget_actions_do_not_mutate_state(self):
        s = Simulation(self.config(1))
        for purpose, approved, conflict, amount in (("housing", False, False, 100), ("housing", True, True, 100),
                                                   ("personal_gift", True, False, 100), ("housing", True, False, 1200001)):
            before = dict(s.ledger.balances)
            with self.assertRaises(RuleError):
                s.government_spend("bad", amount, "project_escrow", purpose, approved, conflict)
            self.assertEqual(before, s.ledger.balances)
        before = dict(s.ledger.balances)
        with self.assertRaises(RuleError):
            s.government_spend("diverted", 100, "player02", "housing", True)
        self.assertEqual(before, s.ledger.balances)
        self.assertTrue(s.government_spend("good", 100, "project_escrow", "housing", True))
        self.assertFalse(s.government_spend("good", 100, "project_escrow", "housing", True))
        with self.assertRaises(RuleError):
            s.government_spend("good", 101, "project_escrow", "housing", True)

    def test_account_creation_alone_does_not_expand_housing(self):
        c = self.config()
        c["daily_wage_cents"] = 1000000
        c["public_job_capacity"] = 0
        s = Simulation(c, "arrivals").run()
        self.assertEqual(len(s.households), 68)
        self.assertEqual(s.projects_completed, 0)
        self.assertEqual(s.housing, c["initial_housing"])

    def test_housing_can_finish_when_materials_can_accumulate(self):
        c = self.config()
        c["material_export_daily_limit"] = 16
        c["reserve_target_bread"] = c["reserve_target_vegetables"] = 48
        s = Simulation(c, "arrivals").run()
        self.assertGreaterEqual(s.projects_completed, 2)
        self.assertEqual(s.summary()["unhoused_final"], 0)
        self.assertTrue(any(e["type"] == "housing_started" for e in s.events))
        s.ledger.check()
        s.stocks.check()

    def test_invalid_configuration_is_rejected(self):
        for key, value in (("days", 0), ("market_period_hours", 5), ("simulated_hours_per_real_hour", 0),
                           ("wage_tax_basis_points", 10001), ("daily_rent_cents", -1)):
            with self.subTest(key=key):
                c = self.config()
                c[key] = value
                with self.assertRaises(RuleError):
                    Simulation(c)


if __name__ == "__main__":
    unittest.main()
