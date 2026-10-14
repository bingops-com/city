# Plan de simulation

## Question à résoudre

La première simulation doit vérifier si une petite ville peut fonctionner durablement avec peu de joueurs, accueillir des arrivants et absorber des absences ou des pénuries sans concentrer toutes les possibilités chez quelques personnes.

Le livrable est un moteur local sans interface graphique, avec paramètres explicites et résultats exportables. Ce document conserve le protocole de conception. Un premier moteur et un premier passage existent désormais ; leur périmètre réellement exécuté est décrit dans [Première simulation exécutée](08-premiere-simulation.md), avec les [résultats](../results/first-simulation/report.md).

## Périmètre initial

Le modèle commence avec une monnaie courante, des logements, des emplois, une production alimentaire courte, un marché et un budget municipal. Les PNJ ont des budgets et des besoins. Les joueurs sont représentés par des comportements simulés.

Le déplacement est d'abord représenté par des distances entre lieux et une capacité de livraison. Le rendu pixel art, les dialogues détaillés et la vie familiale ne sont pas nécessaires pour comparer les règles économiques.

La crypto est un second module d'expérience. La politique est d'abord représentée par des permissions, des budgets et des décisions programmées ; une simulation ne peut pas prédire les alliances humaines.

## Modèle minimal

| Entité | État nécessaire |
| --- | --- |
| Ménage | Membres, budget, logement, besoins, préférences et routine. |
| Travailleur | Employeur, disponibilité, rémunération et activité. |
| Entreprise | Propriétaire, trésorerie, stocks, recette, capacité, personnel et prix. |
| Bâtiment | Usage, capacité, emplacement, coût et entretien. |
| Produit | Unité, conservation, substituts éventuels et chaîne de production. |
| Marché | Ordres, réservations, exécutions et frais. |
| Municipalité | Budget, réserves, engagements, projets et droits de décision. |
| Quartier | Parcelles, occupation, accès aux services et conditions d'expansion. |
| Événement | Conditions, début, durée, effets bornés et moyens de réponse. |
| Joueur simulé | Date d'arrivée, présence, stratégie et décisions autorisées. |

## Paramètres illustratifs

Ces valeurs servent uniquement à définir une première expérience reproductible : elles ne dimensionnent pas le futur serveur et ne fixent pas les paramètres de jeu.

| Paramètre | Point de départ proposé |
| --- | --- |
| Durée | 90 jours simulés. |
| Pas de calcul économique | Une heure simulée. |
| Population fictive permanente | 40 habitants. |
| Joueurs simulés de départ | 8, avec plusieurs rythmes de présence. |
| Produits | Céréales, farine, pain, légumes et matériau de construction. |
| Aléatoire | Une graine de référence, puis 30 graines pour tester la variabilité. |
| Marché | Traitement périodique configurable. |
| Monnaies au premier passage | Monnaie courante seule. |

Le rapport entre temps réel et temps simulé reste configurable. Une absence est définie en durée réelle, puis traduite dans la simulation. Accélérer le moteur pour une expérience ne doit pas changer les règles d'absence.

## Cycle de calcul proposé

1. Appliquer les changements programmés, les arrivées et les événements.
2. Actualiser les routines et la disponibilité des personnages.
3. Produire selon le travail, les recettes et les stocks disponibles.
4. Verser les revenus et exécuter les obligations arrivées à échéance.
5. Former les demandes et les ordres dans les limites des budgets.
6. Résoudre les échanges et les livraisons.
7. Consommer, entretenir et appliquer les pertes de conservation.
8. Calculer les indicateurs, les besoins et les possibilités de projet.
9. Enregistrer les décisions, leurs causes et les bilans.

L'ordre exact est une hypothèse à tester. Une règle d'exécution fixe peut avantager certains agents ; l'attribution des ressources rares et les priorités du marché doivent être explicites.

## Profils de joueurs simulés

Le salarié occasionnel cherche un budget prévisible. Le commerçant actif ajuste son stock et ses prix. L'artisan privilégie la qualité. Le nouvel arrivant dispose de peu de capital. Le propriétaire cherche à étendre son patrimoine. Le coopérateur participe aux projets. Un acteur opportuniste essaie de monopoliser les vivres ou d'exploiter les aides.

Chaque stratégie voit les informations auxquelles un joueur aurait accès. Elle ne doit pas connaître les événements futurs ni les budgets privés des autres. Les profils servent à explorer des comportements ; ils ne représentent pas toute la diversité des personnes réelles.

## Scénarios à comparer

| Scénario | Modification | Question |
| --- | --- | --- |
| Référence | Population et activité relativement stables. | Salaires, coûts et consommation peuvent-ils coexister ? |
| Faible présence | Peu de joueurs actifs, PNJ maintenus. | La ville reste-t-elle viable et observable ? |
| Arrivées rapides | Nouveaux joueurs et demande de logements. | Peuvent-ils s'installer sans enrichir uniquement les anciens ? |
| Départ massif | Forte baisse durable de l'activité. | La ville peut-elle se stabiliser puis reprendre ? |
| Absence prolongée | Mise en sommeil de certains commerces. | Les autres acteurs et les personnes absentes restent-ils protégés ? |
| Pénurie | Production alimentaire temporairement réduite. | Réserves, importations et adaptation offrent-elles plusieurs réponses ? |
| Concentration | Un acteur acquiert une part importante des moyens de production. | Les coûts et alternatives limitent-ils sa domination ? |
| Excès de monnaie | Injection supplémentaire identifiée. | Les prix essentiels et l'accès des nouveaux se dégradent-ils ? |
| Modernisation | Nouveau procédé de production disponible. | Les anciens métiers gardent-ils un débouché ? |
| Abus municipal | Tentative de dépense hors budget ou intéressée. | Les règles empêchent-elles l'opération avant son application ? |
| Abus économique | Aide revendue, commandes répétées ou échanges artificiels. | Le modèle permet-il un gain sans coût ni demande réelle ? |
| Crypto ultérieure | Seconde monnaie et comportements spéculatifs. | Les bénéfices d'usage compensent-ils les déséquilibres ajoutés ? |

Chaque scénario est d'abord comparé à la référence en changeant un mécanisme à la fois. Des scénarios combinés testent ensuite les interactions, par exemple pénurie et absence du principal fournisseur.

## Vérifications obligatoires du modèle

- La comptabilité monétaire ferme à chaque étape.
- Un stock ne devient jamais négatif ; toute création ou consommation a une cause.
- Un ordre ne réserve pas plusieurs fois les mêmes fonds ou marchandises.
- Une commande répétée n'est pas exécutée deux fois.
- Une absence protégée ne permet pas un revenu infini sans charge.
- Une décision municipale ne dépasse pas ses droits ni le budget engagé.
- Une expansion ne se déclenche pas sur les seuls comptes créés.
- Les scénarios sont reproductibles avec la même configuration et la même graine.

Ces vérifications détectent des erreurs de modèle. Elles ne démontrent pas que l'économie est plaisante ou socialement équitable.

## Résultats attendus

Chaque expérience produit un résumé de configuration, une série temporelle, une chronologie d'événements et des indicateurs par profil. Les courbes utiles concernent le panier essentiel, les revenus, les réserves, les prix, l'emploi, les logements et la concentration.

Un rapport doit expliquer les difficultés et les changements de régime : pourquoi un commerce ferme, pourquoi le logement manque, quel acteur bénéficie d'une pénurie. Les opérations administratives et les aides sont visibles dans le bilan.

Les exportations sont CSV pour les mesures, JSON pour la configuration et les événements, et Markdown pour le rapport. Le premier passage fournit aussi un graphique SVG autonome dans [results/first-simulation](../results/first-simulation/report.md).

## Passage au prototype

Le modèle doit être comptablement correct, offrir une voie d'installation et éviter les blocages durables dans les scénarios retenus. Les objectifs chiffrés de budget et de récupération seront définis après le premier passage.

Un prototype jouable vérifiera ensuite des questions différentes : comprend-on les choix, le déplacement est-il agréable, les PNJ deviennent-ils familiers, les obligations restent-elles légères ? Une simulation économique favorable ne remplace pas cette validation.
