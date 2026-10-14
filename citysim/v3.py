"""Progressive expansion and simple, automatic routines for the City prototype."""
from __future__ import annotations

import copy
import math
import statistics
from collections import Counter, defaultdict

from .extended import ExtendedSimulation


class WelcomingSimulation(ExtendedSimulation):
    def __init__(self, base, experiment, settings, scenario="reference", policy="v3", seed=None, detailed=False):
        self.settings = copy.deepcopy(settings)
        self.v3_rules = settings["policies"][policy]
        e = copy.deepcopy(experiment)
        e["days"] = settings["days"]
        if self.v3_rules["circulation"]:
            e["wealth_tax_threshold_cents"] = settings["wealth_tax_threshold_cents"]
            e["wealth_tax_weekly_basis_points"] = settings["wealth_tax_weekly_basis_points"]
        super().__init__(base, e, scenario, "balanced", seed, detailed)
        self.policy = policy
        self.original_firms = {b.id: {"jobs": b.jobs, "capacity": b.daily_capacity} for b in self.businesses}
        self.original_population = base["npc_count"] + base["player_count"]
        self.original_public_jobs = base["public_job_capacity"]
        self.first_wage_day = {}
        self.personal_baselines = {}
        self.job_expansions = 0

    def routines(self):
        owners = [(b, b.owner) for b in self.businesses]
        if self.v3_rules["adaptive"]:
            residents = sum(h.absence_start is None or (self.hour - h.absence_start) / self.config["simulated_hours_per_real_hour"] < self.config["absence_sleep_real_hours"] for h in self.residents())
            existing_private_jobs = sum(b.jobs for b in self.businesses)
            self.config["public_job_capacity"] = max(self.original_public_jobs, residents - existing_private_jobs)
        if self.v3_rules["delegation"]:
            for b in self.businesses:
                if b.product != "materials":
                    b.owner = None
        super().routines()
        for b, owner in owners:
            b.owner = owner
        if self.v3_rules["delegation"]:
            by_id = {h.id: h for h in self.residents()}
            for b in self.businesses:
                if b.owner and by_id[b.owner].mode != "normal" and b.mode == "normal" and b.product != "materials":
                    fee = min(self.settings["delegation_daily_fee_cents"], self.ledger.balances[b.id])
                    self.ledger.transfer(b.id, "city", fee, "delegated_management")
        self.personal_baselines = {h.id: (h.income, h.essential_spending) for h in self.residents()}

    def consider_growth(self):
        if not self.v3_rules["adaptive"]:
            return super().consider_growth()
        if self.day % self.settings["workforce_review_days"]:
            return
        active = sum(h.mode != "sleep" for h in self.residents())
        scale = max(1, active / self.original_population)
        workshop = next(b for b in self.businesses if b.product == "materials")
        for b in self.businesses:
            if b.product == "materials" or b.mode != "normal":
                continue
            initial = self.original_firms[b.id]
            desired = max(initial["jobs"], round(initial["jobs"] * scale))
            if desired <= b.jobs:
                continue
            # One funded position at a time. No new four-company bundle and no free capital.
            materials = self.settings["expansion_materials_per_job"]
            material_cost = materials * workshop.price
            labor_cost = self.settings["expansion_cost_per_job_cents"]
            total = material_cost + labor_cost
            if self.ledger.balances["city"] < total + self.commitment_reserve() or self.stocks.items[workshop.id]["materials"] < materials:
                self.funding_blocks["progressive_expansion"] += 1
                continue
            command = f"extend:{self.day}:{b.id}"
            self.government_spend(command, total, "investment_escrow", "business_expansion", approved=True)
            self.ledger.transfer("investment_escrow", workshop.id, material_cost, "growth_materials")
            workshop.revenue += material_cost
            workshop.sales += materials
            self.ledger.transfer(workshop.id, "city", material_cost * self.config["sales_tax_basis_points"] // 10000, "sales_tax")
            self.ledger.transfer("investment_escrow", "external", labor_cost, "progressive_expansion_contract")
            self.stocks.take(workshop.id, "materials", materials, "progressive_expansion")
            b.jobs += 1
            b.daily_capacity = round(initial["capacity"] * b.jobs / initial["jobs"])
            self.job_expansions += 1
            self.event("business_extended", "Un poste financé dans un commerce existant", business=b.id, jobs=b.jobs, cost_cents=total)

    def public_prices(self):
        if not self.v3_rules["cooperative_prices"]:
            return super().public_prices()
        active = sum(h.mode != "sleep" for h in self.households)
        c = self.config
        quoted = {}
        for product in ("grain", "flour", "bread", "vegetables"):
            sellers = [b for b in self.businesses if b.product == product and b.mode not in ("sleep", "insolvent")]
            if not sellers:
                continue
            input = sellers[0].input
            inputs = quoted.get(input, min((x.price for x in self.businesses if x.product == input), default=0)) if input else 0
            wages = sum(sum(c["daily_wage_cents"] // (2 if h.mode == "reduced" else 1) for h in b.workers) for b in sellers)
            cost = inputs + (wages + sum(b.maintenance for b in sellers)) / max(1, active)
            spoil = c["products"][product]["daily_spoil_basis_points"] / 10000
            target = round(cost / (1 - spoil) / (1 - c["sales_tax_basis_points"] / 10000) * self.settings["cooperative_markup"])
            stocks = sum(self.stocks.items[b.id][product] for b in sellers)
            if stocks < active * .25:
                target = round(target * 1.1)
            old = round(statistics.mean(self.price_history[b.id][-1] if self.price_history[b.id] else c["products"][product]["base_price_cents"] for b in sellers))
            fraction = self.experiment["price_adjustment_max_fraction"]
            target = min(round(old * (1 + fraction)), max(round(old * (1 - fraction)), target))
            base = c["products"][product]["base_price_cents"]
            price = max(round(base * .8), min(round(base * c["price_maximum_multiplier"]), target))
            quoted[product] = price
            # A cooperative posted tariff is a tested rule, not a guaranteed outlet.
            # Actual orders, funds, delivery and stock still determine sales.
            for b in sellers:
                b.price = price

    def distribute_profits(self):
        super().distribute_profits()
        if self.v3_rules["circulation"]:
            for b in self.businesses:
                if b.mode != "normal":
                    continue
                reserve = max(self.starting_firm_cash[b.id], b.jobs * self.config["daily_wage_cents"] * 14)
                surplus = max(0, self.ledger.balances[b.id] - reserve)
                tax = surplus * self.settings["municipal_profit_tax_basis_points"] // 10000
                if tax:
                    self.ledger.transfer(b.id, "city", tax, "retained_business_surplus_tax")

    def imports_and_exports(self):
        if not self.v3_rules["adaptive"]:
            return super().imports_and_exports()
        workshop = next(b for b in self.businesses if b.product == "materials")
        limit = self.config["material_export_daily_limit"]
        self.config["material_export_daily_limit"] = min(limit, max(0, self.stocks.items[workshop.id]["materials"] - self.settings["local_material_reserve"]))
        super().imports_and_exports()
        self.config["material_export_daily_limit"] = limit

    def discretionary_market(self):
        # Furniture should never compete with food for the newcomer budget.
        if not any(h.housing and h.mode == "normal" for h in self.residents()):
            return
        return super().discretionary_market()

    def observations(self):
        super().observations()
        latest = self.household_daily[-len(self.residents()):]
        by_id = {h.id: h for h in self.residents()}
        for row in latest:
            h = by_id[row["household"]]
            income, spent = self.personal_baselines.get(h.id, (0, 0))
            wealth_tax = self.ledger.daily_flows[self.day].get((h.id, "city", "wealth_tax"), 0)
            row["income_cents"] = h.income - income - wealth_tax
            row["essential_spending_cents"] = h.essential_spending - spent
            if row["paid_wages_cents"]:
                self.first_wage_day.setdefault(h.id, self.day)

    def step_day(self):
        if self.day >= self.config["days"]:
            raise ValueError("Horizon de simulation atteint")
        self.day += 1
        self.hour = (self.day - 1) * 24
        self.ledger.hour = self.hour
        self.daily_sales.clear()
        self.daily_firm_revenue.clear()
        self.weather = self.weather_rng.uniform(.9, 1.1)
        self.apply_events()
        self.routines()
        before = {h.id: h.food_received for h in self.households}
        self.day_consumed = Counter()
        for hod in range(24):
            self.hour = (self.day - 1) * 24 + hod
            self.ledger.hour = self.hour
            self.produce(hod)
            self.payroll(hod)
            self.market_batch(hod)
            if hod == 23:
                self.food_relief()
                self.expenses_and_prices()
                self.consume_and_spoil()
                self.imports_and_exports()
                self.consider_housing()
                self.day_consumed = Counter({h.id: h.food_received - before[h.id] for h in self.households})
            self.ledger.check()
            self.stocks.check()
            assert not self.market.orders
            self.checks += 1
            self.min_city_cash = min(self.min_city_cash, self.ledger.balances["city"])
            if self.record_hourly:
                self.hourly.append(self.metrics())
        self.daily.append(self.metrics())
        return self.daily[-1]

    def run(self):
        while self.day < self.config["days"]:
            self.step_day()
        self.event("run_completed", "Simulation terminée, invariants vérifiés à chaque heure", checks=self.checks)
        return self

    def newcomer_cohorts(self):
        groups = defaultdict(list)
        histories = defaultdict(list)
        for row in self.household_daily:
            histories[row["household"]].append(row)
        for h in self.residents():
            if not h.id.startswith("new"):
                continue
            last = histories[h.id][-30:]
            first = histories[h.id][:30]
            income = sum(r["income_cents"] for r in last)
            spent = sum(r["essential_spending_cents"] for r in last)
            waiting = self.first_wage_day.get(h.id, self.config["days"] + 1) - h.arrival
            groups[h.arrival].append({"cash": self.ledger.balances[h.id], "cover": income / spent if spent else 0,
                                      "initial_cover": sum(r["income_cents"] for r in first) / max(1, sum(r["essential_spending_cents"] for r in first)),
                                      "food_access": 1 - sum(r["food_missing_units"] for r in histories[h.id]) / max(1, 2 * sum(r["mode"] != "sleep" for r in histories[h.id])),
                                      "first_wage_wait": waiting, "housing_wait": h.housed_day - h.arrival if h.housed_day else self.config["days"] - h.arrival + 1,
                                      "reserve_days": self.ledger.balances[h.id] / max(1, spent / max(1, len(last)))})
        return [{"arrival_day": day, "households": len(group), "cash_median_cents": statistics.median(r["cash"] for r in group),
                 "essential_cover_median": statistics.median(r["cover"] for r in group),
                 "initial_cover_median": statistics.median(r["initial_cover"] for r in group),
                 "food_access_minimum": min(r["food_access"] for r in group),
                 "reserve_days_median": statistics.median(r["reserve_days"] for r in group),
                 "first_wage_wait_max_days": max(r["first_wage_wait"] for r in group),
                 "housing_wait_max_days": max(r["housing_wait"] for r in group)} for day, group in sorted(groups.items())]

    def summary(self):
        result = super().summary()
        cohorts = self.newcomer_cohorts()
        criteria = self.settings["criteria"]
        original_operating = sum(b.id in self.original_firms and b.mode not in ("sleep", "insolvent") for b in self.businesses)
        result.update({"model": "welcoming-v3", "job_expansions": self.job_expansions,
                       "existing_businesses_operating": original_operating,
                       "business_surplus_tax_cents": self.ledger.reason_totals["retained_business_surplus_tax"],
                       "newcomer_cohorts": cohorts, "gameplay_required_daily_actions": 0})
        result["criteria"].update({
            "first_income": all(c["first_wage_wait_max_days"] <= criteria["first_wage_max_days"] for c in cohorts),
            "housing_delay": all(c["housing_wait_max_days"] <= criteria["housing_wait_max_days"] for c in cohorts),
            "newcomer_budget": all(c["essential_cover_median"] >= criteria["newcomer_essential_cover_minimum"] for c in cohorts),
            "newcomer_initial_margin": all(c["initial_cover_median"] >= criteria["newcomer_initial_cover_minimum"] for c in cohorts),
            "newcomer_food": all(c["food_access_minimum"] >= criteria["newcomer_food_access_minimum"] for c in cohorts),
            "newcomer_reserve": all(c["reserve_days_median"] >= criteria["newcomer_reserve_minimum_days"] for c in cohorts),
            "existing_businesses": original_operating >= criteria["existing_businesses_operating_minimum"],
        })
        result["all_criteria_met"] = all(result["criteria"].values())
        return result
