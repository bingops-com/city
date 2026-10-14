# Vision et décisions

## Intention

City vise une véritable sandbox de vie : le joueur choisit comment habiter, rencontrer les autres, exercer une activité, créer et transformer son environnement. Ces possibilités doivent agir sur une même ville persistante. La simplicité concerne les commandes, l'accueil et les tâches ordinaires ; la profondeur vient des choix et de leurs conséquences.

Créer un lieu dans lequel les joueurs ont envie de s'installer, de retrouver des visages familiers et de laisser une trace. La ville doit être intéressante à observer même lorsque peu de joueurs sont connectés. Les interactions humaines enrichissent un monde que les habitants fictifs font déjà fonctionner.

Le plaisir repose sur la construction, les relations, les échanges et les conséquences visibles des décisions. Une réussite peut être un commerce rentable, une maison aménagée, un quartier agréable, un métier reconnu ou un projet collectif achevé. Il n'y a pas de victoire finale définie à ce stade.

## Choix validés

| Sujet | Décision |
| --- | --- |
| Projet | Dossier `city` dans `/opt/homeops`, domaine cible `city.lab.bingo`. |
| Monde | Une ville sandbox commune et persistante. |
| Nature du jeu | Simulation de vie ouverte : habitation, relations, activités et transformations durables du monde. |
| Accessibilité | Prise en main simple, possibilités progressivement accessibles, tâches ordinaires délégables. |
| Visite | Carte et vie publique observables sans connexion. |
| Participation | Compte et approbation par bingops pour devenir habitant. |
| Administration | Panel pour gérer les candidatures, la communauté et la simulation. |
| Représentation | 2D vue du dessus oblique, légèrement tournée vers la gauche ; décors en perspective, plus détaillés et moins pixelisés. |
| Interactions | Mélange de déplacement du personnage et de gestion par interfaces. |
| Temps | Cycle accéléré ; rapport exact entre temps réel et temps simulé à déterminer. |
| Population | PNJ clés permanents, PNJ temporaires et joueurs. |
| Réalisme | Causes compréhensibles, choix conséquents, surprises raisonnables. |
| Liberté | Accompagnement progressif, objectifs facultatifs et parcours variés. |
| Développement urbain | Carte simple, expansion liée à l'activité de la communauté. |
| Construction | Catalogue, avec disponibilité évolutive. |
| Économie | Travail, production, vivres, consommation et échanges. |
| Monnaies | Monnaie quotidienne et crypto fictive interne au jeu. |
| Concurrence | Coopération dominante et concurrence commerciale encadrée. |
| Absence | Autonomie puis protection progressive pour les absences prolongées. |
| Politique | Un maire qui ne décide pas de tout, avec une balance des pouvoirs. |
| Ambiance | Coexistence entre ancienneté et modernité. |
| Rythme social | Échanges et informations regroupés pour éviter le flood. |

## Propositions à éprouver

Les règles suivantes donnent une première forme au jeu. Elles ne constituent pas encore des réglages validés :

- Un logement de départ accessible et des emplois salariés disponibles.
- Des besoins de base pris en charge par les routines ordinaires.
- Des propriétés publiques, des locations et des propriétés privées.
- Une économie locale complétée par des échanges avec l'extérieur.
- Une monnaie courante pour les dépenses essentielles et une crypto facultative.
- Des projets urbains déclenchés par les besoins puis arbitrés collectivement.
- Une mémoire structurée des relations avec les PNJ permanents.
- Des mandats municipaux limités, des budgets visibles et des recours.
- Des nouveaux arrivants qui peuvent progresser sans rattraper tout le patrimoine des anciens.

## Questions encore ouvertes

| Décision | Orientation de départ |
| --- | --- |
| Angle exact de la caméra | Direction oblique vers la gauche retenue ; inclinaison précise à ajuster visuellement. Zoom, dézoom et déplacement de la vue dans le prototype. |
| Échelle du monde | Une petite ville extensible ; capacité maximale à mesurer. |
| Durée d'une journée | Plusieurs journées simulées par journée réelle, sans échéances injustes. |
| Profondeur de la vie personnelle | Commencer par logement, travail, besoins simples et relations. Familles et vieillissement restent à discuter. |
| Élections | Durée du mandat, quorum, révocation et conditions de candidature à définir. |
| Construction | Étendue de la personnalisation et conditions d'accès aux bâtiments du catalogue. |
| Crypto | Usages, émission, liquidité et mode de fixation du cours à tester. |
| Protection des absences | Délais, obligations déjà engagées et traitement du foncier. |
| Technique | Choix du moteur de simulation, du rendu et de l'authentification après le premier modèle. |

## Inspirations

Springfield inspire la lisibilité d'une ville animée et le plaisir d'aménager. Les jeux de gestion urbaine inspirent les liens entre emplois, logements, transports et commerces. Les simulations de vie inspirent les routines et les relations. La direction graphique évolue vers un village illustré en perspective, avec des décors fins et une caméra zoomable. Les espaces sociaux persistants donnent la direction communautaire.

Ces références orientent l'expérience. Les personnages, les bâtiments, les textes et les images devront former un univers original.

## Priorités de conception

La ville doit rester accueillante pour un nouveau joueur et viable pour un joueur occasionnel. Les systèmes doivent pouvoir être expliqués par des informations visibles : dépenses, demande, stocks, délais et relations.

Une nouvelle fonctionnalité doit apporter des décisions ou des interactions utiles. Les mécaniques de besoins quotidiens, de trading et de gestion ne doivent pas multiplier les actions répétitives.

Le premier socle réalisé est une économie observable et une tranche graphique locale. La prochaine tranche doit relier vie personnelle, interactions et transformation des lieux dans un petit quartier. Les outils financiers avancés et la grande carte viennent après une boucle de vie convaincante.

## Ce qui doit faire de City une sandbox de vie

| Dimension | Expérience attendue | Lien avec les autres systèmes |
| --- | --- | --- |
| Habiter | Entrer chez soi, utiliser les lieux et aménager un espace personnel. | Droits de propriété, meubles, ressources, dépenses et visites. |
| Rencontrer | Interagir avec des habitants ayant leurs habitudes, préférences et mémoire. | Entraide, échanges, réputation, invitations et événements. |
| Agir | Manipuler des objets, apprendre et pratiquer des activités choisies. | Inventaire, outils, ressources, production et savoir-faire. |
| Entreprendre | Changer de parcours, exercer un métier ou développer une activité. | Demande locale, fournisseurs, clients, personnel et routines. |
| Transformer | Modifier ses lieux et contribuer au quartier. | Construction, usages, fréquentation et besoins des habitants. |
| Faire vivre la ville | Constater des changements pendant et entre les sessions. | Routines réelles, événements contextualisés, projets et décisions collectives. |

Les exemples détaillés restent des propositions de mise en œuvre. La famille, le vieillissement et les autres dimensions encore ouvertes ne deviennent pas des fonctionnalités retenues par cette description.

Un même objet ou événement doit avoir des conséquences dans plusieurs systèmes. Un meuble est placé dans un lieu, possède un propriétaire et provient de ressources réellement achetées ou fabriquées. Une aide donnée à un habitant peut modifier son budget, sa situation et le souvenir qu'il garde du joueur. Le résultat doit être visible dans le monde.

Les routines prennent en charge les tâches répétitives autorisées. Le joueur garde les choix qui donnent une direction à sa vie : logement, relations, activités, créations et engagements. Une courte session doit permettre une interaction intéressante ; une longue session doit ouvrir davantage de possibilités sans rendre la connexion obligatoire.

## Portée du prototype actuel

Le moteur économique teste certains flux de la ville. Le prototype permet déplacements, installation, budget automatique et deux aménagements à emplacement fixé. Ses animations de PNJ ne représentent pas encore tous leurs déplacements simulés ; leurs relations, souvenirs et interactions de vie ne sont pas jouables. Il ne contient pas encore d'intérieurs utilisables, de placement libre d'objets ni de monde partagé entre comptes.

Il s'agit d'un socle technique expérimental. Le nombre de simulations, l'aspect de la carte et la sauvegarde locale ne suffisent pas à mesurer l'avancement du jeu final. Aucun pourcentage global n'est retenu tant que le périmètre et les critères des versions ne sont pas établis.
