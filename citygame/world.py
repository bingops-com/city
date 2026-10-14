"""Shared collision map, places and player-facing actions."""

WIDTH, HEIGHT = 48, 30
BUILDINGS = [
    {"id": "townhall", "name": "Mairie", "x": 19, "y": 5, "w": 7, "h": 5, "door": [22, 11], "kind": "townhall"},
    {"id": "market", "name": "Épicerie de Nora", "x": 30, "y": 12, "w": 6, "h": 5, "door": [32, 18], "kind": "market"},
    {"id": "bakery", "name": "Boulangerie", "x": 11, "y": 13, "w": 5, "h": 4, "door": [13, 18], "kind": "bakery"},
    {"id": "home_place", "name": "Maison de la place", "x": 9, "y": 5, "w": 5, "h": 4, "door": [11, 10], "kind": "house"},
    {"id": "home_garden", "name": "Maison du jardin", "x": 32, "y": 5, "w": 5, "h": 4, "door": [34, 10], "kind": "house"},
    {"id": "workshop", "name": "Atelier de Malik", "x": 31, "y": 22, "w": 6, "h": 4, "door": [33, 27], "kind": "workshop"},
    {"id": "farm", "name": "Jardins partagés", "x": 8, "y": 22, "w": 6, "h": 4, "door": [11, 27], "kind": "farm"},
]
GOALS = {"garden": {"name": "Planter un petit jardin", "materials": 2, "location": "farm"},
         "bench": {"name": "Fabriquer un banc", "materials": 2, "location": "workshop"}}
JOBS = {"gardener": {"name": "Jardinier municipal", "place": "farm"},
        "delivery": {"name": "Livreur du quartier", "place": "market"}}
NPCS = [
    {"id": "npc32", "name": "Jeanne", "role": "Accueil de la mairie", "start": [22, 11], "shirt": "#6079a0"},
    {"id": "npc35", "name": "Nora", "role": "Épicière", "start": [32, 18], "shirt": "#a06882"},
    {"id": "npc31", "name": "Malik", "role": "Artisan", "start": [33, 27], "shirt": "#ba854d"},
    {"id": "npc18", "name": "Lucie", "role": "Jardinière", "start": [11, 27], "shirt": "#5f8364"},
    {"id": "npc10", "name": "Émile", "role": "Boulanger", "start": [13, 18], "shirt": "#ded7b6"},
    {"id": "npc36", "name": "Sacha", "role": "Habitant", "start": [25, 18], "shirt": "#b77555"},
]


def walkable(x, y):
    if not isinstance(x, int) or not isinstance(y, int) or not 1 <= x < WIDTH - 1 or not 1 <= y < HEIGHT - 1:
        return False
    if 39 <= x <= 45 and 18 <= y <= 25:
        return False
    return not any(b["x"] <= x < b["x"] + b["w"] and b["y"] <= y < b["y"] + b["h"] for b in BUILDINGS)


def layout():
    return {"width": WIDTH, "height": HEIGHT, "buildings": BUILDINGS, "people": NPCS,
            "blocked": [[x, y] for y in range(HEIGHT) for x in range(WIDTH) if not walkable(x, y)]}
