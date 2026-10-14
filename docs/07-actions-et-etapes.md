# Actions et étapes

## Point de départ

La conception, les simulations économiques et une première tranche jouable locale sont enregistrées. La [V3 et son prototype](10-v3-et-prototype.md) relient une carte à l'économie, avec deux choix initiaux et des routines automatiques. Les étapes ci-dessous indiquent les acquis et ce qui reste avant un essai partagé.

La cible est une véritable sandbox de vie. Le prototype actuel est un socle expérimental ; les étapes réalisées ne représentent pas des fractions égales du jeu final. Le prochain jalon doit apporter une boucle de vie dans laquelle interactions, créations et habitants partagent des conséquences persistantes.

## Actions possibles maintenant

| Action | Livrable concret | Ce qu'elle permet de décider |
| --- | --- | --- |
| Simulation économique | Moteur local, scénarios reproductibles et rapport comparatif. | Viabilité des métiers, accès des nouveaux, absences, pénuries et croissance. |
| Prototype visuel | Petite carte originale, déplacements et routines visibles de quelques PNJ. | Caméra, échelle, lisibilité, ambiance et qualité de navigation. |
| Maquette des parcours | Écrans de visite, candidature, arrivée, budget, marché et mairie. | Compréhension du joueur et quantité de guidage nécessaire. |
| Définition de l'univers | Quartier initial, personnages permanents et catalogue de départ. | Identité de la ville et premières situations narratives. |

La simulation est recommandée en premier car l'économie, les absences et l'expansion se contraignent mutuellement. Un petit essai visuel peut suivre rapidement pour éviter que le modèle soit développé sans lien avec l'expérience souhaitée.

## Étape 1 Construire la simulation de base

Implémenter les ménages, emplois, produits, entreprises et transactions de la monnaie quotidienne. Ajouter une configuration, une graine aléatoire et les bilans comptables.

Livrables attendus : un scénario de référence reproductible, des exports lisibles et des vérifications de conservation de monnaie et de stocks. Le modèle devrait pouvoir être réutilisé ou porté vers le futur serveur.

**Réalisé au premier passage** : moteur Python sans dépendance externe, configuration unique, pas horaire, scénario de référence et exports CSV/JSON/Markdown/SVG. La technologie du futur serveur reste ouverte.

## Étape 2 Tester les tensions

Ajouter nouveaux arrivants, longues absences, pénurie, concentration et évolution de la carte. Comparer les mécanismes de protection avec leurs effets secondaires.

Livrables attendus : un rapport de problèmes observés, quelques variantes documentées et une proposition de règles initiales. La crypto reste une expérience séparée à ce stade.

**Première comparaison réalisée** : neuf scénarios et trois variantes de référence. Les difficultés de prix, de budget municipal, d'accès à l'emploi et de réserves restent à corriger et à retester. Ces premiers résultats ne constituent pas une validation d'équilibrage.

**Comparaison annuelle réalisée** : [735 expériences sur 360 jours](../results/annual-simulation/report.md), quinze scénarios, deux ensembles de règles et cinq variantes de familles de mécanismes. Le financement et le stockage stabilisent la référence ; l'arrivée de nouveaux résidents et les crises répétées restent des points faibles. La prochaine correction porte sur les effectifs et la viabilité des entreprises après expansion, le revenu des arrivants et la durée des manques alimentaires.

**V3 réalisée** : [744 comparaisons sur un et trois ans](../results/v3-simulation/report.md). Croissance des commerces existants, tarifs coopératifs, délégation et circulation sont comparés avec la V2 sur les mêmes graines. Les résultats de longue durée et des pénuries déterminent les corrections restantes ; une amélioration annuelle ne vaut pas validation générale.

## Étape 3 Construire une tranche jouable

Relier une petite carte, un personnage contrôlable, quelques PNJ, un emploi et un commerce au modèle. Permettre une visite publique et préparer l'installation après approbation.

Livrables attendus : une première session guidée, un cycle de production visible, un bilan personnel et des interactions simples. La carte doit être agréable à observer avant son agrandissement.

**Première tranche locale réalisée** : petite ville illustrée en perspective basse depuis la gauche, caméra zoomable, déplacements, six PNJ affichés, choix de logement et d'activité, budget automatique, jardin et banc facultatifs à emplacement fixé. Elle utilise réellement le moteur V3. Les parcours ont été vérifiés avec le script livré et le gestionnaire HTTP ; la mise en page dans un vrai navigateur reste à vérifier, les restrictions d'exécution bloquant Chromium et les ports TCP.

**Prochaine tranche de vie proposée** : un logement avec intérieur utilisable et aménagement libre, un inventaire, une activité produisant des ressources, et quelques PNJ avec habitudes liées au moteur et mémoire d'interactions. Relier ces éléments : obtenir un objet, le placer chez soi, échanger ou aider un voisin, puis retrouver les conséquences après reprise. Les comptes et permissions du futur monde partagé doivent être prévus dans cet état de jeu.

Cette tranche est prête à essayer lorsque plusieurs parcours fonctionnent dans le même quartier : aménager chez soi, produire et échanger, développer une relation. Le joueur peut passer d'un parcours à l'autre, les objets et les relations sont sauvegardés, et les PNJ utilisent les changements pertinents dans leurs routines. Les tâches quotidiennes restent délégables. Ces fonctionnalités restent à implémenter ; la tranche graphique existante ne les valide pas.

## Étape 4 Introduire la persistance et l'administration

Définir comptes, whitelist, sauvegardes, reprise et règles de commandes. L'autorisation et les transactions sont contrôlées côté serveur. Les commandes sont protégées contre les répétitions et les opérations concurrentes.

Livrables attendus : un accès approuvé fonctionnel, un panel minimal de bingops, un historique des actions et un redémarrage sans perte ou duplication. Une vérification de restauration fait partie de la validation.

**Socle local réalisé** : journal SQLite, reprise contrôlée, commandes sans duplication, accès privé au carnet et export JSON restaurable. Le joueur local est préapprouvé. Comptes multijoueurs, whitelist réelle et panel de bingops restent à réaliser avant l'ouverture partagée.

La séparation entre affichage, simulation et commandes facilite une visite publique qui n'expose que les informations autorisées. Le principe d'autorité du serveur est décrit dans la [documentation Unity](https://docs.unity.com/en-us/cloud-code/server-authority) ; cela n'impose pas l'usage de Unity pour city.

## Étape 5 Organiser un essai communautaire

Inviter un petit groupe approuvé à explorer, travailler, commercer et s'absenter. Observer les difficultés réelles et recueillir les explications des participants.

Livrables attendus : ajustements d'ergonomie, de rythme, de coût et de guidage. Le test doit inclure des nouveaux arrivants après le début de la ville et des personnes présentes à des horaires différents.

## Étape 6 Étendre les systèmes validés

Ajouter progressivement projets municipaux, élections, nouveaux quartiers, métiers et crypto fictive. Chaque extension conserve un scénario de comparaison et des règles de recours.

L'ouverture sur `city.lab.bingo` constitue une étape d'exploitation distincte, avec domaine, accès, persistance et diagnostic opérationnels. Le présent dossier prépare la conception et n'effectue aucune configuration d'infrastructure.

## Hypothèses à réexaminer après le premier passage

Les choix suivants peuvent commencer comme hypothèses configurables :

- Population initiale et nombre de logements disponibles.
- Budget d'installation et revenu accessible d'un premier emploi.
- Recettes et capacités de la chaîne alimentaire.
- Rapport entre temps réel et temps simulé.
- Règles de mise en sommeil et traitement des engagements.
- Définition d'un besoin durable permettant un projet d'expansion.

Ces hypothèses sont rassemblées dans une configuration unique, accompagnée de leurs unités. Aucun montant illustratif ne devient une règle validée par simple présence dans un exemple.

## Choix recommandé pour la suite

Construire la tranche de vie décrite à l'étape 3 et vérifier son rendu dans un vrai navigateur. Traiter en parallèle les échecs de la V3 sur les pénuries et la longue durée. Faire ensuite essayer ce quartier interactif à quelques personnes et mesurer leur liberté d'action, la compréhension des conséquences et l'intérêt de revenir. Préparer les comptes approuvés et l'administration pour un essai commun. Les commandes restent simples et les routines prennent en charge les répétitions, tandis que les possibilités de vie s'enrichissent.
