# Simulation annuelle approfondie

Une seconde expérience étend le modèle sur 360 jours, avec saisons et scénarios plus longs. Elle conserve le [premier passage](../results/first-simulation/report.md) et le moteur initial ; les extensions sont dans [citysim/extended.py](../citysim/extended.py).

Le [rapport annuel](../results/annual-simulation/report.md) compare quinze scénarios et leurs trajectoires, puis distingue les effets des cinq familles de réglages. Tous les changements de règles et critères restent des propositions d'expérience.

## Exécuter

Avec Python 3.10 ou supérieur, depuis `/opt/homeops/city` :

```bash
python3 -m citysim.annual --config config/extended.json --output results/annual-simulation --seeds 20 --workers 4
```

Ce passage compare `legacy` et `balanced` sur les quinze scénarios. Cinq variantes de mécanismes sont aussi comparées sur la référence. Il y a 35 cas, chacun exécuté avec la graine détaillée `20261014` et vingt graines supplémentaires `20261015` à `20261034` : **735 expériences et 6 350 400 contrôles horaires**. Les quatre processus servent uniquement à exécuter des calculs indépendants ; ils ne changent aucune règle temporelle.

Essai court dans un dossier distinct :

```bash
python3 -m citysim.annual --config config/extended.json --output results/annual-smoke --days 10 --seeds 0 --workers 2
```

Vérifications du modèle et des résultats :

```bash
python3 -m unittest discover -s tests -v
```

```bash
python3 -m citysim.verify_annual --results results/annual-simulation
```

Le moteur utilise la bibliothèque standard. Les courbes du rapport sont produites avec Matplotlib si disponible ; les calculs et exports tabulaires restent possibles sans lui. Les résultats d'un même dossier sont réécrits lors d'un nouveau passage. `progress.json` indique le nombre d'expériences déjà terminées.

## Périmètre supplémentaire

| Dimension | Modèle annuel |
| --- | --- |
| Horizon | 360 jours, douze bilans de trente jours ; pas économique horaire. |
| Saisons | Capacité agricole variant de ±20 % sur un cycle de 360 jours, en plus de la météo journalière bornée. |
| Installation | Arrivées successives aux jours 20, 27, 90 et 180 ; 84 résidents au terme du scénario d'arrivées. |
| Absences | Deux propriétaires absents de J20 à J140 ; six joueurs cessant leur activité de J25 à J220. Les délais de protection restent mesurés en temps réel. |
| Production et marché | Intrants, travail, livraison limitée, réservations, recettes et conservation ; insolvabilité et possibilité de vente du stock dans la variante de croissance. |
| Visiteurs | Deux PNJ de passage toutes les deux semaines, trois jours de séjour, 65 unités de budget chacun transférées de l'extérieur. Le budget inutilisé est rendu à leur départ. |
| Dépenses facultatives | Achat plafonné de matériaux pour des aménagements personnels, seulement au-delà d'une réserve de dépenses essentielles. Les matériaux sont consommés et tracés ; leur localisation n'est pas simulée. |
| Profils | Routines et propriétés initiales, contribution volontaire du coopérateur, stockage et revente tentés par l'opportuniste avec fonds et marchandises réellement disponibles. |
| Prix | Contrôle historique fondé sur le stock du vendeur, comparé à un prix fondé sur coûts et stocks publics agrégés. Prix proposés et prix réellement échangés sont distincts. |
| Finances publiques | Salaires effectivement versés, impayés, revenus locaux, contrats extérieurs limités et adaptation du financement aux besoins et à une cible de trésorerie. |
| Croissance | Logements, priorité aux matériaux de construction, nouvelles chaînes alimentaires collectives et emplois publics supplémentaires. Chaque ouverture exige un financement existant. |
| Répartition | Bénéfices partagés, réserves de travail, dividendes bornés, prélèvement sur les liquidités élevées et détention initiale limitée. |
| Modernisation | Investissement payé pour augmenter certaines capacités de 30 % ; emplois et recettes conservés. |
| Gouvernance | Approbations programmées, engagements et bénéficiaires contrôlés, refus de dépenses non autorisées, intéressées ou hors budget. |
| Résilience | Fenêtres de récupération de sept jours comprenant alimentation et rémunération effective, avant le prochain événement. |

Les profils n'ont pas de connaissance des futurs événements ni des budgets des autres ménages. L'aléatoire météorologique est appairé entre politiques par la graine. Une règle qui change les transactions ou les pertes modifie ensuite la trajectoire ; les plages sur les graines décrivent cette variabilité.

## Calendriers de tension

Les neuf scénarios économiques de départ sont repris avec des durées plus longues et des arrivées successives. Six comparaisons supplémentaires portent sur :

- Cinq pénuries agricoles de quinze jours à partir de J60, J120, J180, J240 et J300.
- Une capacité de livraison réduite à 40 unités par lot de J60 à J89 et un délai d'importation porté à six jours.
- L'arrêt de nouveaux contrats extérieurs, exports de matériaux et commandes d'importation de J120 à J179. Les livraisons déjà engagées restent honorées.
- L'investissement dans de nouvelles capacités au jour 100, seulement si l'entreprise peut payer.
- Quatre tentatives de dépense municipale refusées au jour 35.
- Des tentatives de double réservation de stocks et d'argent et de répétition d'ordre au jour 35.

La concentration est toujours une différence de contrôle initial, pas un rachat simulé. La variante de répartition limite ce contrôle à deux entreprises. La crypto reste un module ultérieur séparé ; santé, familles, élections humaines et préférence pour une qualité artisanale ne sont pas couvertes.

## Comparaisons de règles

[config/extended.json](../config/extended.json) décrit le calendrier, la durée, les paramètres des extensions, les politiques et les critères. Les paramètres fondamentaux sont lus depuis [config/default.json](../config/default.json).

`legacy` conserve les règles économiques historiques dans le nouveau monde annuel. `balanced` active stockage, prix publics, financement, croissance et répartition. Les variantes `storage_only`, `pricing_only`, `finance_only`, `growth_only` et `distribution_only` activent une seule famille sur la référence.

La comparaison de deux politiques utilise les mêmes graines et le même calendrier. Il ne faut pas attribuer une amélioration à un seul réglage à partir du résultat de `balanced` ; les variantes de famille et `paired_comparison.csv` aident à distinguer effets et interactions.

La cible de contrats municipaux utilise les revenus locaux et les dépenses d'importation observés dans les sept derniers jours, les salaires prévus et un retour progressif vers la trésorerie cible sur trente jours. En croissance, les besoins de logements et d'emploi observés augmentent cette cible. L'extérieur conserve un plafond de demande et un budget fini : une demande programmée n'est payée que si ces fonds existent.

Une chaîne collective consomme quarante matériaux, paie une prestation de construction et reçoit quatre trésoreries de démarrage financées par la ville. Ses quatre entreprises créent sept postes. Le capital est réservé pendant le chantier et transféré aux entreprises à l'ouverture ; aucune émission n'est implicite. Les ouvertures sont limitées à quatre chaînes pour cette expérience. Le financement ne garantit pas leur viabilité ultérieure.

## Indicateurs et conservation

Les bilans suivent alimentation moyenne et quotidienne, plus longue pénurie, budgets minimaux et médians, dépenses essentielles, emplois affectés et réellement payés, logement, attente d'installation, réserves, concentration des ventes aux ménages, partage de bénéfices, aides, impayés et dépendance extérieure.

Le Gini des liquidités mesure les portefeuilles. Le second Gini ajoute les trésoreries et stocks des entreprises détenues, valorisés aux prix initiaux ; il exclut la valeur des bâtiments, du foncier et des entreprises collectives sans propriétaire joueur. Il s'agit d'une mesure partielle de patrimoine.

Les critères de comparaison sont provisoires : 99 % de portions servies sur l'année, au plus sept jours consécutifs sous ce seuil, 80 % d'emploi payé en fin d'expérience, aucun ménage sans logement, aucun salaire municipal non versé, sept jours de réserve salariale et un Gini des liquidités inférieur ou égal à 0,6. Ils n'établissent pas le plaisir de jeu ni un accord communautaire sur la distribution des richesses.

Chaque heure vérifie que les comptes et stocks restent non négatifs et que la monnaie et la matière se conservent. Les gains de production, transformations, achats extérieurs, pertes, consommation et construction ont des causes explicites. Les investissements et aides déplacent des fonds existants ; les dotations d'arrivants et l'injection expérimentale sont les seules émissions de ces scénarios.

La vérification indépendante rejoue toutes les écritures monétaires détaillées, contrôle les comptes finaux, les audits matière et les empreintes. Elle vérifie également les empreintes des exports de la première simulation.

Un diagnostic financier complémentaire attribue les paiements des comptes de réservation à leur acheteur et distingue recettes, apports de capital, intrants, salaires, entretien, taxes, dividendes, partage et investissement. Le premier rapport annuel inclut ce diagnostic. Pour le refaire et l'ajouter au rapport :

```bash
python3 -m citysim.financial_diagnostics --results results/annual-simulation --append-report
```

## Résultats conservés

| Fichier | Rôle |
| --- | --- |
| `report.md` | Résultats, causes, personnes touchées, limites et suite proposée. |
| `comparison.svg/png`, `trajectories.svg/png` | Comparaisons entre règles et trajectoires sur la graine détaillée. |
| `suite.json`, `runs.jsonl` | Protocole, code utilisé et synthèse de toutes les expériences. |
| `comparison.csv`, `paired_comparison.csv` | Moyennes, plages et différences entre graines appairées. |
| `politique/scénario/daily.csv`, `monthly.csv` | Indicateurs quotidiens et bilans de trente jours. |
| `profiles.csv`, `cohorts.csv`, `businesses.csv` | Trajectoires par profil, génération d'arrivée et entreprise. |
| `household_daily.csv.gz`, `hourly.csv.gz` | Trajectoires quotidiennes individuelles et indicateurs horaires. |
| `ledger.csv.gz`, `initial_accounts.json`, `audit.json` | Journal complet compressé, comptes de départ et conservations. |
| `events.json`, `visitors.json`, `flows.json` | Chronologie, séjours et flux monétaires par cause. |
| `financial_diagnostics.csv/md` | Marges par entreprise et période, notamment avant les premiers arrêts de commerce. |
| `manifest.json`, `verification.json` | Empreintes par passage et résultat de vérification indépendante. |

La compression ne supprime pas les transactions : les fichiers `.csv.gz` contiennent les journaux complets des trente-cinq cas détaillés. Les autres graines conservent seulement leur synthèse et appliquent les mêmes contrôles horaires.

## Bilan de vérification du passage

Les 25 tests du moteur passent. La vérification indépendante ferme les comptes de 735 expériences, rejoue 16 384 575 écritures monétaires détaillées et contrôle les 560 empreintes des fichiers détaillés. Les 108 empreintes des exports historiques restent identiques.

La référence avec les règles combinées satisfait les critères provisoires sur 21 graines sur 21. Le scénario d'arrivées loge ses 84 résidents, mais n'en rémunère qu'environ 64,7 % en équivalents de travail en fin d'année et laisse les nouvelles cohortes avec très peu de liquidités. Les pénuries répétées restent au-dessus de 99 % d'alimentation sur l'année, mais dépassent la durée de manque acceptable proposée. La référence seule ne suffit donc pas à valider l'équilibrage.
