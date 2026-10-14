from __future__ import annotations

import copy
import hashlib
import json
import re
import secrets
import sqlite3
import threading
from pathlib import Path

from citysim.engine import RuleError
from citysim.v3 import WelcomingSimulation
from .world import BUILDINGS, GOALS, JOBS, layout, walkable


ROOT = Path(__file__).resolve().parents[1]


class Game:
    """Single-device, preapproved local player. SQLite commands are replayed on restart."""

    def __init__(self, database):
        self.lock = threading.RLock()
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(database, check_same_thread=False)
        Path(database).chmod(0o600)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS commands (seq INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL, action TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL)")
        self.base = json.loads((ROOT / "config/default.json").read_text())
        self.experiment = json.loads((ROOT / "config/extended.json").read_text())
        self.settings = json.loads((ROOT / "config/v3.json").read_text())
        self.settings["days"] = 1080
        fingerprint = hashlib.sha256(json.dumps([self.base, self.experiment, self.settings], sort_keys=True).encode()).hexdigest()
        existing = self.meta("configuration")
        if existing is not None and existing != fingerprint:
            raise RuleError("Cette sauvegarde utilise un autre réglage. Conserve-la et choisis un nouveau fichier de sauvegarde.")
        self.set_meta("configuration", fingerprint)
        self.token = self.meta("session") or secrets.token_urlsafe(32)
        self.set_meta("session", self.token)
        self.position = json.loads(self.meta("position") or "[22,19]")
        if not walkable(*self.position):
            self.position = [22, 19]
        self.reset_model()
        self.replay()
        self.db.commit()

    def meta(self, key):
        row = self.db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def set_meta(self, key, value):
        self.db.execute("INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    def reset_model(self):
        self.sim = WelcomingSimulation(self.base, self.experiment, self.settings, detailed=False)
        self.player_id = "player04"
        self.home = self.job = self.goal = None
        self.completed_goals = []

    @property
    def player(self):
        return next(h for h in self.sim.residents() if h.id == self.player_id)

    def digest(self):
        data = {"day": self.sim.day, "accounts": self.sim.ledger.balances,
                "stocks": {k: dict(v) for k, v in self.sim.stocks.items.items()}, "home": self.home,
                "job": self.job, "goal": self.goal, "completed": self.completed_goals}
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def replay(self):
        for id, action, payload, expected in self.db.execute("SELECT id,action,payload,digest FROM commands ORDER BY seq"):
            self.apply(action, json.loads(payload), id, replay=True)
            if self.digest() != expected:
                raise RuleError("La reprise de cette sauvegarde ne correspond pas au journal. La sauvegarde originale est conservée.")

    def command(self, id, action, payload):
        if not isinstance(id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{8,80}", id):
            raise RuleError("Identifiant de commande invalide")
        if not isinstance(payload, dict):
            raise RuleError("Commande invalide")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with self.lock:
            existing = self.db.execute("SELECT action,payload FROM commands WHERE id=?", (id,)).fetchone()
            if existing:
                if existing != (action, encoded):
                    raise RuleError("Cet identifiant a déjà servi pour une autre commande")
                return self.snapshot()
            try:
                self.apply(action, payload, id)
                self.sim.ledger.check()
                self.sim.stocks.check()
                self.db.execute("INSERT INTO commands(id,action,payload,digest) VALUES(?,?,?,?)", (id, action, encoded, self.digest()))
                self.db.commit()
            except Exception:
                self.db.rollback()
                self.reset_model()
                self.replay()
                raise
            return self.snapshot()

    def apply(self, action, payload, id, replay=False):
        s, h = self.sim, self.player
        if action == "home":
            home = payload.get("home")
            if home not in ("home_place", "home_garden") or self.home is not None:
                raise RuleError("Choisis un logement disponible")
            self.home = home
            h.housing = True
            h.housed_day = 1
        elif action == "job":
            job = payload.get("job")
            if not self.home or self.job is not None or job not in JOBS:
                raise RuleError("Choisis d'abord ton logement, puis une activité")
            self.job = job
        elif action == "goal":
            goal = payload.get("goal")
            if not self.job or goal not in GOALS or goal in self.completed_goals:
                raise RuleError("Choisis un objectif disponible")
            self.goal = goal
        elif action == "cancel_goal":
            if not self.job:
                raise RuleError("Installe-toi d'abord")
            self.goal = None
        elif action == "advance":
            if not self.home or not self.job:
                raise RuleError("Termine ton installation avant de découvrir la journée suivante")
            s.step_day()
        elif action == "complete_goal":
            if not self.job or not self.goal or self.goal in self.completed_goals:
                raise RuleError("Choisis d'abord un objectif")
            goal = GOALS[self.goal]
            place = next(b for b in BUILDINGS if b["id"] == goal["location"])
            if not replay and abs(self.position[0] - place["door"][0]) + abs(self.position[1] - place["door"][1]) > 3:
                raise RuleError("Approche-toi du lieu indiqué sur la carte")
            workshop = next(b for b in s.businesses if b.product == "materials")
            qty = goal["materials"]
            cost = qty * workshop.price
            reserve = (self.food_price() + s.config["daily_rent_cents"]) * 3
            if s.ledger.balances[h.id] < cost + reserve:
                raise RuleError("Garde de quoi payer trois jours de nourriture et de loyer")
            if s.stocks.items[workshop.id]["materials"] < qty:
                raise RuleError("L'atelier prépare des matériaux. Reviens après la prochaine journée")
            s.ledger.transfer(h.id, workshop.id, cost, "player_goal:materials", "goal:" + id)
            s.stocks.take(workshop.id, "materials", qty, "player_goal")
            workshop.revenue += cost
            workshop.sales += qty
            tax = cost * s.config["sales_tax_basis_points"] // 10000
            s.ledger.transfer(workshop.id, "city", tax, "sales_tax")
            self.completed_goals.append(self.goal)
            self.goal = None
        else:
            raise RuleError("Action inconnue")

    def move(self, x, y):
        if type(x) is not int or type(y) is not int or not walkable(x, y):
            raise RuleError("Ce chemin n'est pas accessible")
        with self.lock:
            self.position = [x, y]
            self.set_meta("position", json.dumps(self.position))
            self.db.commit()

    def food_price(self):
        return round(sum(min((b.price for b in self.sim.businesses if b.product == p and b.mode == "normal"), default=self.base["products"][p]["base_price_cents"]) for p in ("bread", "vegetables")))

    def public_snapshot(self):
        s = self.sim
        return {"day": s.day, "population": len(s.residents()), "housing": s.housing,
                "food_price_cents": self.food_price(), "places": layout(),
                "story": "Une petite ville où chacun peut trouver sa place.",
                "completed_projects": s.projects_completed}

    def snapshot(self):
        with self.lock:
            s, h = self.sim, self.player
            income = s.config["daily_wage_cents"]
            net = income - 8 * (income // 8 * s.config["wage_tax_basis_points"] // 10000)
            journal = []
            if s.day:
                rows = [r for r in s.household_daily if r["household"] == h.id and r["day"] == s.day]
                if rows:
                    today = rows[-1]
                    journal = [{"label": "Revenus reçus", "cents": today["income_cents"]},
                               {"label": "Panier et loyer", "cents": -today["essential_spending_cents"]}]
                    if today["food_missing_units"]:
                        journal.append({"label": "Une aide alimentaire a été demandée", "cents": 0})
            return {"world": self.public_snapshot(), "player": {
                "name": "Camille", "home": self.home, "job": self.job, "goal": self.goal,
                "completed_goals": self.completed_goals, "position": self.position,
                "cash_cents": s.ledger.balances[h.id], "wage_net_cents": net,
                "rent_cents": s.config["daily_rent_cents"], "food_price_cents": self.food_price(),
                "daily_balance_cents": net - self.food_price() - s.config["daily_rent_cents"],
                "journal": journal, "routine_enabled": self.job is not None},
                "saved": True, "jobs": JOBS, "goals": {id: {**g, "cost_cents": g["materials"] * self.base["products"]["materials"]["base_price_cents"]} for id, g in GOALS.items()}}

    def backup(self):
        with self.lock:
            return {"format": "city-prototype-commands-v1", "configuration": self.meta("configuration"),
                    "position": self.position, "commands": [{"id": id, "action": action, "payload": json.loads(payload), "digest": digest}
                    for id, action, payload, digest in self.db.execute("SELECT id,action,payload,digest FROM commands ORDER BY seq")]}

    def restore_backup(self, backup):
        with self.lock:
            if self.db.execute("SELECT COUNT(*) FROM commands").fetchone()[0]:
                raise RuleError("Restaure dans une nouvelle sauvegarde pour conserver la partie actuelle")
            if not isinstance(backup, dict) or backup.get("format") != "city-prototype-commands-v1" or backup.get("configuration") != self.meta("configuration"):
                raise RuleError("Format ou réglage de sauvegarde incompatible")
            position = backup.get("position")
            commands = backup.get("commands")
            if not isinstance(position, list) or len(position) != 2 or any(type(n) is not int for n in position) or not walkable(*position):
                raise RuleError("Position sauvegardée invalide")
            if not isinstance(commands, list) or len(commands) > 5000:
                raise RuleError("Journal sauvegardé invalide")
            try:
                self.db.execute("BEGIN")
                for command in commands:
                    id = command.get("id")
                    if not isinstance(id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{8,80}", id) or not isinstance(command.get("payload"), dict):
                        raise RuleError("Commande sauvegardée invalide")
                    self.apply(command["action"], command["payload"], id, replay=True)
                    if self.digest() != command.get("digest"):
                        raise RuleError("Le journal de sauvegarde a été modifié ou est incompatible")
                    self.db.execute("INSERT INTO commands(id,action,payload,digest) VALUES(?,?,?,?)", (id, command["action"], json.dumps(command["payload"], sort_keys=True, separators=(",", ":")), command["digest"]))
                self.set_meta("position", json.dumps(position))
                self.db.commit()
                self.position = position
            except Exception:
                self.db.rollback()
                self.reset_model()
                raise


    def close(self):
        self.db.close()
