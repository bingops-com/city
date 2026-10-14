from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import asdict
from html import escape
from pathlib import Path

from .engine import SCENARIOS


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path, rows, fields=None):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or (list(rows[0]) if rows else []))
        writer.writeheader()
        writer.writerows(rows)


def export_run(simulation, destination):
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    s = simulation
    write_json(dest / "config.json", {**s.config, "seed": s.seed, "scenario": s.scenario})
    write_json(dest / "summary.json", s.summary())
    write_json(dest / "events.json", s.events)
    write_csv(dest / "daily.csv", s.daily)
    write_csv(dest / "hourly.csv", s.hourly)
    write_csv(dest / "profiles.csv", s.profiles())
    businesses = []
    for b in s.businesses:
        businesses.append({k: v for k, v in asdict(b).items() if k != "workers"} | {
            "cash_final_cents": s.ledger.balances[b.id], "workers_final": len(b.workers),
            "inventory_final": json.dumps(s.stocks.items[b.id], sort_keys=True),
            "cash_change_cents": s.ledger.balances[b.id] - s.config["initial_business_cash_cents"],
        })
    write_csv(dest / "businesses.csv", businesses)
    with (dest / "ledger.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["hour", "source", "target", "cents", "reason"])
        writer.writerows(s.ledger.history)
    flows = Counter()
    for _, source, target, cents, reason in s.ledger.history:
        if reason not in ("order_reservation", "order_refund"):
            flows[(source.startswith("escrow:"), reason)] += cents
    write_json(dest / "audit.json", {
        "hourly_checks": s.checks, "money_initial_cents": s.ledger.initial,
        "money_created_cents": s.ledger.created, "money_removed_cents": s.ledger.removed,
        "money_final_cents": sum(s.ledger.balances.values()),
        "accounts_final": s.ledger.balances,
        "stock_initial": dict(s.stocks.initial), "stock_added": dict(s.stocks.added),
        "stock_taken": dict(s.stocks.taken),
        "stock_final": {p: sum(items[p] for items in s.stocks.items.values()) for p in s.stocks.products},
        "stock_causes": [{"product": p, "cause": cause, "quantity": q} for (p, cause), q in sorted(s.stocks.flows.items())],
        "monetary_flows": [{"reason": reason, "from_market_escrow": escrow, "cents": cents} for (escrow, reason), cents in sorted(flows.items())],
        "open_orders": len(s.market.orders),
        "in_transit_imports": s.imports,
    })
    write_json(dest / "manifest.json", {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(dest.iterdir()) if p.is_file() and p.name != "manifest.json"})


def chart_svg(path, runs):
    plots = [("Panier alimentaire proposé (unités)", "basket_price_cents", .01),
             ("Trésorerie municipale (unités)", "city_cash_cents", .01),
             ("Besoins alimentaires satisfaits (%)", "food_access_rate", 100),
             ("Ménages sans logement", "unhoused", 1)]
    colors = ["#315bb6", "#63832c", "#aa5a13", "#8d4dc0", "#147f81", "#c23e4b", "#976420", "#69758c", "#bc397e"]
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="870" viewBox="0 0 1200 870" role="img" aria-label="Comparaison des simulations économiques City">',
           '<rect width="1200" height="870" fill="#fff"/>',
           '<style>text{font-family:system-ui,sans-serif;fill:#253041;font-size:12px}.title{font-size:18px;font-weight:600}.axis{stroke:#a7adb6;stroke-width:1;fill:none}</style>',
           '<text x="50" y="32" class="title">City — première simulation, graine de référence</text>']
    for index, (title, key, scale) in enumerate(plots):
        left, top = 65 + (index % 2) * 595, 95 + (index // 2) * 330
        width, height = 480, 245
        all_values = [r[key] * scale for s in runs for r in s.daily]
        maximum = max(all_values, default=1) or 1
        maximum = maximum * 1.05
        out.append(f'<text x="{left}" y="{top - 20}" class="title">{escape(title)}</text>')
        for i in range(5):
            y = top + height - height * i / 4
            value = maximum * i / 4
            out.append(f'<path d="M{left},{y} h{width}" stroke="#e7e9ed"/><text x="{left - 8}" y="{y + 4}" text-anchor="end">{value:.0f}</text>')
        out.append(f'<path class="axis" d="M{left},{top} v{height} h{width}"/>')
        max_day = max(s.config["days"] for s in runs)
        for day in (1, 30, 60, 90):
            if day <= max_day:
                x = left + (day - 1) / max(1, max_day - 1) * width
                out.append(f'<text x="{x}" y="{top + height + 20}" text-anchor="middle">J{day}</text>')
        for n, s in enumerate(runs):
            points = " ".join(f"{left + (r['day'] - 1) / max(1, max_day - 1) * width:.1f},{top + height - r[key] * scale / maximum * height:.1f}" for r in s.daily)
            out.append(f'<polyline fill="none" stroke="{colors[n % len(colors)]}" stroke-width="1.8" opacity=".85" points="{points}"><title>{escape(s.scenario)}</title></polyline>')
    for i, s in enumerate(runs):
        x, y = 65 + i % 3 * 375, 775 + i // 3 * 27
        out.append(f'<path d="M{x},{y - 4} h22" stroke="{colors[i % len(colors)]}" stroke-width="3"/><text x="{x + 30}" y="{y}">{escape(s.scenario)}</text>')
    out.append("</svg>")
    Path(path).write_text("\n".join(out) + "\n", encoding="utf-8")


def money(cents):
    return f"{cents / 100:,.2f}".replace(",", " ")


def suite_report(destination, runs, samples, variants):
    dest = Path(destination)
    reference = next((s for s in runs if s.scenario == "reference"), runs[0])
    ref = reference.summary()
    lines = ["# Première simulation économique de City", "", "Expérience locale du 14 octobre 2026. Tous les montants ci-dessous sont exprimés en unités de monnaie fictive (100 centimes = 1 unité).", "",
             f"{len(runs)} scénarios, {reference.config['days']} jours par scénario, un pas d'une heure, graine détaillée **{reference.seed}**. {len(samples)} expériences supplémentaires de variabilité ; {len(variants)} variantes de réglage détaillées.", "",
             "## Conclusion du premier passage", "",
             f"La référence sert **{ref['food_access_rate']:.2%}** des besoins alimentaires, avec **{ref['days_with_food_shortage']} jours incomplets**. La trésorerie municipale passe de **{money(ref['city_initial_cash_cents'])}** à **{money(ref['city_final_cash_cents'])}**, et le panier proposé de **{money(ref['basket_initial_cents'])}** à **{money(ref['basket_final_cents'])}**.", "",
             f"Les **{ref['checks']} contrôles horaires** de la référence ferment la comptabilité monétaire et matière. Cette exactitude ne suffit pas à valider les règles économiques : les réserves périssables coûtent cher à renouveler et le prix fondé sur le stock d'un seul vendeur peut monter même quand d'autres fournisseurs disposent de marchandises.", "",
             "## Comparaison des scénarios", "",
             "| Scénario | Alimentation servie | Jours incomplets | Panier final | Mairie finale | Sans logement (pic / fin) | Emploi final |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for s in runs:
        r = s.summary()
        lines.append(f"| {s.scenario} | {r['food_access_rate']:.2%} | {r['days_with_food_shortage']} | {money(r['basket_final_cents'])} | {money(r['city_final_cash_cents'])} | {r['unhoused_peak']} / {r['unhoused_final']} | {r['employment_final']:.1%} |")
    lines += ["", "![Courbes comparatives](comparison.svg)", "", "Le panier est la moyenne non pondérée des prix proposés par les entreprises en fonctionnement, pour un pain et un légume. Il exclut loyer et livraison. Les aides gratuites ne constituent pas un prix de marché. Le taux d'alimentation compte deux portions par ménage actif et par jour, aides et substitutions incluses.", "", "## Variabilité", "", "La graine détaillée n'est pas comptée dans les graines supplémentaires. Chaque intervalle ci-dessous indique minimum–maximum, sans interprétation comme intervalle de confiance.", "", "| Scénario | Graines supplémentaires | Alimentation servie | Mairie finale | Jours incomplets |", "| --- | ---: | ---: | ---: | ---: |"]
    for name in [s.scenario for s in runs]:
        group = [r for r in samples if r["scenario"] == name]
        if group:
            lines.append(f"| {name} | {len(group)} | {min(r['food_access_rate'] for r in group):.2%}–{max(r['food_access_rate'] for r in group):.2%} | {money(min(r['city_final_cash_cents'] for r in group))}–{money(max(r['city_final_cash_cents'] for r in group))} | {min(r['days_with_food_shortage'] for r in group)}–{max(r['days_with_food_shortage'] for r in group)} |")
    if variants:
        lines += ["", "## Réglages comparés à la référence", "", "Même graine et mêmes événements de référence ; les modifications sont des hypothèses, pas des décisions validées.", "", "| Variante | Paramètres modifiés | Alimentation servie | Mairie finale | Panier final | Gini des liquidités |", "| --- | --- | ---: | ---: | ---: | ---: |"]
        for label, changes, s in variants:
            r = s.summary()
            text = "; ".join(f"{k}={v}" for k, v in changes.items())
            lines.append(f"| {label} | {text} | {r['food_access_rate']:.2%} | {money(r['city_final_cash_cents'])} | {money(r['basket_final_cents'])} | {r['household_cash_gini_final']:.3f} |")
        lines += ["", "Le seuil de prix plus bas teste une réaction moins sensible à l'épuisement du stock d'un vendeur. Les réserves plus petites réduisent les pertes et les achats de renouvellement, mais offrent moins de protection face à une pénurie. La variante combinée explore leur interaction ; elle ne démontre pas leur robustesse dans les autres scénarios."]
    lines += ["", "## Incidents et contraintes observés", ""]
    first_unpaid = next((e for e in reference.events if e["type"] == "unpaid_wage"), None)
    if first_unpaid:
        count = sum(e["type"] == "unpaid_wage" for e in reference.events)
        lines += [f"**Référence :** premier salaire non versé au jour {first_unpaid['day']}, puis {count} échéances horaires non payées. Les contrats de services municipaux ne couvrent qu'une partie des salaires ; taxes et loyers complètent le financement, tandis que les achats de renouvellement des réserves épuisent la trésorerie.", ""]
    for s in runs:
        r = s.summary()
        if s.scenario == "low_presence":
            lines += ["**Faible présence :** les mouvements financiers sont identiques à la référence, car la présence connectée ne modifie pas les routines. Cette égalité vérifie une règle du modèle ; elle ne prédit pas les décisions d'un groupe humain peu actif.", ""]
        if s.scenario == "arrivals":
            materials = [row["stock_materials"] for row in s.daily]
            b = next(b for b in s.businesses if b.product == "materials")
            lines += [f"**Arrivées :** {len(s.households)} ménages pour {s.housing} logements et {s.daily[-1]['employed']} postes affectés. Aucun chantier ne termine. Le stock de matériaux reste entre {min(materials)} et {max(materials)} unités, sous le besoin de {s.config['housing_project_materials']} unités par chantier : l'atelier produit {b.daily_capacity} unités par jour et exporte jusqu'à {s.config['material_export_daily_limit']} unités, empêchant l'accumulation pour construire. Le budget municipal se dégrade ensuite. L'expansion ne peut donc pas résoudre l'accueil avec cette priorité d'exportation.", ""]
        if s.scenario in ("absence", "departure", "combined"):
            sleeps = [e for e in s.events if e["type"] == "routine_change" and "→ sleep" in e["description"]]
            days = sorted({e["day"] for e in sleeps})
            lines += [f"**{s.scenario} :** {len(sleeps)} ménages entrent en sommeil aux jours {days}. Les commerces de leurs propriétaires suspendent leur production et les emplois se redistribuent dans les capacités disponibles. Les protections suspendent revenus et loyers ensemble ; les salariés des entreprises fermées restent exposés au manque de postes.", ""]
        closed = [e for e in s.events if e["type"] == "business_insolvent"]
        for e in closed:
            lines += [f"**{s.scenario}, jour {e['day']} :** {e['description']} (trésorerie {money(e['cash_cents'])}). Le moteur suspend le travail faute de pouvoir financer salaire et entretien, sans effacer les biens ni créer de monnaie. Les stocks restants ne sont pas vendus en mode insolvable dans ce premier modèle ; une liquidation ou une recapitalisation reste à définir.", ""]
        if s.scenario == "shortage":
            during = [row for row in s.daily if s.config["shortage_start_day"] <= row["day"] <= s.config["shortage_end_day"]]
            if during:
                lines += [f"**Pénurie :** le minimum d'accès alimentaire pendant l'événement est {min(row['food_access_rate'] for row in during):.2%}. Les réserves, achats extérieurs et substitutions amortissent la baisse agricole. Le bilan global doit être distingué de la réponse pendant l'événement : les difficultés tardives de trésorerie peuvent dominer ce bilan.", ""]
            else:
                lines += ["**Pénurie :** ce passage s'arrête avant le début de l'événement programmé.", ""]
        if s.scenario == "concentration":
            h = next((h for h in s.profiles() if h["household"] == "player08"), None)
            if h:
                lines += [f"**Concentration :** l'opportuniste reçoit {money(h['net_income_cents'])} de revenus nets (salaire et dividendes) et finit avec {money(h['cash_final_cents'])} en liquidités. La part maximale quotidienne des ventes essentielles d'un propriétaire atteint {r['largest_essential_owner_share_peak']:.1%}. L'avantage observé dépend de la propriété et des prix initialement imposés ; aucun coût de rachat n'est modélisé.", ""]
        if s.scenario == "money_injection":
            lines += [f"**Injection :** {money(r['money_created_cents'])} de monnaie sont émis et identifiés. Les ménages continuent à acheter seulement deux portions par jour ; la dotation évite leur manque de fonds, mais ne teste ni achats facultatifs, ni crédit, ni inflation immobilière.", ""]
    lines += ["", "## Budgets et causes à examiner", "",
              f"La référence engage **{money(ref['public_import_cost_cents'])}** d'importations municipales sur {ref['days']} jours. Le solde net des échanges avec l'extérieur est **{money(ref['external_net_transfer_to_city_economy_cents'])}** reçu par l'économie locale (valeur négative : sortie nette). Les achats déjà payés et non encore livrés figurent dans `summary.json` et `audit.json`.", "",
              "| Profil joueur, référence | Revenu net total | Dépenses essentielles | Solde final | Jours avec manque alimentaire |", "| --- | ---: | ---: | ---: | ---: |"]
    for h in reference.profiles():
        if h["household"].startswith("player"):
            lines.append(f"| {h['profile']} | {money(h['net_income_cents'])} | {money(h['essential_spending_cents'])} | {money(h['cash_final_cents'])} | {h['days_missing_food']} |")
    lines += ["", "Les revenus nets comprennent salaires après taxe et dividendes. Le Gini mesure uniquement les liquidités des ménages ; il exclut la valeur des entreprises et du foncier. Le taux d'emploi mesure les postes affectés, et `profiles.csv` précise les jours de paiement ; un poste municipal peut être affecté sans salaire lorsque le budget est épuisé.", "", "## Hypothèses et limites", "",
              "- Un ménage représente un habitant, avec deux portions quotidiennes. Aucun décès, aucune dette automatique et aucun emprunt.",
              "- Huit entreprises, une chaîne céréales → farine → pain, deux fournisseurs de légumes et un atelier de matériaux. Les recettes sont 1:1 ; les productions agricoles varient de ±10 % autour de leur capacité.",
              "- Les 40 PNJ et les joueurs suivent des routines autorisées. La présence connectée ne procure aucun bonus. Les profils distinguent présence et propriété initiale ; artisanat de qualité, stratégie foncière et coopération sociale ne sont pas encore modélisés.",
              "- Les salaires et loyers sont en centimes entiers. Les divisions horaires sont arrondies vers le bas. Les prix réagissent aux stocks et aux ventes observés ; la demande essentielle reste fixe, donc l'injection de monnaie ne suffit pas à tester une inflation générale.",
              "- L'extérieur possède un budget fini : il achète des matériaux et des services municipaux, vend des vivres avec délai, et réalise les chantiers. Ce modèle teste une économie ouverte, pas une ville autonome.",
              "- Les réserves municipales subissent la même conservation que les stocks privés. Les secours sont plafonnés et directement consommés, sans revente. Les imports restent limités et payés avant livraison.",
              "- Une absence est mesurée en heures réelles indépendamment de la vitesse d'exécution du programme : réduction après 24 h réelles, sommeil après 72 h, à 6 heures simulées par heure réelle. Au sommeil, salaires, dividendes, besoins et loyers sont suspendus ; le logement reste occupé et protégé. La consommation suspendue est une convention abstraite d'absence.",
              "- Les engagements municipaux exigent droit, absence de conflit et financement préalable. Les projets ont une approbation collective programmée ; élections, recours et votes humains ne sont pas simulés.",
              "- Les arrivants reçoivent une émission explicite de monnaie. Une expansion exige un besoin de logement durable, un emploi affecté à au moins 55 % des actifs, matériaux et budget. L'activité sociale et le contenu d'une ville jouable restent à mesurer.",
              "- La concentration est une différence de propriété et de politique tarifaire initiales, sans simuler un rachat. Modernisation, crypto, PNJ temporaires et vie personnelle détaillée sont différés.",
              "- Les vérifications de commandes et de permissions sont locales. Elles ne démontrent pas la résistance d'un serveur concurrent ; cette étape demandera transactions atomiques et contrôle d'autorisation côté serveur.", "",
              "## Suite proposée", "", "Comparer les réglages de prix et de réserve sur les scénarios de pénurie et d'arrivée, financer durablement les emplois municipaux, et lier les nouvelles capacités d'emploi aux logements. Garder les exports de ce premier passage comme référence. Les objectifs chiffrés de récupération et d'installation restent à choisir avant de déclarer l'économie prête pour un prototype.", "",
              "## Reproduction et fichiers", "", "Depuis la racine du projet :", "", "```bash", f"python3 -m citysim --config config/default.json --output results/first-simulation --seeds {len(samples) // len(runs)}", "```", "",
              "`daily.csv` et `hourly.csv` contiennent les indicateurs ; la consommation n'est réglée qu'à l'heure 23, donc les valeurs alimentaires horaires avant cette clôture ne représentent pas un manque durable. `profiles.csv` et `businesses.csv` décrivent les trajectoires et soldes. `ledger.csv` enregistre les mouvements, `events.json` les causes, `audit.json` les conservations, et `manifest.json` les empreintes des exports. Les dossiers détaillés ne contiennent que la graine de référence ; les autres graines sont synthétisées dans `variability.csv`. `suite.json` rassemble le protocole et les contrôles."]
    (dest / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    chart_svg(dest / "comparison.svg", runs)

