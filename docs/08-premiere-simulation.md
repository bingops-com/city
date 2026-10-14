# Première simulation exécutée

Le 14 octobre 2026, le projet passe de la conception à un moteur économique local. Le moteur est écrit en Python, utilise uniquement la bibliothèque standard et produit des résultats reproductibles. Aucun service persistant ni site n'est déployé.

Le [rapport du premier passage](../results/first-simulation/report.md) contient les résultats, les courbes, les limites et les comparaisons. Les paramètres restent des hypothèses proposées. Les valeurs initiales du plan ont été reprises : 90 jours, pas horaire, 40 PNJ et 8 joueurs, cinq produits et monnaie quotidienne seule.

## Exécuter

Depuis `/opt/homeops/city`, avec Python 3.10 ou supérieur (premier passage exécuté avec Python 3.13.3) :

```bash
python3 -m citysim --config config/default.json --output results/first-simulation --seeds 30
```

Ce passage produit neuf scénarios détaillés avec la graine `20261014`, trente graines supplémentaires par scénario (`20261015` à `20261044`) et trois variantes de référence. Cela représente 282 expériences et 609 120 contrôles horaires de conservation.

Un essai court dans un autre dossier :

```bash
python3 -m citysim --scenario reference --days 10 --seeds 0 --output results/smoke
```

Un scénario de tension isolé :

```bash
python3 -m citysim --scenario shortage --seeds 0 --output results/shortage-check
```

Les fichiers d'un même dossier sont réécrits lorsqu'on rejoue une expérience. Utiliser une autre destination pour conserver le premier passage.

Les vérifications du modèle se lancent avec :

```bash
python3 -m unittest discover -s tests -v
```

## Configuration et unités

[La configuration](../config/default.json) rassemble les paramètres. La monnaie est stockée en centimes entiers ; les stocks sont des unités entières. Un ménage représente ici une seule personne. Tous les ménages actifs ont besoin de deux portions par jour : un pain et un légume de préférence, avec substitution après les premières tentatives d'achat.

| Hypothèse | Première valeur |
| --- | --- |
| Salaire par journée complète | 18 unités, versées pendant les huit heures de travail. |
| Loyer quotidien | 3 unités, payé à la municipalité. |
| Taxe salariale | 8 %, versée à la municipalité. |
| Taxe sur les ventes | 3 %, versée à la municipalité. |
| Dotation par habitant | 300 unités. |
| Trésorerie de chaque entreprise | 1 500 unités. |
| Trésorerie municipale | 12 000 unités. |
| Budget extérieur fini | 100 000 unités. |
| Logements / postes initiaux | 52 logements ; 31 postes privés et 17 municipaux. |
| Réserves initiales et cibles | 144 pains et 144 légumes. |
| Importations de secours | Au plus 24 unités par produit et par jour ; délai de deux jours. |
| Livraison au marché | 180 unités par lot, traitement toutes les deux heures, frais selon distance. |
| Logements par chantier | 8, après cinq jours de besoin durable ; chantier de sept jours. |

Les huit entreprises comprennent deux exploitations céréalières, un moulin, deux boulangeries, deux fermes maraîchères et un atelier de matériaux. Quatre joueurs possèdent initialement une entreprise. Les autres entreprises gardent leurs bénéfices dans leur propre compte ; un acheteur PNJ ne détruit pas de monnaie.

Le prix initial du panier est de 12,45 unités avant réaction tarifaire, livraison et loyer. La conservation quotidienne enlève en moyenne 1 % des céréales et de la farine, 10 % du pain et 6 % des légumes. Les fractions de pertes sont tirées avec la graine ; aucun stock fractionnaire n'est créé.

## Cycle réellement exécuté

1. Au début du jour : arrivées, événements, livraisons prévues, fin des chantiers, routines et affectation des postes et logements.
2. Entre les heures 8 et 15 : production selon personnel et intrants, puis rémunération et taxe salariale. Le réapprovisionnement des intrants passe par les lots de marché entre 6 et 16.
3. Toutes les deux heures : offres avec réservation des marchandises, demandes avec réservation du montant maximal incluant livraison, puis règlement. Les ordres expirent à la fin du lot et les reliquats sont rendus.
4. Entre 16 et 20 : achat du panier préféré ; à 22, tentative de substitution si une portion manque.
5. À 23 : secours personnels immédiatement consommés, loyers et entretien, adaptation des prix et dividendes éventuels, consommation restante et pertes de conservation, commandes d'importation, exports de matériaux et décision de chantier.
6. À chaque heure : conservation monétaire et matière, soldes et stocks non négatifs, absence d'ordre restant ouvert. Les indicateurs alimentaires du jour sont définitifs après l'heure 23.

Les ordres d'achat sont classés par prix limite, les offres par prix demandé, et les égalités sont mélangées par une graine. L'ordre de création des ménages ne donne pas une priorité fixe aux achats. L'extérieur vend à la mairie et achète des matériaux et des services municipaux dans la limite de son budget ; ces transferts apparaissent dans le journal.

La croissance nécessite des ménages sans logement pendant cinq jours, un poste affecté à au moins 55 % des habitants actifs, suffisamment de matériaux et un financement complet. L'approbation collective est programmée pour cette expérience. Des comptes créés sans activité rémunérable ne déclenchent pas un chantier.

## Absence et propriété

Le rapport de temps initial est de six heures simulées pour une heure réelle. Les routines deviennent réduites après 24 heures réelles d'absence et passent en sommeil après 72 heures réelles. L'exécution accélérée du programme ne modifie pas ces délais.

En mode réduit, salaire et loyer sont divisés par deux. Une entreprise dont le propriétaire est en mode réduit voit aussi sa capacité et son entretien diminuer. En sommeil, le ménage n'a plus de salaire, dividende, loyer ni besoin alimentaire ; le logement reste occupé et le commerce ferme temporairement. Les denrées stockées continuent à se conserver selon leur règle ordinaire. Les salariés peuvent chercher un autre poste. Au retour, la reprise nécessite des fonds suffisants.

La suspension des besoins est une abstraction de protection, pas une simulation physiologique. Les profils ne modélisent pas encore les préférences de qualité, la spéculation foncière ou les décisions de coopération. La faible présence connectée conserve les routines et ne procure ni bonus ni pénalité économique.

## Vérifications et portée

Les tests exercent la double réservation de fonds et de biens, les commandes répétées, les remboursements après livraison partielle, l'interdiction d'un échange avec soi-même, les dépenses municipales refusées avant mutation, la conservation sur les neuf scénarios, la répétabilité, les délais d'absence et l'absence de salaire, de loyer et de dividende pendant le sommeil.

Le contrôle matière vérifie, pour chaque produit : stock final = stock initial + production et imports livrés − intrants transformés, consommation, secours, pertes, exports et construction. Les mouvements internes, y compris les réservations, s'annulent. Les importations déjà payées mais en transit restent identifiées séparément.

Les autorisations sont représentées par des décisions programmées. Elles ne constituent pas encore une API sécurisée, une authentification, un système électoral ou une protection contre des transactions concurrentes. Le nombre de postes affectés est distinct du paiement effectif ; quand la mairie manque de fonds, les salaires non versés restent visibles dans le journal d'événements.

La crypto et la modernisation restent différées. La concentration teste un contrôle initial différent et une majoration tarifaire ; elle ne représente pas un processus de rachat. L'injection monétaire garde une consommation essentielle fixe et ne permet donc pas de conclure sur une inflation générale.

## Fichiers produits

| Fichier | Usage |
| --- | --- |
| `report.md`, `comparison.svg` | Résultats interprétés et courbes autonomes. |
| `suite.json` | Configuration, résumés, variantes, nombre de contrôles et empreintes du code. |
| `variability.csv` | Résumés des trente graines supplémentaires par scénario. |
| `config.json`, `summary.json` | Paramètres complets et synthèse de chaque passage détaillé. |
| `daily.csv`, `hourly.csv` | Prix proposés, budgets, stocks, emploi, logement et alimentation. |
| `profiles.csv`, `businesses.csv` | Trajectoires des habitants et bilans des entreprises. |
| `events.json` | Arrivées, absences, pénuries, imports, chantiers et incidents financiers. |
| `ledger.csv`, `audit.json` | Mouvements d'argent, comptes finaux et causes des flux de matière. |
| `manifest.json` | Empreintes SHA-256 des exports détaillés. |

Les courbes portent sur les neuf scénarios de la graine de référence. Les variantes ont leur propre dossier sous `variants/`. Les autres graines produisent une synthèse, sans journal complet afin de limiter la taille des résultats.

Le premier passage fournit aussi `comparison.png`, un aperçu des courbes. Ce rendu a été réalisé avec Matplotlib, présent dans l'environnement de travail. Le moteur produit seul un SVG autonome ; Matplotlib est uniquement nécessaire pour refaire ce rendu facultatif :

```bash
python3 scripts/plot_results.py --results results/first-simulation
```
