# city

`city.lab.bingo` est un projet de jeu de vie communautaire dans une ville persistante, en 2D vue du dessus oblique, avec des décors illustrés en perspective. Les joueurs y habitent au milieu de personnages fictifs, travaillent, commercent, aménagent leurs propriétés et participent à l'évolution de leur ville.

La cible est une véritable **sandbox de vie** : habitation, relations, activités et transformations du monde sont reliées. La prise en main doit rester simple, avec de la profondeur dans les possibilités. Le prototype actuel couvre un socle technique ; intérieurs utilisables, aménagement libre, inventaire interactif, relations avec les PNJ et monde multijoueur restent à construire. Le [prochain jalon](docs/07-actions-et-etapes.md) porte sur une boucle de vie réunissant ces premières possibilités dans un quartier.

La ville est visible sans connexion. Pour y vivre, il faut un compte approuvé par **bingops**, administrateur du jeu. Une petite carte initiale grandit selon l'activité réelle de la communauté. L'univers mêle bâtiments anciens, métiers traditionnels et technologies modernes.

## État du projet

Le dépôt public conserve le code, la conception, les rapports et les figures.
Les données détaillées générées sous `results/`, les parties locales sous
`data/` et les caches restent dans le home privé de développement ; les commandes
de simulation ci-dessous permettent de reconstruire les résultats détaillés.

Conception, simulations économiques et première tranche jouable locale au 14 octobre 2026. La V3 compare l'accueil des nouveaux habitants et la viabilité des commerces sur un et trois ans. Le prototype relie une carte en perspective, des déplacements, un budget automatique et des aménagements facultatifs au même moteur. Aucun site n'est déployé. `city.lab.bingo` est le domaine cible ; sa configuration ne fait pas partie de cette étape.

Le [rapport annuel](results/annual-simulation/report.md) compare les prix, les réserves, le financement municipal, la croissance et la répartition des bénéfices. Le [premier rapport](results/first-simulation/report.md) reste conservé comme référence historique.

Le travail courant est décrit dans [V3 et prototype](docs/10-v3-et-prototype.md), avec un [rapport comparatif](results/v3-simulation/report.md) et un [aperçu du dessin de la carte](results/prototype/map-preview.png). Le parcours demande deux choix initiaux, logement et activité ; salaire, courses et loyer suivent ensuite une routine. Aucun passage quotidien n'est obligatoire.

## Lancer le prototype local

Avec Python 3.10 ou supérieur, depuis la racine du projet :

```bash
python3 -m citygame --port 8092
```

Ouvrir `http://127.0.0.1:8092` sur la machine qui exécute cette commande. Déplacements au clic, aux flèches ou avec ZQSD. Zoom à la molette, aux boutons ou par pincement ; glisser pour déplacer la vue. « Vue entière » montre le quartier et « Me retrouver » recentre sur le personnage. La partie est sauvegardée dans `data/prototype.sqlite` et reprise au redémarrage ; un export JSON et sa restauration sont disponibles. Les journées avancent uniquement dans un onglet actif, avec pause et avance manuelle. Ce rythme d'essai précède la vraie ville persistante et multijoueur.

L'environnement de réalisation bloque les ports TCP et Chromium. Les parcours et transactions ont été vérifiés avec le véritable gestionnaire HTTP et un DOM de test ; la mise en page dans un navigateur reste à vérifier sur la machine de lancement.

## Lire la conception

| Document | Contenu |
| --- | --- |
| [Vision et décisions](docs/01-vision-et-decisions.md) | Concept, choix validés, propositions et questions restantes. |
| [Monde et expérience de jeu](docs/02-monde-et-experience.md) | Carte, progression, personnages, routines et accueil des joueurs. |
| [Économie et échanges](docs/03-economie-et-echanges.md) | Vivres, métiers, monnaie, marché, crypto fictive et absences. |
| [Gouvernance et administration](docs/04-gouvernance-et-administration.md) | Répartition des pouvoirs, mairie, whitelist et panel de bingops. |
| [Équilibrage et risques](docs/05-equilibrage-et-risques.md) | Déséquilibres prévisibles, prévention et indicateurs. |
| [Plan de simulation](docs/06-plan-de-simulation.md) | Modèle proposé, scénarios, mesures et conditions de passage au prototype. |
| [Actions et étapes](docs/07-actions-et-etapes.md) | Ordre de réalisation, livrables et décisions à prendre. |
| [Première simulation exécutée](docs/08-premiere-simulation.md) | Commandes, hypothèses, cycle du moteur et portée des vérifications. |
| [Simulation annuelle approfondie](docs/09-simulation-annuelle.md) | Année simulée, scénarios, familles de règles, cohortes et vérification indépendante. |
| [V3 et prototype simple](docs/10-v3-et-prototype.md) | Accueil, comparaison sur trois ans, parcours jouable, sauvegardes et limites. |

## Décisions structurantes

- Une ville commune, persistante et publique à observer.
- Des joueurs approuvés par bingops pour devenir habitants.
- Des déplacements directs et des interfaces de gestion complémentaires.
- Un temps accéléré, avec des règles adaptées aux absences réelles.
- Des habitants fictifs permanents et des personnages de passage.
- Une simulation crédible et un aléatoire contextualisé et limité.
- Des possibilités guidées, avec une liberté de parcours.
- Une construction depuis un catalogue évolutif.
- Une coopération dominante et une concurrence commerciale encadrée.
- Des échanges de vivres et de monnaies, dont une crypto entièrement fictive.
- Un maire avec des pouvoirs réels mais partagés et limités.

## Première simulation exécutée

Le moteur simule 40 PNJ et 8 joueurs pendant 90 jours, avec monnaie quotidienne, salaires, production, marché, logement, budget municipal et expansion. Il compare référence, faible présence, arrivées, départ, absence, pénurie, concentration, injection monétaire et pénurie combinée à des absences.

Depuis la racine du dossier, avec Python 3.10 ou supérieur et sans installation de dépendances :

```bash
python3 -m citysim --config config/default.json --output results/first-simulation --seeds 30
```

Le [rapport](results/first-simulation/report.md), les [courbes](results/first-simulation/comparison.svg) et les exports CSV/JSON sont enregistrés dans `results/first-simulation`. Les paramètres et unités sont dans [config/default.json](config/default.json). Rejouer cette commande réécrit les résultats dans ce dossier ; choisir un autre `--output` pour préserver un passage.

## Simulation annuelle approfondie

735 expériences comparent quinze scénarios sur 360 jours, avec vingt graines supplémentaires par cas. Les nouvelles mesures distinguent les postes attribués des salaires réellement payés, les arrivants des anciens et les liquidités du patrimoine entrepreneurial. Elles suivent aussi visiteurs, saisons, nouvelles entreprises, partage de bénéfices, incidents de transport et interruption des échanges extérieurs.

```bash
python3 -m citysim.annual --config config/extended.json --output results/annual-simulation --seeds 20 --workers 4
```

Consulter le [rapport annuel](results/annual-simulation/report.md), les [comparaisons](results/annual-simulation/comparison.svg) et les [trajectoires](results/annual-simulation/trajectories.svg). La [configuration annuelle](config/extended.json) précise les hypothèses. La commande réécrit sa destination ; la première simulation reste dans un dossier distinct.

Vérifier les écritures exportées et les empreintes :

```bash
python3 -m citysim.verify_annual --results results/annual-simulation
```

Vérifications du moteur :

```bash
python3 -m unittest discover -s tests -v
```

La simulation évalue des hypothèses économiques et des règles. Le plaisir de jeu, l'attachement aux PNJ et la compréhension de l'interface demandent ensuite des essais avec de vraies personnes.

## Comparaison V3

744 expériences : quinze scénarios V2/V3 et quatre variantes isolées sur 360 jours, puis trois scénarios V2/V3 sur 1080 jours. La simulation historique reste conservée. La comparaison utilise les mêmes graines et la même dotation initiale.

```bash
python3 -m citysim.welcoming --config config/v3.json --output results/v3-simulation --seeds 20 --long-seeds 4 --workers 4
```

Cette commande réécrit sa destination. Pour conserver le passage livré, utiliser un autre dossier `--output`.

```bash
python3 -m citysim.verify_v3 --results results/v3-simulation
```

Les journaux détaillés de la graine de référence sont dans les sous-dossiers `annual` et `long` ; toutes les graines figurent dans `runs.jsonl`. Les critères d'accueil prennent en compte le premier salaire, le délai de logement, les dépenses essentielles, les réserves et l'accès alimentaire individuel.

## Convention de lecture

**Validé** désigne un choix explicitement retenu dans la discussion. **Proposé** désigne une solution de conception à tester. **À préciser** désigne une décision ouverte. Les exemples de personnes, les montants et les seuils illustratifs ne fixent pas le contenu définitif du jeu.

Les réglages chiffrés sont centralisés dans la configuration de simulation. Une modification d'équilibrage doit être accompagnée de son effet attendu et d'une comparaison avec le scénario de référence. Les résultats favorables d'une variante ne valident pas automatiquement ses paramètres.
