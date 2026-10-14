"""Annual experiments with explicit policy variants; the first engine stays intact."""
from __future__ import annotations

import copy
import math
from collections import Counter, defaultdict

from .engine import Business, Household, Ledger, RuleError, Simulation, gini


class TrackingLedger(Ledger):
    def __init__(self, balances, retain_history):
        super().__init__(balances)
        self.retain_history = retain_history
        self.reason_totals = Counter()
        self.daily_flows = defaultdict(Counter)
        self.initial_balances = dict(balances)

    def transfer(self, source, target, cents, reason, command=None):
        changed = super().transfer(source, target, cents, reason, command)
        if changed and cents:
            self.reason_totals[reason] += cents
            if reason not in ("order_reservation", "order_refund"):
                origin = "market_escrow" if source.startswith("escrow:") else source
                self.daily_flows[self.hour // 24 + 1][(origin, target, reason)] += cents
        if not self.retain_history:
            self.history.clear()
        return changed

    def issue(self, target, cents, reason):
        super().issue(target, cents, reason)
        self.reason_totals[reason] += cents
        self.daily_flows[self.hour // 24 + 1][("issuance", target, reason)] += cents
        if not self.retain_history:
            self.history.clear()


class ExtendedSimulation(Simulation):
    def __init__(self, base, experiment, scenario="reference", policy="balanced", seed=None, detailed=False):
        self.experiment = copy.deepcopy(experiment)
        if scenario not in experiment["scenarios"] or policy not in experiment["policies"]:
            raise RuleError("Scénario ou politique étendue inconnu")
        self.policy = policy
        self.rules = experiment["policies"][policy]
        self.schedule = copy.deepcopy(experiment["scenarios"][scenario])
        config = copy.deepcopy(base)
        config["days"] = experiment["days"]
        config["seed"] = experiment["seed"] if seed is None else seed
        if self.rules["finance"]:
            config["public_contract_cents_per_worker_day"] = 1600
        super().__init__(config, "concentration" if scenario == "concentration" else "reference", seed, record_hourly=detailed)
        self.scenario = scenario
        self.ledger = TrackingLedger(self.ledger.balances, detailed)
        self.market.ledger = self.ledger
        self.nominal = copy.deepcopy(self.config)
        self.tourists = {}
        self.visitor_history = []
        self.visitor_sequence = 0
        self.growth_project = None
        self.growth_pressure = self.growth_completed = 0
        self.grant_days = Counter()
        self.improvements = Counter()
        self.price_history = defaultdict(list)
        self.sales_history = defaultdict(list)
        self.municipal_arrears = self.private_arrears = 0
        self.funding_blocks = Counter()
        self.rejected_abuses = 0
        self.technology = set()
        self.last_modes = {}
        self.day_observations = []
        self.household_daily = []
        self.last_food_missed = Counter()
        self.essential_seller_volumes = Counter()
        self.executed_events = set()
        self.essential_purchase_cost = Counter()
        self.essential_purchase_quantity = Counter()
        self.starting_firm_cash = {b.id: self.ledger.balances[b.id] for b in self.businesses}
        self.validate_extended()
        if self.rules["distribution"]:
            holdings = Counter()
            for b in self.businesses:
                if b.owner:
                    holdings[b.owner] += 1
                    if holdings[b.owner] > experiment["max_businesses_per_owner"]:
                        self.event("ownership_limit", "Détention initiale réaffectée à une entreprise sans propriétaire joueur", business=b.id, former_owner=b.owner)
                        b.owner = None

    def validate_extended(self):
        e = self.experiment
        for key in ("tourism_interval_days", "tourism_stay_days", "discretionary_interval_days", "growth_pressure_days", "growth_project_days", "season_length_days"):
            if not isinstance(e[key], int) or e[key] <= 0:
                raise RuleError(f"Paramètre étendu invalide : {key}")
        if not 0 <= e["season_amplitude"] < 1 or not 0 <= e["storage_spoil_multiplier"] <= 1:
            raise RuleError("Saison ou conservation invalide")
        for key in ("worker_profit_share_basis_points", "owner_dividend_share_basis_points", "wealth_tax_weekly_basis_points"):
            if not isinstance(e[key], int) or not 0 <= e[key] <= 10000:
                raise RuleError("Répartition invalide")
        if e["worker_profit_share_basis_points"] + e["owner_dividend_share_basis_points"] > 10000:
            raise RuleError("Répartition supérieure au bénéfice disponible")
        for event in self.schedule:
            if event["day"] < 1 or event.get("end", event["day"]) < event["day"]:
                raise RuleError("Calendrier invalide")
            if event["kind"] not in {"arrivals", "absence", "shortage", "injection", "transport", "external_stop", "modernization", "municipal_abuse", "economic_abuse"}:
                raise RuleError("Événement inconnu")

    def residents(self):
        return [h for h in self.households if h.id not in self.tourists]

    def active_effects(self):
        return [e for e in self.schedule if e["day"] <= self.day <= e.get("end", e["day"])]

    def government_spend(self, command, amount, target, purpose, approved=False, conflict=False):
        if purpose == "business_expansion":
            if not approved or conflict or target != "investment_escrow":
                raise RuleError("Investissement municipal non autorisé")
            return self.ledger.transfer("city", target, amount, "municipal:business_expansion", command)
        return super().government_spend(command, amount, target, purpose, approved, conflict)

    def apply_events(self):
        # Common deliveries and construction use the first engine, without its short timetable.
        self.essential_purchase_cost.clear()
        self.essential_purchase_quantity.clear()
        before_housing = self.housing
        name = self.scenario
        self.scenario = "reference"
        super().apply_events()
        self.scenario = name
        e, c = self.experiment, self.config
        if self.rules["growth"] and self.housing > before_housing:
            c["public_job_capacity"] += e["growth_public_jobs_per_housing_project"]
        for key in ("import_daily_limit_per_product", "import_delay_days", "public_contract_cents_per_worker_day", "material_export_daily_limit"):
            c[key] = self.nominal[key]
        self.market.capacity = self.nominal["delivery_capacity_per_batch"]
        self.weather *= 1 + e["season_amplitude"] * math.sin(2 * math.pi * (self.day - 1) / e["season_length_days"])
        for index, event in enumerate(self.schedule):
            kind = event["kind"]
            if self.day == event["day"] and index not in self.executed_events:
                self.executed_events.add(index)
                self.execute_event(event)
            if self.day == event.get("end", -2) + 1:
                if kind == "absence":
                    for h in self.households:
                        if h.id in event["households"]:
                            h.absence_start = None
                self.event("stress_ended", "Fin d'un événement programmé", kind=kind)
            if event["day"] <= self.day <= event.get("end", event["day"]):
                if kind == "shortage":
                    self.weather *= event["factor"]
                elif kind == "transport":
                    self.market.capacity = event["capacity"]
                    c["import_delay_days"] = event["import_delay"]
                elif kind == "external_stop":
                    c["public_contract_cents_per_worker_day"] = 0
                    c["material_export_daily_limit"] = 0
                    c["import_daily_limit_per_product"] = 0
        for h in list(self.households):
            if h.id in self.tourists and self.day >= self.tourists[h.id]["departure"]:
                self.leave_visitor(h)
        if e["tourism_party_size"] and (self.day - 1) % e["tourism_interval_days"] == 0:
            for _ in range(e["tourism_party_size"]):
                if self.ledger.balances["external"] < e["tourism_budget_cents"]:
                    break
                self.visitor_sequence += 1
                id = f"visitor{self.visitor_sequence:04d}"
                h = Household(id, "PNJ de passage", arrival=self.day)
                self.households.append(h)
                self.ledger.balances[id] = 0
                self.ledger.transfer("external", id, e["tourism_budget_cents"], "visitor_budget")
                self.household_initial_cash[id] = e["tourism_budget_cents"]
                self.tourists[id] = {"departure": self.day + e["tourism_stay_days"], "endowment_cents": e["tourism_budget_cents"]}
                self.event("visitor_arrival", "Visiteur avec budget extérieur fini", household=id)
        if self.growth_project and self.day >= self.growth_project["completion"]:
            self.complete_growth()
        if self.rules["storage"]:
            active = sum(h.mode != "sleep" for h in self.households)
            for p in ("bread", "vegetables"):
                c["reserve_target_" + p] = math.ceil(active * e["target_reserve_days"])

    def execute_event(self, event):
        kind = event["kind"]
        self.event("stress_started", "Événement programmé", **{k: v for k, v in event.items() if k != "day"})
        if kind == "arrivals":
            for _ in range(event["count"]):
                id = f"new{sum(h.id.startswith('new') for h in self.households) + 1:03d}"
                self.households.append(Household(id, "nouvel arrivant", arrival=self.day))
                self.ledger.balances[id] = 0
                self.ledger.issue(id, self.config["initial_household_cash_cents"], "arrival_endowment")
                self.household_initial_cash[id] = self.config["initial_household_cash_cents"]
        elif kind == "absence":
            for h in self.households:
                if h.id in event["households"]:
                    h.absence_start = self.hour
        elif kind == "injection":
            for h in self.residents():
                self.ledger.issue(h.id, event["cents_per_household"], "experimental_injection")
        elif kind == "modernization":
            for b in self.businesses:
                if b.product in ("grain", "flour") and self.ledger.balances[b.id] >= self.experiment["modernization_cost_cents"]:
                    self.ledger.transfer(b.id, "external", self.experiment["modernization_cost_cents"], "technology_investment")
                    b.daily_capacity = round(b.daily_capacity * self.experiment["modernization_capacity_multiplier"])
                    self.technology.add(b.id)
                    self.event("technology_installed", "Capacité accrue, emplois et recette conservés", business=b.id, capacity=b.daily_capacity)
        elif kind == "municipal_abuse":
            self.probe_municipal_abuse()
        elif kind == "economic_abuse":
            self.probe_economic_abuse()

    def leave_visitor(self, h):
        refund = self.ledger.balances[h.id]
        self.ledger.transfer(h.id, "external", refund, "visitor_unused_budget_return")
        for product, quantity in list(self.stocks.items[h.id].items()):
            self.stocks.move(h.id, "city", product, quantity)
        self.visitor_history.append({"household": h.id, "arrival": h.arrival, "departure": self.day,
                                     "food_missing_units": h.missed_food, "budget_refunded_cents": refund})
        self.households.remove(h)
        del self.tourists[h.id]
        self.event("visitor_departure", "Budget non utilisé rendu à l'extérieur", household=h.id, refund_cents=refund)

    def routines(self):
        visitors = [h for h in self.households if h.id in self.tourists]
        self.households = self.residents()
        super().routines()
        self.households.extend(visitors)
        if self.rules["finance"]:
            e = self.experiment
            if not any(x["kind"] == "external_stop" for x in self.active_effects()):
                staff = sum(h.employer == "city" for h in self.households)
                target = e["municipal_target_cash_cents"]
                if self.rules["growth"]:
                    homes = math.ceil(self.housing_pressure() / self.config["housing_project_units"])
                    unemployed = sum(h.employer is None and h.mode != "sleep" for h in self.residents())
                    target += homes * (self.config["housing_project_labor_cents"] + self.config["housing_project_materials"] * self.config["products"]["materials"]["base_price_cents"])
                    target += math.ceil(unemployed / 7) * (4 * e["growth_firm_cash_cents"] + e["growth_labor_cents"])
                prior = list(range(max(1, self.day - 7), self.day))
                local_income = sum(v for d in prior for (_, target_account, reason), v in self.ledger.daily_flows[d].items()
                                   if target_account == "city" and reason != "public_service_export") / max(1, len(prior))
                prior_imports = sum(v for d in prior for (source, _, reason), v in self.ledger.daily_flows[d].items()
                                    if source == "city" and reason == "municipal:food_import") / max(1, len(prior))
                daily_gap = staff * self.config["daily_wage_cents"] + prior_imports + (e["storage_daily_cost_cents"] if self.rules["storage"] else 0) - local_income
                daily_gap += (target - self.ledger.balances["city"]) / e["municipal_target_adjustment_days"]
                daily_contract = min(e["public_contract_daily_cap_cents"], max(0, round(daily_gap)))
                self.config["public_contract_cents_per_worker_day"] = min(self.nominal["public_contract_cents_per_worker_day"], daily_contract // max(1, staff))
            recipients = [h for h in self.residents() if h.mode == "normal" and self.grant_days[h.id] < e["subsistence_max_days_per_household"] and
                          self.ledger.balances[h.id] < self.essential_reserve(h)]
            # Poorer households have priority, with seeded tie ordering.
            self.rng.shuffle(recipients)
            recipients.sort(key=lambda h: self.ledger.balances[h.id])
            budget = min(e["subsistence_daily_budget_cents"], max(0, self.ledger.balances["city"] - self.commitment_reserve()))
            for h in recipients:
                amount = min(e["subsistence_daily_cents"], budget)
                if not amount:
                    break
                self.ledger.transfer("city", h.id, amount, "subsistence_grant")
                h.income += amount
                self.grant_days[h.id] += 1
                budget -= amount
        self.last_modes = {h.id: h.mode for h in self.households}

    def produce(self, hod):
        name = self.scenario
        self.scenario = "reference"  # Agricultural shocks already enter the day's weather.
        super().produce(hod)
        self.scenario = name

    def payroll(self, hod):
        c = self.config
        old = c["public_contract_cents_per_worker_day"]
        staff = sum(h.employer == "city" for h in self.households)
        c["public_contract_cents_per_worker_day"] = min(old, self.experiment["public_contract_daily_cap_cents"] // max(1, staff))
        super().payroll(hod)
        c["public_contract_cents_per_worker_day"] = old

    def market_batch(self, hod):
        # Insolvent businesses may liquidate their own stock, then recover next day.
        liquidating = []
        if self.rules["growth"]:
            for b in self.businesses:
                if b.mode == "insolvent":
                    liquidating.append(b)
                    b.mode = "liquidating"
        before = len(self.market.trades)
        super().market_batch(hod)
        for b in liquidating:
            b.mode = "insolvent"
        self.observe_trades(self.market.trades[before:])
        if self.hour % self.config["market_period_hours"]:
            return
        capacity = self.market.capacity
        self.market.capacity = max(0, capacity - self.market.delivered)
        if hod == 12 and self.day % self.experiment["discretionary_interval_days"] == 0:
            self.discretionary_market()
        if hod == 14:
            self.opportunist_market()
        self.market.capacity = capacity

    def observe_trades(self, trades):
        ids = {h.id for h in self.households}
        for _, buyer, _, product, quantity, price, fee in trades:
            if buyer in ids and product in ("bread", "vegetables"):
                self.essential_purchase_cost[product] += quantity * price
                self.essential_purchase_quantity[product] += quantity
        for _, buyer, seller, product, quantity, _, _ in trades:
            if buyer in ids and product in ("bread", "vegetables"):
                b = next((b for b in self.businesses if b.id == seller), None)
                self.essential_seller_volumes[b.owner or b.id if b else seller] += quantity

    def essential_reserve(self, h):
        basket = sum(min((b.price for b in self.businesses if b.product == p and b.mode not in ("sleep", "insolvent")), default=self.config["products"][p]["base_price_cents"]) for p in ("bread", "vegetables"))
        return (basket + self.config["daily_rent_cents"]) * self.experiment["discretionary_cash_reserve_days"]

    def discretionary_market(self):
        workshop = next(b for b in self.businesses if b.product == "materials")
        if workshop.mode in ("sleep", "insolvent"):
            return
        available = self.stocks.items[workshop.id]["materials"]
        if self.rules["growth"] and self.housing_pressure():
            available = max(0, available - self.config["housing_project_materials"])
        if not available:
            return
        self.market.place(f"{self.hour}:discretionary:sell", workshop.id, "materials", available, workshop.price, workshop.location, "sell")
        ids = {h.id: h for h in self.residents()}
        for index, h in enumerate(ids.values()):
            if h.mode != "normal":
                continue
            surplus = max(0, self.ledger.balances[h.id] - self.essential_reserve(h))
            quantity = min(self.experiment["discretionary_max_material_units"], surplus // (workshop.price + 6 * self.market.fee))
            if quantity:
                self.market.place(f"{self.hour}:improvement:{h.id}", h.id, "materials", quantity, workshop.price, index % 7, "buy")
        for _, buyer, seller, product, quantity, price, fee in self.market.clear():
            self.stocks.take(buyer, product, quantity, "household_improvement")
            self.improvements[buyer] += quantity
            workshop.revenue += quantity * price
            workshop.sales += quantity
            self.ledger.transfer(seller, "city", quantity * price * self.config["sales_tax_basis_points"] // 10000, "sales_tax")

    def opportunist_market(self):
        h = next((h for h in self.households if h.profile == "opportuniste" and h.mode == "normal"), None)
        if not h:
            return
        max_units = 1 if self.rules["distribution"] else self.experiment["hoarding_units_per_product"]
        for p in ("bread", "vegetables"):
            existing = self.stocks.items[h.id][p]
            if existing > 1:
                price = round(min((b.price for b in self.businesses if b.product == p), default=self.config["products"][p]["base_price_cents"]) * 1.1)
                self.market.place(f"{self.hour}:hoard:sell:{p}", h.id, p, existing - 1, price, 3, "sell")
            sellers = [b for b in self.businesses if b.product == p and b.mode not in ("sleep", "insolvent") and self.stocks.items[b.id][p]]
            for b in sellers:
                self.market.place(f"{self.hour}:hoard:offer:{b.id}", b.id, p, self.stocks.items[b.id][p], b.price, b.location, "sell")
            price = min((b.price for b in sellers), default=0)
            surplus = max(0, self.ledger.balances[h.id] - self.essential_reserve(h))
            qty = min(max(0, max_units - existing), surplus // (price + 6 * self.market.fee)) if price else 0
            if qty:
                self.market.place(f"{self.hour}:hoard:buy:{p}", h.id, p, qty, price, 3, "buy")
        # Only surplus-budget households can buy resale goods; no artificial guaranteed outlet.
        for i, buyer in enumerate(self.residents()):
            if buyer.id == h.id or buyer.mode != "normal":
                continue
            for p in ("bread", "vegetables"):
                if not self.stocks.items[buyer.id][p]:
                    price = round(self.config["products"][p]["base_price_cents"] * self.config["price_maximum_multiplier"])
                    if self.ledger.balances[buyer.id] >= price + 6 * self.market.fee:
                        self.market.place(f"{self.hour}:early:{buyer.id}:{p}", buyer.id, p, 1, price, i % 7, "buy")
        trades = self.market.clear()
        self.observe_trades(trades)
        households = {x.id: x for x in self.households}
        for _, buyer, seller, p, quantity, price, fee in trades:
            households[buyer].essential_spending += quantity * price + fee
            if seller == h.id:
                h.income += quantity * price - quantity * price * self.config["sales_tax_basis_points"] // 10000
            else:
                b = next(b for b in self.businesses if b.id == seller)
                b.revenue += quantity * price
                b.sales += quantity
                self.daily_sales[(seller, p)] += quantity
            self.ledger.transfer(seller, "city", quantity * price * self.config["sales_tax_basis_points"] // 10000, "sales_tax")

    def expenses_and_prices(self):
        e, c = self.experiment, self.config
        # Legacy expenses/prices remain a control. Disable only its weekly dividends
        # when profit distribution is being compared.
        owners = [(b, b.owner) for b in self.businesses]
        if self.rules["distribution"]:
            for b, _ in owners:
                b.owner = None
        super().expenses_and_prices()
        for b, owner in owners:
            b.owner = owner
        for h in self.households:
            if h.id in self.tourists:
                amount = min(e["tourism_room_daily_cents"], self.ledger.balances[h.id])
                self.ledger.transfer(h.id, "city", amount, "visitor_room")
                h.essential_spending += amount
        if self.rules["public_prices"]:
            self.public_prices()
        if self.rules["storage"]:
            amount = min(e["storage_daily_cost_cents"], self.ledger.balances["city"])
            self.ledger.transfer("city", "external", amount, "reserve_storage_service")
            self.storage_paid = amount == e["storage_daily_cost_cents"]
        if self.rules["distribution"] and self.day % 7 == 0:
            self.distribute_profits()
        for b in self.businesses:
            self.price_history[b.id].append(b.price)
            self.sales_history[b.id].append(self.daily_sales[(b.id, b.product)])
        if self.day % 7 == 0:
            for h in self.residents():
                if h.profile == "coopérateur" and h.mode == "normal":
                    amount = min(200, max(0, self.ledger.balances[h.id] - self.essential_reserve(h)))
                    if amount:
                        self.ledger.transfer(h.id, "city", amount, "voluntary_contribution")

    def public_prices(self):
        e, c = self.experiment, self.config
        active = sum(h.mode != "sleep" for h in self.households)
        for b in self.businesses:
            if b.mode in ("sleep", "insolvent") or b.product == "materials":
                continue
            competitors = [x for x in self.businesses if x.product == b.product and x.mode not in ("sleep", "insolvent")]
            public_stock = sum(self.stocks.items[x.id][b.product] for x in competitors)
            expected_sales = max(1, active / max(1, len(competitors)))
            input_price = 0
            if b.input:
                quotes = [x.price for x in self.businesses if x.product == b.input and x.mode not in ("sleep", "insolvent")]
                input_price = min(quotes, default=c["products"][b.input]["base_price_cents"])
            payroll = len(b.workers) * c["daily_wage_cents"]
            cost = input_price + (payroll + b.maintenance) / expected_sales
            loss = c["products"][b.product]["daily_spoil_basis_points"] / 10000
            target = round(cost / (1 - min(.4, loss)) / (1 - c["sales_tax_basis_points"] / 10000) * e["essential_price_markup"])
            if public_stock < active * .25:
                target = round(target * 1.1)
            # Public quotes and own production costs, with a bounded daily adjustment.
            previous = self.price_history[b.id][-1] if self.price_history[b.id] else c["products"][b.product]["base_price_cents"]
            fraction = e["price_adjustment_max_fraction"]
            target = max(round(previous * (1 - fraction)), min(round(previous * (1 + fraction)), target))
            base = c["products"][b.product]["base_price_cents"]
            b.price = max(round(base * .8), min(round(base * c["price_maximum_multiplier"]), target))

    def distribute_profits(self):
        e, c = self.experiment, self.config
        for b in self.businesses:
            if b.mode != "normal":
                continue
            reserve = max(self.starting_firm_cash[b.id], b.jobs * c["daily_wage_cents"] * 14)
            surplus = max(0, self.ledger.balances[b.id] - reserve)
            workers = [h for h in b.workers if h.mode == "normal"]
            pool = surplus * e["worker_profit_share_basis_points"] // 10000
            for h in workers:
                amount = pool // max(1, len(workers))
                if amount:
                    self.ledger.transfer(b.id, h.id, amount, "worker_profit_share")
                    h.income += amount
            owner = next((h for h in self.households if h.id == b.owner and h.mode == "normal"), None)
            if owner:
                amount = surplus * e["owner_dividend_share_basis_points"] // 10000
                if amount:
                    self.ledger.transfer(b.id, owner.id, amount, "dividend")
                    owner.income += amount
        for h in self.residents():
            if h.mode == "sleep":
                continue
            tax = max(0, self.ledger.balances[h.id] - e["wealth_tax_threshold_cents"]) * e["wealth_tax_weekly_basis_points"] // 10000
            if tax:
                self.ledger.transfer(h.id, "city", tax, "wealth_tax")

    def consume_and_spoil(self):
        # Scale only municipal storage losses; private conservation is unchanged.
        rates = {p: self.config["products"][p]["daily_spoil_basis_points"] for p in ("bread", "vegetables")}
        city_inventory = Counter(self.stocks.items["city"])
        if self.rules["storage"] and self.storage_paid:
            for p, qty in city_inventory.items():
                self.stocks.move("city", "cold_storage", p, qty)
            cold = self.stocks.items.pop("cold_storage")
            super().consume_and_spoil()
            self.stocks.items["cold_storage"] = cold
            for p, qty in list(cold.items()):
                rate = self.config["products"][p]["daily_spoil_basis_points"] / 10000 * self.experiment["storage_spoil_multiplier"]
                expected = qty * rate
                loss = math.floor(expected) + (self.spoilage_rng.random() < expected % 1)
                self.stocks.take("cold_storage", p, loss, "municipal_storage_spoilage")
                self.stocks.move("cold_storage", "city", p, qty - loss)
        else:
            super().consume_and_spoil()

    def commitment_reserve(self):
        public = sum(h.employer == "city" and h.mode != "sleep" for h in self.households)
        return public * self.config["daily_wage_cents"] * self.experiment["municipal_commitment_reserve_days"]

    def housing_pressure(self):
        return sum(not h.housing and h.mode != "sleep" for h in self.residents())

    def imports_and_exports(self):
        if self.rules["growth"] and (self.housing_pressure() or self.growth_pressure):
            b = next(b for b in self.businesses if b.product == "materials")
            needed = max(self.config["housing_project_materials"], self.experiment["growth_materials"])
            old = self.config["material_export_daily_limit"]
            self.config["material_export_daily_limit"] = min(old, max(0, self.stocks.items[b.id]["materials"] - needed))
            super().imports_and_exports()
            self.config["material_export_daily_limit"] = old
        else:
            super().imports_and_exports()

    def consider_housing(self):
        visitors = [h for h in self.households if h.id in self.tourists]
        self.households = self.residents()
        paid = sum(amount for (_, _, reason), amount in self.ledger.daily_flows[self.day].items() if reason == "wage")
        was_project = self.project
        can_fund = not self.rules["growth"] or self.ledger.balances["city"] >= self.commitment_reserve() + self.config["housing_project_labor_cents"] + self.config["housing_project_materials"] * self.config["products"]["materials"]["base_price_cents"]
        if paid and can_fund:
            super().consider_housing()
        else:
            self.funding_blocks["housing"] += bool(self.housing_pressure())
        self.households.extend(visitors)
        if not was_project and self.project:
            self.ledger.transfer(next(b.id for b in self.businesses if b.product == "materials"), "city", self.config["housing_project_materials"] * self.config["products"]["materials"]["base_price_cents"] * self.config["sales_tax_basis_points"] // 10000, "sales_tax")
        if self.rules["growth"]:
            self.consider_growth()
        self.observations()

    def consider_growth(self):
        e, c = self.experiment, self.config
        active = [h for h in self.residents() if h.mode != "sleep"]
        unemployed = sum(not h.employer for h in active)
        useful = sum(amount for (_, _, reason), amount in self.ledger.daily_flows[self.day].items() if reason == "wage") >= c["daily_wage_cents"] * len(active) * .55
        self.growth_pressure = self.growth_pressure + 1 if unemployed >= 4 and useful else 0
        if self.growth_project or self.growth_pressure < e["growth_pressure_days"] or self.growth_completed >= e["growth_max_bundles"]:
            return
        workshop = next(b for b in self.businesses if b.product == "materials")
        material_cost = e["growth_materials"] * workshop.price
        total = 4 * e["growth_firm_cash_cents"] + e["growth_labor_cents"] + material_cost
        if self.stocks.items[workshop.id]["materials"] < e["growth_materials"] or self.ledger.balances["city"] < total + self.commitment_reserve():
            self.funding_blocks["business_expansion"] += 1
            return
        self.government_spend(f"business_expansion:{self.day}", total, "investment_escrow", "business_expansion", approved=True)
        self.ledger.transfer("investment_escrow", workshop.id, material_cost, "growth_materials")
        workshop.revenue += material_cost
        workshop.sales += e["growth_materials"]
        self.ledger.transfer(workshop.id, "city", material_cost * c["sales_tax_basis_points"] // 10000, "sales_tax")
        self.stocks.take(workshop.id, "materials", e["growth_materials"], "business_construction")
        self.ledger.transfer("investment_escrow", "external", e["growth_labor_cents"], "growth_construction_contract")
        self.growth_project = {"completion": self.day + e["growth_project_days"], "cash_per_firm": e["growth_firm_cash_cents"], "total_cost_cents": total}
        self.event("business_expansion_started", "Chaîne alimentaire collective financée", **self.growth_project)
        self.growth_pressure = 0

    def complete_growth(self):
        self.growth_completed += 1
        specs = [("grain", 30, 2, None), ("flour", 30, 1, "grain"), ("bread", 30, 2, "flour"), ("vegetables", 30, 2, None)]
        for product, capacity, jobs, input in specs:
            id = f"cooperative{self.growth_completed}_{product}"
            b = Business(id, product, capacity, jobs, self.growth_completed % 7, 150, input)
            b.price = self.config["products"][product]["base_price_cents"]
            self.businesses.append(b)
            self.ledger.balances[id] = 0
            self.ledger.transfer("investment_escrow", id, self.growth_project["cash_per_firm"], "business_starting_capital")
            self.starting_firm_cash[id] = self.growth_project["cash_per_firm"]
        self.event("business_expansion_completed", "Sept emplois et quatre entreprises alimentaires ouverts", bundle=self.growth_completed)
        self.growth_project = None

    def probe_municipal_abuse(self):
        probes = [("gift", 10000, "player08", "housing", True, False),
                  ("conflict", 10000, "project_escrow", "housing", True, True),
                  ("rights", 10000, "project_escrow", "housing", False, False),
                  ("budget", self.ledger.balances["city"] + 1, "project_escrow", "housing", True, False)]
        for args in probes:
            before = dict(self.ledger.balances)
            try:
                self.government_spend(*args)
            except RuleError as error:
                assert before == self.ledger.balances
                self.rejected_abuses += 1
                self.event("abuse_rejected", str(error), command=args[0])
            else:
                raise AssertionError("Abus municipal accepté")

    def probe_economic_abuse(self):
        buyer = self.residents()[0].id
        seller = next(b.id for b in self.businesses if self.stocks.items[b.id][b.product] > 0)
        product = next(b.product for b in self.businesses if b.id == seller)
        qty = self.stocks.items[seller][product]
        self.market.place("probe:sell", seller, product, qty, 1, 0, "sell")
        try:
            self.market.place("probe:double_stock", seller, product, 1, 1, 0, "sell")
        except RuleError:
            self.rejected_abuses += 1
        else:
            raise AssertionError("Double réservation de stock acceptée")
        amount = self.ledger.balances[buyer]
        if amount >= 7:
            quantity = amount // 7
            self.market.place("probe:buy", buyer, "materials", quantity, 1, 0, "buy")
            before = dict(self.ledger.balances)
            assert not self.market.place("probe:buy", buyer, "materials", quantity, 1, 0, "buy")
            assert before == self.ledger.balances
            self.rejected_abuses += 1
            try:
                self.market.place("probe:double_funds", buyer, "materials", quantity, 1, 0, "buy")
            except RuleError:
                self.rejected_abuses += 1
            else:
                raise AssertionError("Double réservation de fonds acceptée")
        # Disjoint product avoids accidentally buying the probe seller's goods.
        self.market.orders.pop("probe:sell")
        self.stocks.move("escrow:probe:sell", seller, product, qty)
        self.stocks.items.pop("escrow:probe:sell", None)
        self.market.clear()
        self.event("abuse_rejected", "Double réservation et répétition refusées", rejected=self.rejected_abuses)

    def observations(self):
        flows = self.ledger.daily_flows[self.day]
        residents = {h.id: h for h in self.residents()}
        paid = Counter()
        unpaid = Counter()
        for (source, target, reason), cents in flows.items():
            if reason == "wage" and target in residents:
                paid[target] += cents
        for h in self.residents():
            expected = (self.config["daily_wage_cents"] // 8 // (2 if h.mode == "reduced" else 1)) * 8 if h.employer and h.mode != "sleep" else 0
            gap = max(0, expected - paid[h.id])
            if h.employer == "city":
                self.municipal_arrears += gap
            else:
                self.private_arrears += gap
            if h.mode == "sleep":
                assert paid[h.id] == 0
                assert not any(target == h.id and reason in ("dividend", "worker_profit_share", "subsistence_grant") for (_, target, reason) in flows)
            self.household_daily.append({
                "day": self.day, "household": h.id, "profile": h.profile, "arrival_day": h.arrival,
                "mode": h.mode, "cash_cents": self.ledger.balances[h.id], "housed": h.housing,
                "employer": h.employer, "paid_wages_cents": paid[h.id],
                "food_missing_units": h.missed_food - self.last_food_missed[h.id],
            })
            self.last_food_missed[h.id] = h.missed_food
        self.day_observations.append({
            "paid_workers": sum(paid[h.id] > 0 for h in self.residents()),
            "paid_full_time_equivalents": sum(paid.values()) / max(1, self.config["daily_wage_cents"]),
            "public_wages_paid_cents": sum(cents for (source, _, reason), cents in flows.items() if reason == "wage" and source == "city"),
            "private_wages_paid_cents": sum(cents for (source, _, reason), cents in flows.items() if reason == "wage" and source != "city"),
            "city_income_cents": sum(v for (_, target, reason), v in flows.items() if target == "city" and reason not in ("order_reservation", "order_refund")),
            "city_spending_cents": sum(v for (source, _, reason), v in flows.items() if source == "city" and reason not in ("order_reservation", "order_refund")),
        })
        # Detailed batches keep their full ledger; summary-only runs retain daily aggregates.
        if not self.ledger.retain_history:
            self.market.trades.clear()

    def metrics(self):
        row = super().metrics()
        residents = [h for h in self.residents() if h.mode != "sleep"]
        row.update({
            "resident_population": len(self.residents()), "visitors": len(self.tourists),
            "unhoused": sum(not h.housing for h in self.residents()),
            "cash_gini_residents": gini([self.ledger.balances[h.id] for h in self.residents()]),
            "asset_gini_residents": gini(self.asset_values()),
            "active_residents": len(residents), "growth_bundles_completed": self.growth_completed,
            "municipal_unpaid_wages_cents": self.municipal_arrears,
            "households_under_essential_reserve": sum(self.ledger.balances[h.id] < self.essential_reserve(h) for h in residents),
            "technology_installed": len(self.technology),
        })
        if len(self.day_observations) >= self.day:
            row.update(self.day_observations[self.day - 1])
            row["paid_employment_rate"] = row["paid_full_time_equivalents"] / max(1, len(residents))
        else:
            row.update({k: 0 for k in ("paid_workers", "paid_full_time_equivalents", "public_wages_paid_cents", "private_wages_paid_cents", "city_income_cents", "city_spending_cents", "paid_employment_rate")})
        row["actual_basket_price_cents"] = round(sum(self.essential_purchase_cost[p] / self.essential_purchase_quantity[p] for p in ("bread", "vegetables"))) if all(self.essential_purchase_quantity[p] for p in ("bread", "vegetables")) else None
        return row

    def asset_values(self):
        values = []
        for h in self.residents():
            value = self.ledger.balances[h.id]
            for b in self.businesses:
                if b.owner == h.id:
                    value += self.ledger.balances[b.id]
                    value += sum(qty * self.config["products"][p]["base_price_cents"] for p, qty in self.stocks.items[b.id].items())
            values.append(value)
        return values

    def summary(self):
        result = super().summary()
        last = self.daily[-1]
        result.update({
            "model": "annual-v2", "policy": self.policy,
            "public_import_cost_cents": self.ledger.reason_totals["municipal:food_import"],
            "municipal_unpaid_wages_cents": self.municipal_arrears,
            "private_unpaid_wages_cents": self.private_arrears,
            "paid_employment_last30": sum(r["paid_employment_rate"] for r in self.daily[-30:]) / len(self.daily[-30:]),
            "resident_population_final": len(self.residents()),
            "cash_gini_final": last["cash_gini_residents"],
            "asset_gini_final": last["asset_gini_residents"],
            "largest_essential_owner_share_year": max(self.essential_seller_volumes.values(), default=0) / max(1, sum(self.essential_seller_volumes.values())),
            "growth_bundles_completed": self.growth_completed,
            "visitor_arrivals": self.visitor_sequence,
            "visitor_net_spending_cents": self.ledger.reason_totals["visitor_budget"] - self.ledger.reason_totals["visitor_unused_budget_return"],
            "discretionary_materials_consumed": sum(self.improvements.values()),
            "subsistence_cost_cents": self.ledger.reason_totals["subsistence_grant"],
            "worker_profit_share_cents": self.ledger.reason_totals["worker_profit_share"],
            "wealth_tax_cents": self.ledger.reason_totals["wealth_tax"],
            "storage_cost_cents": self.ledger.reason_totals["reserve_storage_service"],
            "technology_installed": len(self.technology), "rejected_abuses": self.rejected_abuses,
            "budget_final_change_last30_cents": last["city_cash_cents"] - self.daily[max(0, len(self.daily) - 31)]["city_cash_cents"],
            "external_cash_final_cents": self.ledger.balances["external"],
            "housing_wait_max_days": max((h.housed_day - h.arrival if h.housed_day else self.config["days"] - h.arrival + 1 for h in self.residents()), default=0),
            "critical_food_gap_max_days": longest_streak([r["food_access_rate"] < .99 for r in self.daily]),
            "funding_blocks": dict(self.funding_blocks),
            "pending_growth": self.growth_project,
            "last30_food_access": sum(r["food_units_served"] for r in self.daily[-30:]) / max(1, sum(2 * r["active_population"] for r in self.daily[-30:])),
        })
        criteria = self.experiment["criteria"]
        result["criteria"] = {
            "food": result["food_access_rate"] >= criteria["food_access_minimum"],
            "food_gap": result["critical_food_gap_max_days"] <= criteria["food_gap_max_consecutive_days"],
            "employment": result["paid_employment_last30"] >= criteria["paid_employment_last30_minimum"],
            "housing": result["unhoused_final"] <= criteria["final_unhoused_maximum"],
            "municipal_wages": self.municipal_arrears == 0,
            "budget": self.ledger.balances["city"] >= self.commitment_reserve(),
            "inequality": result["cash_gini_final"] <= criteria["cash_gini_maximum"],
        }
        result["all_criteria_met"] = all(result["criteria"].values())
        result["recoveries"] = []
        for event in self.schedule:
            if event["kind"] not in ("shortage", "transport", "external_stop", "absence"):
                continue
            end = event["end"]
            next_stress = min((e["day"] for e in self.schedule if e["day"] > end), default=self.config["days"] + 1)
            recovery = None
            for i, row in enumerate(self.daily):
                window = self.daily[i:i + 7]
                if row["day"] > end and len(window) == 7 and window[-1]["day"] < next_stress and all(r["food_access_rate"] >= .99 and r["paid_employment_rate"] >= .8 for r in window):
                    recovery = row["day"] - end
                    break
            result["recoveries"].append({"kind": event["kind"], "end": end, "days": recovery})
        return result


def longest_streak(flags):
    best = count = 0
    for flag in flags:
        count = count + 1 if flag else 0
        best = max(best, count)
    return best
