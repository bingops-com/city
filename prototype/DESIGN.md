# Prototype City : quartier des Tilleuls

## Direction révisée : village illustré en perspective

Vue oblique basse depuis la gauche : axes au sol (32, -5) et (12, 13), élévation verticale pour les façades et toitures. Les côtés gauches des bâtiments sont visibles. Le sol est davantage raccourci pour montrer plus les façades et moins les toits. La carte et ses collisions conservent leurs coordonnées ; une projection inversible gère les clics. Les décors sont dessinés en formes vectorielles fines, avec ombres, tuiles, volets, enseignes, plantations et mobilier. Aucun agrandissement de sprites à gros pixels.

Palette : prairie `#a9c38d`, feuillage `#527c5a`, pierre `#e0d6bf`, ardoise `#637f89`, tuiles `#b47d68`, encre `#29473f`. Police Candara, puis Trebuchet MS : titrage doux, contrôles courts, valeurs lisibles.

La ville occupe toute la largeur, avec un petit guide dans un coin et les contrôles de caméra à gauche. Une seule consigne, deux choix visuels, les détails du budget repliés. Repères sur les maisons et les activités, chemin pointillé et indication de destination. Zoom à la molette, aux boutons, au pincement ; glisser pour déplacer la caméra ; bouton pour retrouver son personnage. Sur téléphone le guide passe sous la carte.

```text
City       Les Tilleuls                             Jour / pièces
┌────────────────────────────────────────────────────────────────┐
│ [− +] [Vue entière]              Village en perspective         │
│ [Me retrouver]                   Maisons, arbres, commerces     │
│                                  Repères et chemin à suivre     │
│                                     ┌───────────────────────┐  │
│                                     │ Jeanne : une consigne │  │
│                                     │ deux choix / une action│ │
│                                     └───────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
Lieux      Lendemain / Pause                    Sauvegarde
```

Critique du plan : garder un carnet de statistiques à côté d'une petite carte reproduirait le premier prototype. La carte devient donc le cadre principal ; le budget détaillé se consulte à la demande. Les repères servent les étapes réelles du joueur, les décors et la perspective portent l'identité.

## Première direction conservée comme référence

Le joueur découvre une ville accueillante et choisit une vie simple. L'interface doit rester compréhensible sans connaître les règles économiques.

Palette : prairie `#8daa63`, étang `#568baf`, toiture `#97524a`, papier `#f9eed2`, encre `#263b36`, chemin `#dbcaa0`. La prairie et les bâtiments portent l'identité ; les panneaux restent calmes. Texte en Trebuchet MS avec alternatives sans empattement, titre City dessiné comme une enseigne. Pas de fonte ou de ressource distante.

La carte originale en pixels occupe environ deux tiers de l'écran. Un carnet latéral accompagne une étape à la fois : logement puis activité. Après l'installation, il montre un objectif facultatif et le bilan quotidien. Sur mobile, le carnet suit la carte. Texte aligné à gauche ; les montants seuls sont alignés pour faciliter la lecture.

```text
City     Le quartier des Tilleuls               Jour / portefeuille
┌────────────────────────────────────┐  ┌─────────────────────────┐
│ Ville, personnages, chemins        │  │ Jeanne et prochaine étape│
│ Carte jouable au clic et clavier   │  │ Une action principale    │
│                                    │  │ Objectif libre, puis bilan│
└────────────────────────────────────┘  └─────────────────────────┘
Lieux accessibles     Journée suivante     Pause     Sauvegarde
```

Deux choix obligatoires au départ : logement et activité. Aucun ordre de bourse, recette à mémoriser, taxe à régler manuellement, obligation alimentaire répétitive ou pénalité hors connexion. Les routines font travailler le personnage, achètent son panier et paient son loyer. Les objectifs d'aménagement sont facultatifs.

Une seule chose attire fortement l'œil : la ville animée. Les mouvements des personnages expriment leur routine ; les panneaux ne multiplient pas les animations. Contrôles accessibles au clavier, focus visible, mode de mouvement réduit, jeu au clic sur téléphone. Les informations privées restent dans le carnet du joueur ; la carte publique n'affiche pas les budgets des autres.

Critique avant construction : une page de cartes de statistiques évoquerait un outil de gestion. Ici, la carte constitue l'expérience principale. La couleur papier est réservée au carnet et aux petits contrôles, sans typographie de journal ni décor de tableau de bord.
