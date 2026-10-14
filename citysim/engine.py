from __future__ import annotations

import copy
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field


SCENARIOS = {
    "reference": "Population et routines stables",
    "low_presence": "Présence connectée divisée par quatre, routines autorisées conservées",
    "arrivals": "12 arrivants au jour 20, puis 8 au jour 27",
    "departure": "6 joueurs quittent leur activité au jour 25 et reviennent au jour 70",
    "absence": "Deux propriétaires absents du jour 20 au jour 65",
    "shortage": "Production agricole à 25 % du jour 30 au jour 44 inclus",
    "concentration": "Un propriétaire contrôle initialement les deux boulangeries et une ferme maraîchère",
    "money_injection": "Dotation exceptionnelle de 600 unités à chaque ménage au jour 20",
    "combined": "Pénurie et absence des deux propriétaires",
}
PROFILES = ["salarié occasionnel", "commerçant actif", "artisan", "nouvel arrivant",
            "propriétaire", "coopérateur", "salarié régulier", "opportuniste"]


class RuleError(ValueError):
    pass


class Ledger:
    """Integer cents; every internal movement has a source, destination and cause."""

    def __init__(self, balances):
        self.balances = dict(balances)
        self.initial = sum(balances.values())
        self.created = self.removed = 0
        self.history = []
        self.commands = {}
        self.hour = 0

    def transfer(self, source, target, cents, reason, command=None):
        signature = (source, target, cents, reason)
        if command is not None and command in self.commands:
            if self.commands[command] != signature:
                raise RuleError("Commande répétée avec un contenu différent")
            return False
        if not isinstance(cents, int) or cents < 0 or source == target:
            raise RuleError("Transfert invalide")
        if self.balances.get(source, 0) < cents:
            raise RuleError("Fonds insuffisants")
        self.balances[source] -= cents
        self.balances[target] = self.balances.get(target, 0) + cents
        if command is not None:
            self.commands[command] = signature
        if cents:
            self.history.append((self.hour, source, target, cents, reason))
        return True

    def issue(self, target, cents, reason):
        if not isinstance(cents, int) or cents < 0:
            raise RuleError("Émission invalide")
        self.balances[target] += cents
        self.created += cents
        self.history.append((self.hour, "issuance", target, cents, reason))

    def check(self):
        assert all(isinstance(x, int) and x >= 0 for x in self.balances.values())
        assert sum(self.balances.values()) == self.initial + self.created - self.removed


class Stocks:
    def __init__(self, products):
        self.products = tuple(products)
        self.items = defaultdict(Counter)
        self.initial = Counter()
        self.added = Counter()
        self.taken = Counter()
        self.flows = Counter()

    def initialize(self, owner, quantities):
        self.items[owner].update(quantities)
        self.initial.update(quantities)

    def add(self, owner, product, quantity, cause):
        if not isinstance(quantity, int) or quantity < 0:
            raise RuleError("Quantité invalide")
        self.items[owner][product] += quantity
        self.added[product] += quantity
        self.flows[(product, cause)] += quantity

    def take(self, owner, product, quantity, cause):
        if not isinstance(quantity, int) or quantity < 0 or self.items[owner][product] < quantity:
            raise RuleError("Stock insuffisant ou quantité invalide")
        self.items[owner][product] -= quantity
        self.taken[product] += quantity
        self.flows[(product, cause)] += quantity

    def move(self, source, target, product, quantity):
        if not isinstance(quantity, int) or quantity < 0 or self.items[source][product] < quantity:
            raise RuleError("Stock insuffisant ou quantité invalide")
        self.items[source][product] -= quantity
        self.items[target][product] += quantity

    def check(self):
        totals = Counter()
        for items in self.items.values():
            assert all(isinstance(q, int) and q >= 0 for q in items.values())
            totals.update(items)
        for product in self.products:
            assert totals[product] == self.initial[product] + self.added[product] - self.taken[product]


@dataclass
class Order:
    id: str
    owner: str
    product: str
    quantity: int
    price: int
    location: int
    side: str
    remaining: int
    reserved: int = 0


class Market:
    """Batch settlement, escrow, distance fees and a shared delivery capacity."""

    def __init__(self, ledger, stocks, rng, capacity=180, fee=1):
        self.ledger, self.stocks, self.rng = ledger, stocks, rng
        self.capacity, self.fee = capacity, fee
        self.orders = {}
        self.seen = {}
        self.trades = []
        self.delivered = 0

    def place(self, id, owner, product, quantity, price, location, side):
        if quantity <= 0 or price <= 0 or side not in ("buy", "sell") or not 0 <= location <= 6:
            raise RuleError("Ordre invalide")
        signature = (owner, product, quantity, price, location, side)
        if id in self.seen:
            if self.seen[id] != signature:
                raise RuleError("Ordre répété avec un contenu différent")
            return False
        escrow = "escrow:" + id
        reserved = 0
        if side == "buy":
            reserved = quantity * (price + 6 * self.fee)
            self.ledger.transfer(owner, escrow, reserved, "order_reservation")
        else:
            self.stocks.move(owner, escrow, product, quantity)
        self.orders[id] = Order(id, owner, product, quantity, price, location, side, quantity, reserved)
        self.seen[id] = signature
        return True

    def clear(self):
        self.delivered = 0
        # Shuffle ties before sorting: no permanent priority for a household ID.
        orders = list(self.orders.values())
        self.rng.shuffle(orders)
        buys = sorted((o for o in orders if o.side == "buy"), key=lambda o: -o.price)
        sells = sorted((o for o in orders if o.side == "sell"), key=lambda o: o.price)
        completed = []
        for buy in buys:
            for sell in sells:
                if (sell.product != buy.product or sell.owner == buy.owner or
                        sell.price > buy.price or not buy.remaining or not sell.remaining):
                    continue
                quantity = min(buy.remaining, sell.remaining, self.capacity - self.delivered)
                if not quantity:
                    break
                fee = abs(sell.location - buy.location) * self.fee * quantity
                amount = quantity * sell.price
                self.ledger.transfer("escrow:" + buy.id, sell.owner, amount, "market:" + buy.product)
                if fee:
                    self.ledger.transfer("escrow:" + buy.id, "city", fee, "delivery")
                self.stocks.move("escrow:" + sell.id, buy.owner, buy.product, quantity)
                buy.reserved -= amount + fee
                buy.remaining -= quantity
                sell.remaining -= quantity
                self.delivered += quantity
                trade = (self.ledger.hour, buy.owner, sell.owner, buy.product, quantity, sell.price, fee)
                completed.append(trade)
                self.trades.append(trade)
        # All orders expire at the end of this batch. No sleeping player blocks stock.
        for order in self.orders.values():
            if order.side == "buy" and order.reserved:
                self.ledger.transfer("escrow:" + order.id, order.owner, order.reserved, "order_refund")
            elif order.side == "sell" and order.remaining:
                self.stocks.move("escrow:" + order.id, order.owner, order.product, order.remaining)
            self.ledger.balances.pop("escrow:" + order.id, None)
            self.stocks.items.pop("escrow:" + order.id, None)
        self.orders.clear()
        return completed


@dataclass
class Household:
    id: str
    profile: str
    arrival: int = 1
    housing: bool = False
    employer: str | None = None
    absence_start: int | None = None
    mode: str = "normal"
    connected: bool = False
    needs: int = 2
    food_received: int = 0
    missed_food: int = 0
    missed_days: int = 0
    income: int = 0
    essential_spending: int = 0
    rent_arrears: int = 0
    employed_days: int = 0
    housed_day: int | None = None
    paid_days: int = 0
    protected_income: int = 0


@dataclass
class Business:
    id: str
    product: str
    daily_capacity: int
    jobs: int
    location: int
    maintenance: int
    input: str | None = None
    owner: str | None = None
    workers: list = field(default_factory=list)
    price: int = 0
    remainder: float = 0
    mode: str = "normal"
    sales: int = 0
    revenue: int = 0
    payroll: int = 0
    unpaid_payroll: int = 0
    insolvent_days: int = 0
    production: int = 0


class Simulation:
    def __init__(self, config, scenario="reference", seed=None, record_hourly=True):
        if scenario not in SCENARIOS:
            raise RuleError("Scénario inconnu")
        self.config = copy.deepcopy(config)
        self.validate_config()
        self.seed = config["seed"] if seed is None else seed
        self.scenario = scenario
        self.rng = random.Random(self.seed)
        self.weather_rng = random.Random(f"{self.seed}:weather")
        self.presence_rng = random.Random(f"{self.seed}:presence")
        self.spoilage_rng = random.Random(f"{self.seed}:spoilage")
        self.record_hourly = record_hourly
        self.households = []
        self.businesses = []
        self.events, self.daily, self.hourly = [], [], []
        self.day = self.hour = 0
        self.housing = config["initial_housing"]
        self.pressure = 0
        self.project = None
        self.projects_completed = 0
        self.imports = []
        self.pending_imports = Counter()
        self.daily_sales = Counter()
        self.daily_firm_revenue = Counter()
        self.external_import_units = Counter()
        self.external_export_units = Counter()
        self.private_incomes = Counter()
        self.checks = 0
        self.government_commands = set()
        self.household_initial_cash = {}
        self.min_city_cash = config["initial_city_cash_cents"]
        self.money_error = 0
        balances = {"city": config["initial_city_cash_cents"], "external": config["initial_external_cash_cents"]}
        self.stocks = Stocks(config["products"])
        for i in range(config["npc_count"] + config["player_count"]):
            npc = i < config["npc_count"]
            name = f"npc{i + 1:02d}" if npc else f"player{i - config['npc_count'] + 1:02d}"
            profile = "PNJ" if npc else PROFILES[(i - config["npc_count"]) % len(PROFILES)]
            self.households.append(Household(name, profile))
            balances[name] = config["initial_household_cash_cents"]
            self.household_initial_cash[name] = balances[name]
        specifications = [
            ("grain_a", "grain", 45, 3, 0, 200, None, "player05"),
            ("grain_b", "grain", 45, 3, 6, 200, None, None),
            ("mill", "flour", 80, 3, 2, 400, "grain", None),
            ("bakery_a", "bread", 45, 4, 2, 300, "flour", "player02"),
            ("bakery_b", "bread", 45, 4, 4, 300, "flour", None),
            ("vegetables_a", "vegetables", 45, 5, 1, 300, None, "player03"),
            ("vegetables_b", "vegetables", 45, 5, 5, 300, None, None),
            ("workshop", "materials", 24, 4, 3, 300, None, "player06"),
        ]
        household_ids = {h.id for h in self.households}
        for args in specifications:
            business = Business(*args)
            if business.owner not in household_ids:
                business.owner = None
            business.price = config["products"][business.product]["base_price_cents"]
            self.businesses.append(business)
            balances[business.id] = config["initial_business_cash_cents"]
            self.stocks.initialize(business.id, {business.product: 72})
            if business.input:
                self.stocks.initialize(business.id, {business.input: 96})
        if scenario == "concentration" and "player08" in household_ids:
            for business in self.businesses:
                if business.id in ("bakery_a", "bakery_b", "vegetables_a"):
                    business.owner = "player08"
                    business.price = round(business.price * 1.35)
            self.event("initial_concentration", "Contrôle initial de deux boulangeries et d'une ferme ; prix +35 %")
        self.stocks.initialize("city", {"bread": config["reserve_target_bread"],
                                        "vegetables": config["reserve_target_vegetables"]})
        self.ledger = Ledger(balances)
        self.market = Market(self.ledger, self.stocks, self.rng,
                             config["delivery_capacity_per_batch"], config["delivery_fee_cents_per_distance_unit"])

    def validate_config(self):
        c = self.config
        integers = ("days", "npc_count", "player_count", "market_period_hours", "initial_housing",
                    "public_job_capacity", "delivery_capacity_per_batch", "housing_pressure_days",
                    "housing_project_days", "housing_project_units", "housing_project_materials",
                    "housing_maximum", "import_delay_days", "reserve_target_bread", "reserve_target_vegetables",
                    "reserve_daily_release_per_product", "import_daily_limit_per_product",
                    "material_export_daily_limit", "daily_wage_cents", "daily_rent_cents",
                    "initial_household_cash_cents", "initial_business_cash_cents", "initial_city_cash_cents",
                    "initial_external_cash_cents", "public_contract_cents_per_worker_day",
                    "housing_project_labor_cents", "delivery_fee_cents_per_distance_unit")
        for key in integers:
            if not isinstance(c[key], int) or isinstance(c[key], bool) or c[key] < 0:
                raise RuleError(f"Configuration invalide : {key}")
        if not c["days"] or not c["market_period_hours"] or 24 % c["market_period_hours"]:
            raise RuleError("La période du marché doit diviser 24 heures")
        if c["simulated_hours_per_real_hour"] <= 0 or not 0 < c["absence_reduce_real_hours"] < c["absence_sleep_real_hours"]:
            raise RuleError("Temps ou délais d'absence invalides")
        if set(c["products"]) != {"grain", "flour", "bread", "vegetables", "materials"}:
            raise RuleError("Les cinq produits du modèle sont requis")
        for p in c["products"].values():
            if not isinstance(p["base_price_cents"], int) or p["base_price_cents"] <= 0 or not 0 <= p["daily_spoil_basis_points"] <= 10000:
                raise RuleError("Prix ou conservation invalides")
        if not 0 <= c["wage_tax_basis_points"] <= 10000 or not 0 <= c["sales_tax_basis_points"] <= 10000:
            raise RuleError("Taxe invalide")
        if not 0 <= c["shortage_production_multiplier"] <= 1 or c["import_price_multiplier"] < 1 or c["price_maximum_multiplier"] < 1:
            raise RuleError("Multiplicateur invalide")
        if c["price_daily_increase"] < 1 or not 0 <= c["price_scarcity_stock_ratio"] <= 2:
            raise RuleError("Réaction tarifaire invalide")
        if c["npc_count"] + c["player_count"] == 0:
            raise RuleError("La ville doit avoir au moins un habitant")

    def event(self, type, description, **data):
        self.events.append({"day": self.day, "hour": self.hour, "type": type, "description": description, **data})

    def government_spend(self, command, amount, target, purpose, approved=False, conflict=False):
        allowed_targets = {"housing": "project_escrow", "food_import": "external"}
        if purpose not in allowed_targets or target != allowed_targets[purpose] or not approved or conflict:
            raise RuleError("Décision municipale non autorisée")
        executed = self.ledger.transfer("city", target, amount, "municipal:" + purpose, command)
        self.government_commands.add(command)
        return executed

    def apply_events(self):
        c, d = self.config, self.day
        if self.scenario == "arrivals" and d in (20, 27):
            count = 12 if d == 20 else 8
            for _ in range(count):
                id = f"new{sum(h.id.startswith('new') for h in self.households) + 1:02d}"
                self.households.append(Household(id, "nouvel arrivant", arrival=d))
                self.ledger.balances[id] = 0
                # The arrival endowment is an explicit issuance, not a hidden transfer.
                self.ledger.issue(id, c["initial_household_cash_cents"], "arrival_endowment")
                self.household_initial_cash[id] = c["initial_household_cash_cents"]
            self.event("arrivals", f"Installation de {count} nouveaux ménages", count=count)
        if self.scenario == "money_injection" and d == 20:
            for h in self.households:
                self.ledger.issue(h.id, 60000, "experimental_injection")
            self.event("money_injection", "Émission explicite de 600 unités par ménage", cents=60000 * len(self.households))
        if self.scenario in ("absence", "combined") and d in (20, 65):
            for h in self.households:
                if h.id in ("player02", "player03"):
                    h.absence_start = (d - 1) * 24 if d == 20 else None
            self.event("absence_start" if d == 20 else "return", "Deux propriétaires absents" if d == 20 else "Retour des deux propriétaires")
        if self.scenario == "departure" and d in (25, 70):
            for h in self.households:
                if h.id.startswith("player") and h.id not in ("player01", "player07"):
                    h.absence_start = (d - 1) * 24 if d == 25 else None
            self.event("departure" if d == 25 else "return", "Six joueurs cessent leur activité" if d == 25 else "Retour des six joueurs")
        if self.scenario in ("shortage", "combined"):
            if d == c["shortage_start_day"]:
                self.event("shortage_start", "Production agricole temporairement réduite", multiplier=c["shortage_production_multiplier"])
            if d == c["shortage_end_day"] + 1:
                self.event("shortage_end", "Retour de la capacité agricole")
        if self.project and d >= self.project["completion"]:
            self.housing += c["housing_project_units"]
            self.projects_completed += 1
            self.event("housing_completed", "Ouverture de logements", units=c["housing_project_units"], housing=self.housing)
            self.project = None
        for order in list(self.imports):
            if d >= order["arrival"]:
                self.stocks.add("city", order["product"], order["quantity"], "imports")
                self.pending_imports[order["product"]] -= order["quantity"]
                self.event("import_delivered", "Livraison extérieure de vivres", **order)
                self.imports.remove(order)

    def routines(self):
        c = self.config
        for h in self.households:
            old = h.mode
            real_hours = 0 if h.absence_start is None else (self.hour - h.absence_start) / c["simulated_hours_per_real_hour"]
            h.mode = "sleep" if real_hours >= c["absence_sleep_real_hours"] else "reduced" if real_hours >= c["absence_reduce_real_hours"] else "normal"
            h.needs = 0 if h.mode == "sleep" else 2
            if h.mode != old:
                self.event("routine_change", f"{h.id} : {old} → {h.mode}", household=h.id, real_absence_hours=real_hours)
            if h.id.startswith("npc"):
                h.connected = False
            else:
                chance = .65 if h.profile in ("commerçant actif", "artisan", "opportuniste") else .25
                if self.scenario == "low_presence":
                    chance /= 4
                h.connected = h.absence_start is None and self.presence_rng.random() < chance
        by_id = {h.id: h for h in self.households}
        for b in self.businesses:
            b.mode = by_id[b.owner].mode if b.owner else "normal"
            # Recovery is allowed as soon as liquidity and owner availability return.
            if b.mode == "normal" and self.ledger.balances[b.id] < b.jobs * c["daily_wage_cents"] + b.maintenance:
                b.mode = "insolvent"
                b.insolvent_days += 1
                if b.insolvent_days == 1:
                    self.event("business_insolvent", f"{b.id} ne peut plus financer sa journée de travail", cash_cents=self.ledger.balances[b.id])
        # Preserve jobs when possible. Job seekers cannot read other households' budgets.
        available = [h for h in self.households if h.mode != "sleep"]
        previous = {h.id: h.employer for h in available}
        for h in self.households:
            h.employer = None
        assigned = set()
        for b in self.businesses:
            b.workers = []
            if b.mode in ("sleep", "insolvent"):
                continue
            candidates = [h for h in available if previous[h.id] == b.id]
            candidates += [h for h in available if h not in candidates]
            for h in candidates:
                if h.id not in assigned and len(b.workers) < b.jobs:
                    b.workers.append(h)
                    h.employer = b.id
                    assigned.add(h.id)
        public = [h for h in available if h.id not in assigned]
        self.rng.shuffle(public)
        for h in public[:c["public_job_capacity"]]:
            h.employer = "city"
        # Housing survives sleep; newcomers are served in arrival order.
        free = self.housing - sum(h.housing for h in self.households)
        for h in self.households:
            if not h.housing and free > 0:
                h.housing = True
                h.housed_day = self.day
                free -= 1

    def produce(self, hod):
        if not 8 <= hod < 16:
            return
        c = self.config
        active = sum(h.needs > 0 for h in self.households)
        for b in self.businesses:
            if not b.workers or b.mode in ("sleep", "insolvent"):
                continue
            workforce = sum(.5 if h.mode == "reduced" else 1 for h in b.workers) / b.jobs
            factor = .5 if b.mode == "reduced" else 1
            if b.product in ("grain", "vegetables"):
                factor *= self.weather
                if self.scenario in ("shortage", "combined") and c["shortage_start_day"] <= self.day <= c["shortage_end_day"]:
                    factor *= c["shortage_production_multiplier"]
            b.remainder += b.daily_capacity / 8 * workforce * factor
            quantity = math.floor(b.remainder)
            b.remainder -= quantity
            target = math.ceil(active * (2 if b.product == "flour" else 1.5 if b.product in ("bread", "vegetables", "grain") else 3) /
                               sum(x.product == b.product and x.mode not in ("sleep", "insolvent") for x in self.businesses))
            quantity = min(quantity, max(0, target - self.stocks.items[b.id][b.product]))
            if b.input:
                quantity = min(quantity, self.stocks.items[b.id][b.input])
                self.stocks.take(b.id, b.input, quantity, "recipe_input")
            self.stocks.add(b.id, b.product, quantity, "production")
            b.production += quantity

    def payroll(self, hod):
        if not 8 <= hod < 16:
            return
        c = self.config
        working = [h for h in self.households if h.employer and h.mode != "sleep"]
        public = [h for h in working if h.employer == "city"]
        contract = sum(c["public_contract_cents_per_worker_day"] // 8 // (2 if h.mode == "reduced" else 1) for h in public)
        contract = min(contract, self.ledger.balances["external"])
        self.ledger.transfer("external", "city", contract, "public_service_export")
        for h in working:
            cents = c["daily_wage_cents"] // 8 // (2 if h.mode == "reduced" else 1)
            if self.ledger.balances[h.employer] < cents:
                if h.employer != "city":
                    next(b for b in self.businesses if b.id == h.employer).unpaid_payroll += cents
                self.event("unpaid_wage", f"Salaire non versé à {h.id}", employer=h.employer, cents=cents)
                continue
            self.ledger.transfer(h.employer, h.id, cents, "wage")
            tax = cents * c["wage_tax_basis_points"] // 10000
            self.ledger.transfer(h.id, "city", tax, "wage_tax")
            h.income += cents - tax
            h.paid_days += 1 if hod == 15 else 0
            if h.employer != "city":
                next(b for b in self.businesses if b.id == h.employer).payroll += cents
            if h.mode == "sleep":
                h.protected_income += cents

    def market_batch(self, hod):
        c = self.config
        if self.hour % c["market_period_hours"]:
            return
        def buy(owner, product, quantity, location):
            limit = round(c["products"][product]["base_price_cents"] * c["price_maximum_multiplier"])
            affordable = self.ledger.balances[owner] // (limit + 6 * self.market.fee)
            quantity = min(quantity, affordable)
            if quantity:
                self.market.place(f"{self.hour}:{owner}:buy:{product}", owner, product, quantity, limit, location, "buy")
        for b in self.businesses:
            if b.mode in ("sleep", "insolvent"):
                continue
            quantity = self.stocks.items[b.id][b.product]
            if quantity:
                self.market.place(f"{self.hour}:{b.id}:sell", b.id, b.product, quantity, b.price, b.location, "sell")
        if 6 <= hod <= 16:
            for b in self.businesses:
                if b.input and b.workers and b.mode not in ("sleep", "insolvent"):
                    active = sum(h.needs > 0 for h in self.households)
                    competitors = sum(x.product == b.product and x.mode not in ("sleep", "insolvent") for x in self.businesses)
                    target = math.ceil(active * 2 / competitors)
                    buy(b.id, b.input, max(0, target - self.stocks.items[b.id][b.input]), b.location)
        if 16 <= hod <= 20:
            for i, h in enumerate(self.households):
                if not h.needs:
                    continue
                for product in ("bread", "vegetables"):
                    buy(h.id, product, max(0, 1 - self.stocks.items[h.id][product]), i % 7)
        if hod == 22:
            # Substitutes are ordered only after the preferred basket was offered.
            for i, h in enumerate(self.households):
                missing = max(0, h.needs - sum(self.stocks.items[h.id][p] for p in ("bread", "vegetables")))
                if missing:
                    product = min(("bread", "vegetables"), key=lambda p: min((b.price for b in self.businesses if b.product == p and self.stocks.items[b.id][p]), default=10**9))
                    buy(h.id, product, missing, i % 7)
        trades = self.market.clear()
        households = {h.id: h for h in self.households}
        for _, buyer, seller, product, quantity, price, fee in trades:
            self.daily_sales[(seller, product)] += quantity
            self.daily_firm_revenue[seller] += quantity * price
            if seller in {b.id for b in self.businesses}:
                b = next(b for b in self.businesses if b.id == seller)
                b.sales += quantity
                b.revenue += quantity * price
                tax = quantity * price * c["sales_tax_basis_points"] // 10000
                self.ledger.transfer(seller, "city", tax, "sales_tax")
            if buyer in households:
                households[buyer].essential_spending += quantity * price + fee

    def food_relief(self):
        c = self.config
        release = {p: c["reserve_daily_release_per_product"] for p in ("bread", "vegetables")}
        households = list(self.households)
        self.rng.shuffle(households)
        households.sort(key=lambda h: sum(self.stocks.items[h.id][p] for p in release))
        for h in households:
            missing = max(0, h.needs - sum(self.stocks.items[h.id][p] for p in release))
            while missing:
                product = max(release, key=lambda p: min(release[p], self.stocks.items["city"][p]))
                if not release[product] or not self.stocks.items["city"][product]:
                    break
                # Personal, consumed immediately: relief never enters tradable inventory.
                self.stocks.take("city", product, 1, "personal_relief_consumption")
                h.food_received += 1
                h.needs -= 1
                release[product] -= 1
                missing -= 1

    def imports_and_exports(self):
        c = self.config
        for product in ("bread", "vegetables"):
            target = c["reserve_target_" + product]
            needed = max(0, target - self.stocks.items["city"][product] - self.pending_imports[product])
            quantity = min(needed, c["import_daily_limit_per_product"])
            price = round(c["products"][product]["base_price_cents"] * c["import_price_multiplier"])
            quantity = min(quantity, self.ledger.balances["city"] // price)
            if quantity:
                self.government_spend(f"import:{self.day}:{product}", quantity * price, "external", "food_import", approved=True)
                order = {"product": product, "quantity": quantity, "arrival": self.day + c["import_delay_days"], "cost_cents": quantity * price}
                self.imports.append(order)
                self.pending_imports[product] += quantity
                self.external_import_units[product] += quantity
                self.event("import_ordered", "Achat extérieur plafonné, livraison différée", **order)
        b = next(b for b in self.businesses if b.product == "materials")
        price = c["products"]["materials"]["base_price_cents"]
        quantity = min(c["material_export_daily_limit"], self.stocks.items[b.id]["materials"], self.ledger.balances["external"] // price)
        if quantity and b.mode not in ("sleep", "insolvent"):
            self.ledger.transfer("external", b.id, quantity * price, "material_export")
            self.stocks.take(b.id, "materials", quantity, "exports")
            self.external_export_units["materials"] += quantity
            b.revenue += quantity * price
            b.sales += quantity
            self.ledger.transfer(b.id, "city", quantity * price * c["sales_tax_basis_points"] // 10000, "sales_tax")

    def expenses_and_prices(self):
        c = self.config
        for h in self.households:
            if h.housing and h.mode != "sleep":
                due = c["daily_rent_cents"] // (2 if h.mode == "reduced" else 1)
                rent = min(due, self.ledger.balances[h.id])
                self.ledger.transfer(h.id, "city", rent, "rent")
                h.essential_spending += rent
                h.rent_arrears += due - rent
        for b in self.businesses:
            if b.mode in ("sleep", "insolvent"):
                continue
            overhead = b.maintenance // (2 if b.mode == "reduced" else 1)
            self.ledger.transfer(b.id, "city", min(overhead, self.ledger.balances[b.id]), "business_maintenance")
            # Pricing uses own stocks and realized sales, not future events/private budgets.
            sold = self.daily_sales[(b.id, b.product)]
            base = c["products"][b.product]["base_price_cents"]
            floor = round(base * 1.35) if self.scenario == "concentration" and b.owner == "player08" else base
            if sold and self.stocks.items[b.id][b.product] < sold * c["price_scarcity_stock_ratio"]:
                b.price = min(round(base * c["price_maximum_multiplier"]), round(b.price * c["price_daily_increase"]))
            elif self.stocks.items[b.id][b.product] > max(1, sold) * 2:
                b.price = max(floor, round(b.price / c["price_daily_increase"]))
            # Dividends are real cash transfers, available only above initial working capital.
            if b.owner and self.day % 7 == 0:
                h = next(h for h in self.households if h.id == b.owner)
                if h.mode == "normal":
                    dividend = max(0, self.ledger.balances[b.id] - c["initial_business_cash_cents"])
                    if dividend:
                        self.ledger.transfer(b.id, h.id, dividend, "dividend")
                        h.income += dividend

    def consume_and_spoil(self):
        for h in self.households:
            required = h.needs
            consumed = 0
            for product in ("bread", "vegetables"):
                quantity = min(required - consumed, self.stocks.items[h.id][product])
                self.stocks.take(h.id, product, quantity, "consumption")
                consumed += quantity
            h.food_received += consumed
            missing = required - consumed
            h.missed_food += missing
            h.missed_days += bool(missing)
            h.employed_days += bool(h.employer)
        for owner, items in list(self.stocks.items.items()):
            for product, quantity in list(items.items()):
                rate = self.config["products"][product]["daily_spoil_basis_points"] / 10000
                expected = quantity * rate
                spoiled = math.floor(expected) + (self.spoilage_rng.random() < expected % 1)
                self.stocks.take(owner, product, spoiled, "spoilage")

    def consider_housing(self):
        c = self.config
        active = sum(h.mode != "sleep" for h in self.households)
        unhoused = sum(not h.housing and h.mode != "sleep" for h in self.households)
        paid_activity = sum(bool(h.employer) for h in self.households)
        # Demand must be accompanied by useful activity for a sustained number of days.
        useful = active > 0 and paid_activity / active >= .55
        self.pressure = self.pressure + 1 if unhoused and useful else 0
        if self.project or self.pressure < c["housing_pressure_days"] or self.housing + c["housing_project_units"] > c["housing_maximum"]:
            return
        b = next(b for b in self.businesses if b.product == "materials")
        materials = c["housing_project_materials"]
        material_cost = materials * b.price
        cost = material_cost + c["housing_project_labor_cents"]
        if self.stocks.items[b.id]["materials"] < materials or self.ledger.balances["city"] < cost:
            return
        command = f"housing:{self.day}"
        # A scripted collective approval is a hypothesis; no human vote is inferred.
        self.government_spend(command, cost, "project_escrow", "housing", approved=True)
        self.ledger.transfer("project_escrow", b.id, material_cost, "construction_materials")
        self.stocks.take(b.id, "materials", materials, "construction")
        self.project = {"completion": self.day + c["housing_project_days"], "cost_cents": cost}
        self.ledger.transfer("project_escrow", "external", c["housing_project_labor_cents"], "construction_contract")
        b.revenue += material_cost
        self.event("housing_started", "Projet financé après besoin durable et approbation collective simulée", **self.project)
        self.pressure = 0

    def metrics(self):
        active = [h for h in self.households if h.mode != "sleep"]
        served = sum(self.day_consumed.values())
        needs = len(active) * 2
        food_prices = {}
        for product in ("bread", "vegetables"):
            sellers = [b for b in self.businesses if b.product == product and b.mode not in ("sleep", "insolvent")]
            food_prices[product] = sum(b.price for b in sellers) / max(1, len(sellers)) if sellers else self.config["products"][product]["base_price_cents"] * self.config["import_price_multiplier"]
        cash = [self.ledger.balances[h.id] for h in self.households]
        groups = Counter()
        for b in self.businesses:
            if b.product in ("bread", "vegetables"):
                groups[b.owner or b.id] += self.daily_sales[(b.id, b.product)]
        volume = sum(groups.values())
        reserve = sum(self.stocks.items["city"][p] for p in ("bread", "vegetables"))
        return {
            "day": self.day, "hour": self.hour, "population": len(self.households), "active_population": len(active),
            "connected_players": sum(h.connected for h in self.households),
            "sleeping_households": len(self.households) - len(active),
            "employed": sum(h.employer is not None for h in active),
            "employment_rate": sum(h.employer is not None for h in active) / max(1, len(active)),
            "housed": sum(h.housing for h in self.households), "housing_capacity": self.housing,
            "unhoused": sum(not h.housing for h in self.households), "housing_projects_completed": self.projects_completed,
            "food_access_rate": served / needs if needs else 1,
            "food_units_missing": needs - served, "food_units_served": served,
            "basket_price_cents": round(sum(food_prices.values())),
            "city_cash_cents": self.ledger.balances["city"], "household_cash_min_cents": min(cash, default=0),
            "household_cash_median_cents": sorted(cash)[len(cash) // 2] if cash else 0,
            "household_cash_gini": gini(cash),
            "reserve_food_units": reserve, "reserve_days": reserve / max(1, needs),
            "essential_sales_largest_owner_share": max(groups.values(), default=0) / max(1, volume),
            "operating_businesses": sum(b.mode not in ("sleep", "insolvent") for b in self.businesses),
            "money_total_cents": sum(self.ledger.balances.values()), "money_created_cents": self.ledger.created,
            "money_error_cents": sum(self.ledger.balances.values()) - self.ledger.initial - self.ledger.created + self.ledger.removed,
            **{f"stock_{p}": sum(items[p] for items in self.stocks.items.values()) for p in self.stocks.products},
        }

    def run(self):
        for day in range(1, self.config["days"] + 1):
            self.day = day
            self.hour = (day - 1) * 24
            self.ledger.hour = self.hour
            self.daily_sales.clear()
            self.daily_firm_revenue.clear()
            self.weather = self.weather_rng.uniform(.9, 1.1)
            self.apply_events()
            self.routines()
            before = {h.id: h.food_received for h in self.households}
            self.day_consumed = Counter()
            for hod in range(24):
                self.hour = (day - 1) * 24 + hod
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
        self.event("run_completed", "Simulation terminée, invariants vérifiés à chaque heure", checks=self.checks)
        return self

    def summary(self):
        last = self.daily[-1]
        food_needed = sum(r["active_population"] * 2 for r in self.daily)
        food_served = sum(r["food_units_served"] for r in self.daily)
        stress_end = self.config["shortage_end_day"] if self.scenario in ("shortage", "combined") else 64 if self.scenario == "absence" else 69 if self.scenario == "departure" else None
        recovery = None
        if stress_end:
            for i, row in enumerate(self.daily):
                if row["day"] > stress_end and i + 7 <= len(self.daily) and all(r["food_access_rate"] >= .99 for r in self.daily[i:i + 7]):
                    recovery = row["day"] - stress_end
                    break
        return {
            "scenario": self.scenario, "seed": self.seed, "days": self.config["days"], "checks": self.checks,
            "food_access_rate": food_served / food_needed if food_needed else 1,
            "food_access_worst_day": min(r["food_access_rate"] for r in self.daily),
            "days_with_food_shortage": sum(r["food_access_rate"] < .99 for r in self.daily),
            "households_ever_missing_food": sum(h.missed_food > 0 for h in self.households),
            "basket_initial_cents": self.daily[0]["basket_price_cents"], "basket_final_cents": last["basket_price_cents"],
            "basket_peak_cents": max(r["basket_price_cents"] for r in self.daily),
            "city_initial_cash_cents": self.config["initial_city_cash_cents"],
            "city_final_cash_cents": last["city_cash_cents"], "city_min_cash_cents": self.min_city_cash,
            "employment_final": last["employment_rate"], "unhoused_final": last["unhoused"],
            "unhoused_peak": max(r["unhoused"] for r in self.daily), "housing_final": self.housing,
            "projects_completed": self.projects_completed,
            "business_insolvent_days": sum(b.insolvent_days for b in self.businesses),
            "household_cash_gini_final": last["household_cash_gini"],
            "household_cash_min_cents": last["household_cash_min_cents"],
            "largest_essential_owner_share_peak": max(r["essential_sales_largest_owner_share"] for r in self.daily),
            "recovery_days": recovery, "money_initial_cents": self.ledger.initial,
            "money_final_cents": sum(self.ledger.balances.values()), "money_created_cents": self.ledger.created,
            "money_removed_cents": self.ledger.removed, "money_error_cents": last["money_error_cents"],
            "protected_wage_income_cents": sum(h.protected_income for h in self.households),
            "public_import_cost_cents": sum(row[3] for row in self.ledger.history if row[4] == "municipal:food_import"),
            "external_net_transfer_to_city_economy_cents": self.config["initial_external_cash_cents"] - self.ledger.balances["external"],
            "import_units": dict(self.external_import_units), "export_units": dict(self.external_export_units),
            "pending_imports": list(self.imports),
        }

    def profiles(self):
        rows = []
        for h in self.households:
            duration = self.config["days"] - h.arrival + 1
            owned = [b for b in self.businesses if b.owner == h.id]
            rows.append({
                "household": h.id, "profile": h.profile, "arrival_day": h.arrival, "mode_final": h.mode,
                "housed": h.housing, "days_to_housing": None if h.housed_day is None else h.housed_day - h.arrival,
                "cash_initial_cents": self.household_initial_cash[h.id], "cash_final_cents": self.ledger.balances[h.id],
                "net_income_cents": h.income, "essential_spending_cents": h.essential_spending,
                "essential_to_income_ratio": h.essential_spending / h.income if h.income else None,
                "food_missing_units": h.missed_food, "days_missing_food": h.missed_days,
                "employment_days": h.employed_days, "employment_rate": h.employed_days / duration,
                "days_paid_at_last_work_hour": h.paid_days,
                "rent_arrears_cents": h.rent_arrears, "owned_businesses": len(owned),
                "owned_business_cash_cents": sum(self.ledger.balances[b.id] for b in owned),
            })
        return rows


def gini(values):
    ordered = sorted(values)
    total = sum(ordered)
    return (2 * sum(i * v for i, v in enumerate(ordered, 1)) / (len(ordered) * total) -
            (len(ordered) + 1) / len(ordered)) if total else 0.0
