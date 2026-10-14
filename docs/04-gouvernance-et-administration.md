# Gouvernance et administration

## Répartition des responsabilités

La présence d'un maire aux pouvoirs limités est validée. La répartition précise ci-dessous est une proposition destinée à donner des moyens d'action tout en protégeant les habitants.

| Acteur | Décisions possibles | Limites proposées |
| --- | --- | --- |
| Visiteur | Observer la ville et consulter les informations publiques. | Aucune modification du monde. |
| Compte en attente | Visiter et suivre sa candidature. | Aucune installation avant approbation. |
| Habitant joueur | Gérer son personnage, ses activités et ses propriétés depuis le catalogue. | Règles communes de terrain, de capacité et de budget. |
| Maire | Proposer, coordonner, organiser et engager un budget délégué. | Plafonds, mandat, contrôle et décisions réservées au vote. |
| Habitants électeurs | Choisir les grands projets et contrôler certains changements. | Conditions de participation et délais connus. |
| Bingops | Approuver, administrer, modérer et corriger le fonctionnement. | Interventions tracées ; administration distincte de la compétition. |
| Simulation | Appliquer les règles, faire évoluer les PNJ et calculer les conséquences. | Paramètres versionnés et aucune dépense municipale implicite. |

Les règles doivent être contrôlées côté serveur. Le statut municipal ne donne pas les droits de l'administrateur.

## Ce que le maire pourrait décider seul

Le maire dispose d'une enveloppe de fonctionnement connue. Il peut financer de petits aménagements du catalogue, entretenir les équipements publics, organiser un événement et choisir l'ordre de projets déjà approuvés.

Le montant par décision, le cumul des dépenses et les engagements futurs sont limités. Fractionner un grand projet en petites dépenses ne doit pas contourner le vote.

Une intervention d'urgence, comme acheter temporairement des vivres pendant une pénurie, utilise une réserve plafonnée et produit un compte rendu.

## Ce qui demanderait un vote

Une extension de quartier, un grand équipement, un changement durable de fiscalité ou une modification importante d'un espace public passent par une proposition publique.

Chaque proposition décrit le besoin, le coût total, les dépenses futures, les alternatives et le calendrier. Le financement et les ressources nécessaires sont vérifiés avant l'ouverture du vote.

Le quorum, la durée des votes, les majorités et le traitement des abstentions restent à fixer. Une faible population demande une procédure simplifiée mais explicite. Les PNJ expriment leurs besoins ; ils ne servent pas à fabriquer une majorité électorale.

## Protection contre les abus

Les mandats ont une durée définie et les renouvellements consécutifs sont limités. Une procédure de révocation existe avec un seuil de soutien, une durée de vote et une période de stabilité à définir.

Le maire ne peut pas bannir un joueur, saisir arbitrairement un bien, créer de la monnaie ou transférer librement des fonds publics à un proche. Les contrats municipaux suivent des critères visibles. Un candidat concerné personnellement par une attribution doit être identifié comme tel.

Les changements de taxes sont bornés, annoncés et différés. Les règles en cours ne peuvent pas être modifiées pendant une opération pour avantager un participant.

En l'absence de maire ou de candidature, les services essentiels suivent un budget de continuité. L'administration peut assurer la transition sans distribuer de privilèges économiques personnels.

## Whitelist

Le parcours proposé utilise des états distincts : visiteur, candidature en attente, approuvé, refusé ou accès suspendu. L'approbation ne crée qu'une seule installation et reste correcte si la commande est reçue plusieurs fois.

Le panel affiche la présentation, la date de demande, le statut et les actions passées. Bingops peut approuver, refuser, suspendre et rétablir un accès avec une note interne.

La suspension coupe les nouvelles actions autorisées selon sa portée. Les ordres ouverts, les responsabilités municipales et les engagements économiques doivent recevoir un traitement explicite ; ils ne disparaissent pas silencieusement.

Les règles de comptes multiples sont à définir. La whitelist réduit l'accès non autorisé, mais ne suffit pas à empêcher plusieurs comptes de voter ou de réclamer des aides pour une même personne.

## Panel de bingops

| Espace | Fonctions attendues |
| --- | --- |
| Accès | Candidatures, whitelist, rôles, suspensions et historique. |
| Monde | Carte, propriétés, catalogue, chantiers et zones disponibles. |
| Personnages | État, besoins, routines, objectifs et raisons des décisions des PNJ. |
| Économie | Créations et retraits de monnaie, transferts, budgets, stocks, prix et concentration. |
| Municipalité | Mandats, propositions, votes, budgets et engagements futurs. |
| Événements | Programmation, conditions de déclenchement, intensité et conséquences. |
| Diagnostic | Alertes, transactions anormales, incidents et comparaison des paramètres. |
| Corrections | Ajustements motivés, réparations ciblées et consultation des sauvegardes. |

Une modification économique passe par une prévisualisation des personnes et des comptes concernés. L'historique distingue action de joueur, décision municipale, événement simulé et intervention administrative.

## Corrections et continuité

Les corrections financières utilisent de préférence des opérations compensatrices identifiables. Effacer une transaction ancienne pourrait invalider les achats réalisés ensuite par des tiers.

La restauration globale sert à un incident majeur et suit une procédure distincte. Les sauvegardes et la capacité de reprise doivent être validées avant une ouverture persistante.

Si bingops joue lui-même, ses actions administratives et ses actions de personnage doivent être identifiables séparément. Les informations et outils privilégiés ne doivent pas servir à obtenir un avantage sur le marché.
