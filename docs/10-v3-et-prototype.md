# V3 et première tranche jouable

Le projet dispose maintenant d'une comparaison économique V2/V3 et d'un prototype local utilisant le même moteur. Le joueur choisit son logement et son activité, puis découvre la ville. L'équilibrage reste une hypothèse à tester ; les résultats ne remplacent pas l'observation de joueurs.

## Garder le jeu simple

Deux choix sont nécessaires à l'installation : une maison et une activité. Les deux logements ont le même loyer et les deux activités le même salaire municipal. Le choix porte sur la vie souhaitée dans le quartier. Les conséquences budgétaires sont visibles avant confirmation.

Le personnage suit ensuite sa routine : travail, salaire, panier alimentaire et loyer. Le guide montre le reste prévu par journée ; le budget détaillé et le bilan sont repliés et disponibles à la demande. Une consigne courte et des repères sur la carte accompagnent chaque étape. Le joueur n'a pas à connaître les mécanismes fiscaux, placer des ordres de marché ou payer chaque dépense manuellement.

Un jardin et un banc constituent deux petits objectifs facultatifs. Le joueur rejoint le lieu indiqué et confirme l'aménagement. Le moteur achète et consomme réellement les matériaux ; il conserve au moins trois jours de nourriture et de loyer avant d'autoriser la dépense. Un objectif terminé ne peut être payé une seconde fois. On peut changer d'objectif sans coût.

Les déplacements fonctionnent au clic, aux flèches, avec ZQSD ou WASD. Sur téléphone, le clic et les boutons directionnels sont prévus. Six personnages accompagnent sept lieux sur une carte originale de 48 × 30 cases. Leur animation illustre des routines ; leur déplacement graphique n'est pas une simulation physique des trajets commerciaux.

La vue est désormais oblique et plus basse, prise depuis la gauche, avec les côtés gauches et davantage de façades visibles, ainsi que des toits raccourcis en perspective. Le dessin utilise des formes vectorielles antialiasées : tuiles, volets, étals, arbres, plantations, fontaine et mobilier. La résolution du canvas suit la taille de la fenêtre et la densité de l'écran ; les décors ne sont plus des sprites agrandis à gros pixels.

Zoomer avec la molette, les boutons +/− ou le pincement. Le zoom garde le point visé au même endroit. Glisser déplace la caméra ; « Vue entière » revient à l'ensemble du quartier et « Me retrouver » centre le personnage. Les touches +/− et 0 offrent les mêmes commandes. Les clics sur les toits et les repères utilisent la projection de la caméra pour rejoindre le bon bâtiment. Un chemin pointillé indique le trajet choisi ; le budget économique ne change pas lors des manipulations de caméra.

Le prototype avance d'une journée toutes les 60 secondes lorsque l'onglet est actif, une fois l'installation terminée. Pause et avance manuelle restent accessibles. Un onglet masqué ou une partie fermée n'ajoute aucune charge. Ce comportement facilite l'essai : il faudra encore définir les absences dans la future ville commune, dont le serveur continuera de vivre.

## Essayer et conserver sa partie

Python 3.10 ou supérieur suffit pour le moteur et le serveur local, sans dépendance supplémentaire. Depuis la racine du projet :

```bash
python3 -m citygame --port 8092
```

Ouvrir `http://127.0.0.1:8092` sur cette même machine. Le serveur écoute uniquement sur l'interface locale. La carte est visible avant installation ; le personnage Camille est préapprouvé pour cet essai. La gestion de comptes et la véritable whitelist de bingops restent à construire.

Les commandes sont enregistrées dans `data/prototype.sqlite`. Arrêter avec Ctrl+C, puis relancer la même commande reprend la partie. Le bouton Sauvegarde exporte un fichier JSON contenant les commandes et les contrôles d'intégrité. Pour restaurer cet export dans une nouvelle partie enregistrée :

```bash
python3 -m citygame --port 8092 --save data/restored.sqlite --restore city-ma-sauvegarde.json
```

L'import exige une destination sans commandes et les mêmes réglages économiques. Un journal modifié est refusé et la restauration est annulée en entier. Pour reprendre ensuite cette partie restaurée :

```bash
python3 -m citygame --port 8092 --save data/restored.sqlite
```

Pour démarrer un essai indépendant, choisir un autre fichier sans supprimer le précédent :

```bash
python3 -m citygame --port 8092 --save data/second-essai.sqlite
```

Les actions économiques passent par le serveur et sont sérialisées ; un identifiant de commande déjà utilisé ne déclenche pas une seconde transaction. La reprise rejoue les commandes et compare les empreintes des comptes et stocks. L'accès public expose la carte, pas les comptes individuels. Ces protections concernent ce prototype local à un joueur ; elles ne constituent pas une administration multijoueur.

## Comparer les règles économiques

La [configuration V3](../config/v3.json) teste quatre changements : croissance progressive des commerces existants, tarifs coopératifs, délégation des commerces essentiels pendant une absence et circulation des excédents vers la mairie. Une réserve locale de matériaux permet les aménagements. Ces mécanismes restent internes au moteur et ne créent pas de tâches supplémentaires pour le joueur.

La V2 témoin conserve les règles économiques annuelles précédentes. Un test compare ses comptes et ses séries journalières au moteur historique. La V3 utilise les mêmes graines et la même monnaie initiale, avec un fonds extérieur fini. Les transferts, les investissements et les prélèvements ne créent pas d'argent ; les seules émissions sont celles déjà programmées pour les arrivants et les injections.

Le passage complet comprend 744 expériences :

- 714 passages annuels : quinze scénarios avec V2 et V3, plus quatre mécanismes isolés sur la référence, chacun sur 21 graines.
- 30 passages de 1080 jours : référence, arrivées et pénurie avec absences, chacun en V2 et V3 sur cinq graines.
- 40 exports détaillés, soit la graine initiale de chaque cas, avec journaux comptables compressés.

Les 6 946 560 contrôles horaires vérifient monnaie, stocks et absence d'ordres restés ouverts. Le vérificateur indépendant rejoue les écritures des exports, rapproche les soldes finaux, contrôle le tableau agrégé, les paires de graines et les empreintes des fichiers. Les manifests des deux expériences antérieures sont aussi vérifiés.

```bash
python3 -m citysim.welcoming --config config/v3.json --output results/v3-simulation --seeds 20 --long-seeds 4 --workers 4
```

Cette commande remplace les fichiers dans sa destination. Choisir un autre dossier de sortie pour préserver les résultats livrés.

```bash
python3 -m citysim.verify_v3 --results results/v3-simulation
```

Lire le [rapport comparatif](../results/v3-simulation/report.md), le [tableau complet](../results/v3-simulation/comparison.csv) et la [vérification indépendante](../results/v3-simulation/verification.json).

## Résultats et décision

La référence satisfait tous les critères sur 21 graines à un an et cinq graines à trois ans. La faible présence ne détériore pas les revenus. Pour l'accueil de nombreux arrivants, l'emploi payé moyen annuel passe de 64,7 % en V2 à 99,2 % en V3, avec 100 % des besoins alimentaires servis. Sept à huit commerces initiaux restent en activité. Les critères passent sur 19 graines sur 21 ; les deux échecs concernent un revenu des arrivants inférieur aux dépenses essentielles, malgré des réserves encore disponibles.

| Situation V3 | Critères satisfaits | Point restant |
| --- | ---: | --- |
| Référence, 360 jours | 21/21 | À éprouver avec des comportements humains. |
| Arrivées, 360 jours | 19/21 | Deux graines avec déficit courant des arrivants. |
| Pénurie, 360 jours | 15/21 | Six graines avec un épisode critique de 8 à 11 jours. |
| Pénurie et absences, 360 jours | 20/21 | Une graine avec réserves et couverture insuffisantes des arrivants. |
| Crises répétées, 360 jours | 0/21 | Épisodes critiques de 8 à 10 jours, malgré 99,26 % d'alimentation moyenne. |
| Arrivées, 1080 jours | 3/5 | Deux graines avec déficit courant ; une a aussi des réserves insuffisantes et trop d'inégalité. |
| Référence et pénurie avec absences, 1080 jours | 5/5 chacune | Résultat favorable dans le cadre du modèle. |

Le taux alimentaire moyen ne suffit donc pas : une série de mauvais jours peut rendre le jeu pénible malgré une bonne moyenne annuelle. De même, disposer d'économies peut masquer un budget courant déficitaire. L'équilibre est suffisant pour essayer cette boucle locale, mais ne valide pas encore l'accueil durable d'une ville persistante.

La graine détaillée des arrivées sur trois ans montre une cause précise à traiter : `vegetables_a` devient insolvable pendant 720 jours et ses neuf postes ne sont plus occupés. Le calcul des postes municipaux de la V3 compte encore ces postes privés nominaux ; il ne remplace donc pas les emplois devenus indisponibles. Les données finales montrent 89,3 % d'emploi payé, avec des réserves médianes des cohortes d'arrivants entre 0,27 et 0,95 jour. Cela explique une partie du problème ; il faut vérifier une correction sur toutes les graines avant d'en déduire qu'elle suffit.

Les prochaines corrections doivent porter sur les postes effectivement finançables et la reprise d'un commerce fragilisé, puis sur la réserve et la réponse alimentaire aux crises répétées. Comparer chaque correction séparément sur les graines qui échouent, puis rejouer la suite commune. Ces mécanismes doivent rester automatiques : ils ne nécessitent ni connexion quotidienne, ni nouvelle décision fiscale, ni gestion manuelle des courses par le joueur.

Les critères d'accueil distinguent le premier mois, qui doit dégager une marge médiane d'au moins 5 %, de la suite, où le revenu net après prélèvements doit couvrir les dépenses essentielles. Ils demandent aussi trois jours de réserve médiane, un premier salaire sous trois jours, un logement sous quatorze jours, 99 % d'accès alimentaire pour chaque nouvel habitant et au moins six commerces initiaux encore en activité. Ces seuils sont provisoires ; une médiane satisfaisante peut masquer un ménage en difficulté.

Les tarifs communs et les emplois municipaux simplifient le modèle. La marge de 2 %, les prélèvements sur excédents et les contrats extérieurs restent des hypothèses. Une année favorable ne suffit pas à conclure sur plusieurs années : il faut regarder les budgets des nouveaux, la distribution des réserves et les périodes de pénurie.

## Ce qui a été vérifié

43 tests couvrent le moteur historique, la V3 et la partie locale : invariants, mêmes résultats entre calcul par journée et calcul complet, salaire réel des arrivants, délégation sans revenu pour le propriétaire en sommeil, dépenses d'aménagement, doublons de commandes, reprise, restauration et accès aux données privées.

```bash
python3 -m unittest discover -s tests -v
```

Le script d'interface livré a aussi exécuté l'installation, une journée, le déplacement jusqu'au jardin, son paiement et la sauvegarde avec un DOM de test et le véritable gestionnaire HTTP Python. La reprise après trois jours fictifs hors connexion ne change ni la date ni le portefeuille.

```bash
node scripts/prototype_dom_qa.cjs
```

Le [compte rendu de parcours](../results/prototype/dom-qa.json) précise la méthode. La vérification couvre aussi projection inverse, zoom ancré, limites du zoom, vue entière, recentrage, clic sur les toits, glissement et pincement. Le [dessin de la carte](../results/prototype/map-preview.png) et le [détail rapproché](../results/prototype/map-closeup.png) sont rendus depuis les opérations du canvas exécutées par ce script. Ce sont des aperçus du décor ; ils ne prouvent pas la mise en page de l'interface.

Les ports TCP et Chromium sont bloqués dans l'environnement de réalisation. Il n'a donc pas été possible de vérifier la mise en page, le focus, les interactions tactiles ou l'affichage mobile dans un véritable navigateur. L'aperçu de carte n'est pas une capture d'écran de la page. Le script de vérification navigateur est préparé, mais dépend de Chromium et du paquet Playwright déjà présents dans l'environnement hôte ; il n'est pas requis pour jouer.

## Prochain essai avec des personnes

Faire essayer la tranche à cinq personnes pendant dix minutes, sans expliquer l'économie. Leur demander de s'installer, trouver le budget et réaliser ou ignorer un aménagement. Observer si elles comprennent ce qui se fait automatiquement, si elles trouvent une activité agréable et si elles craignent de perdre leur logement en s'absentant.

La cible proposée est que quatre personnes sur cinq terminent l'installation sans assistance et puissent expliquer simplement leur budget et les absences. Mesurer aussi les hésitations, les erreurs de navigation et le nombre de textes qu'elles doivent relire. Un objectif ignoré ne constitue pas un échec : la liberté de visiter fait partie du parcours.

Avant un essai partagé sur internet, vérifier la page dans un vrai navigateur, traiter les échecs économiques restants et ajouter comptes approuvés, contrôle d'accès multijoueur et administration minimale. Les élections, la crypto et les quartiers supplémentaires viennent après validation de cette boucle simple.
