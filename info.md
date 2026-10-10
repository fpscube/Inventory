# Inventory — spécification du projet

## Objectif

Créer une application web locale d’inventaire, accessible depuis un téléphone ou un ordinateur du réseau local.

L’application doit permettre de photographier les objets, de les décrire par texte ou dictée vocale, puis de les retrouver grâce à une recherche textuelle.

Le projet devra être installable comme une brique autonome et démarrer automatiquement avec `systemd` sur Ubuntu.

## Utilisateurs et accès

- Un seul utilisateur.
- Pas d’authentification pour l’interface dans la première version.
- Accès uniquement depuis le réseau local.
- Accès par adresse IP et port sur le réseau local ; un accès HTTPS séparé est prévu pour autoriser la dictée vocale.
- Port prévu : `18765`.
- Le service doit démarrer automatiquement au démarrage du PC, même avant l’ouverture de session.

## Cas d’usage 1 : ajouter un élément

Depuis un téléphone :

1. Ouvrir l’application web.
2. Prendre obligatoirement au moins une photo avec la caméra du téléphone.
3. Ajouter éventuellement jusqu’à 5 photos au total.
11. Dicter ou saisir la description de l’objet.
11. Dicter ou saisir la description de son emplacement.
11. Corriger les textes transcrits si nécessaire.
11. Vérifier les informations et confirmer l’enregistrement.

La sélection d’une photo existante dans la galerie n’est pas prévue dans la première version.

## Cas d’usage 2 : rechercher un élément

La recherche doit être disponible sur mobile et desktop.

Elle doit rechercher simultanément dans :

- la description de l’objet ;
- la description de l’emplacement.

La recherche est textuelle dans la première version. Une recherche plus avancée ou sémantique pourra être ajoutée plus tard, notamment pour un agent Codex.

## Gestion des éléments

Un élément doit pouvoir être :

- consulté ;
- modifié ;
- corrigé au niveau de sa description ;
- corrigé au niveau de son emplacement ;
- photographié à nouveau ou voir ses photos modifiées ;
- supprimé avec confirmation.

La suppression est définitive après confirmation. Il n’y a pas de corbeille.

## Photos

Les photos sont destinées uniquement à reconnaître les objets. Il n’est pas nécessaire de conserver une qualité photographique élevée.

Contraintes prévues :

- photo obligatoire pour créer un élément ;
- maximum 5 photos par élément ;
- redimensionnement automatique ;
- compression automatique ;
- cible d’environ 200 ko par photo ;
- conservation du ratio largeur/hauteur ;
- aucune déformation de l’image ;
- l’image originale haute résolution n’a pas besoin d’être conservée.

La compression doit utiliser une résolution et une qualité par défaut raisonnables. La cible de 200 ko est une cible pratique, et non une obligation de dégrader excessivement l’image.

## Dictée vocale

La première version utilisera la reconnaissance vocale disponible dans le navigateur du téléphone ou de l’ordinateur.

La dictée doit alimenter les champs de description, mais l’utilisateur doit pouvoir modifier le texte avant validation.

La saisie manuelle reste disponible comme solution de secours.

Il n’est pas prévu de stocker les fichiers audio.

## Stockage

Les données de l’application doivent être stockées dans le répertoire utilisateur :

```text
~/.inventory/
```

Le stockage devra contenir au minimum :

- la base de données de l’inventaire ;
- les photos compressées ;
- les exports ZIP ;
- la configuration locale ;
- les journaux utiles au diagnostic.

Les photos ne doivent pas être stockées directement dans la base de données. La base doit conserver leurs métadonnées et leurs chemins.

## Données d’un élément

Chaque élément devra au minimum contenir :

- un identifiant unique ;
- la description de l’objet ;
- la description de l’emplacement ;
- une ou plusieurs photos ;
- la date de création ;
- la date de dernière modification ;

Les catégories, tags et états métier ne sont pas prévus dans la première version.

## API

L’application doit être conçue autour d’une API séparée de l’interface web.

L’API devra permettre à terme de :

- rechercher des éléments ;
- lister les éléments ;
- consulter le détail d’un élément ;
- créer un élément ;
- modifier un élément ;
- modifier son emplacement ;
- ajouter ou remplacer une photo ;
- supprimer un élément ;

Cette API servira plus tard à un agent Codex capable de comprendre des demandes comme :

- « Où sont les câbles HDMI ? »
- « Quels objets sont dans le garage ? »
- « Ajoute cet objet à l’inventaire. »
- « Déplace la perceuse dans le garage. »
- « Supprime l’ancien chargeur. »

Les actions sensibles, en particulier la suppression, devront demander une confirmation explicite à l’agent.

Une clé API devra être prévue pour les accès futurs de Codex, même si l’interface web n’utilise pas d’authentification dans la première version.

## Architecture technique proposée

### Backend

- Python ;
- FastAPI ;
- serveur ASGI ;
- API REST documentée ;
- traitement serveur des images ;
- interface web responsive.

### Base de données

SQLite est suffisante pour un volume estimé entre 1 000 et 5 000 objets.

Les photos seront conservées dans le système de fichiers et référencées depuis la base de données.

Une migration vers PostgreSQL pourra être envisagée si le projet devient multi-utilisateur ou si le volume augmente fortement.

### Interface

L’interface doit être pensée d’abord pour le mobile, tout en restant confortable sur desktop.

Écrans principaux :

- écran de recherche et liste des éléments ;
- écran d’ajout ;
- écran de détail ;
- écran de modification ;
- écran d’import/export.

## Déploiement Ubuntu et systemd

Le projet devra être livré comme une brique autonome comprenant :

- l’application ;
- les dépendances ;
- une procédure d’installation ;
- un service `systemd` ;
- la création automatique de `~/.inventory/` ;
- le démarrage automatique du serveur ;
- la configuration du port `18765` ;
- les commandes de diagnostic et d’arrêt.

Le stockage dans `~/.inventory/` implique de privilégier un service `systemd` utilisateur. Le démarrage persistant de l’utilisateur (`linger`) sera activé pour démarrer avant l’ouverture de session.

Le script d’installation devra vérifier la version d’Ubuntu et signaler clairement les prérequis manquants.

## Import et export

La première version doit inclure un export ZIP complet contenant :

- la base de données ;
- toutes les photos ;
- les métadonnées nécessaires ;
- la version du format d’export.

Elle doit aussi permettre de réimporter une archive complète. La restauration remplace entièrement les données existantes ; elle ne fusionne pas les inventaires.

L’import devra demander confirmation avant de remplacer les données existantes.

Le format ZIP doit être documenté et conçu pour rester restaurable dans les versions futures.

## Sauvegardes

### Première étape

- export ZIP manuel ;
- restauration depuis un ZIP ;
- possibilité de copier l’archive vers un autre support.

### Deuxième étape

Prévoir une sauvegarde automatique vers Google Drive, avec :

- exécution périodique ;
- journal des sauvegardes ;
- gestion des erreurs réseau ;
- conservation de plusieurs versions ;
- restauration manuelle.

## Sécurité minimale

Même si l’application reste sur le réseau local :

- ne pas l’exposer directement à Internet ;
- limiter les fichiers envoyés aux formats image autorisés ;
- limiter la taille des uploads ;
- nettoyer les noms de fichiers ;
- ne jamais exécuter un fichier envoyé ;
- protéger l’API future avec une clé secrète ;
- protéger les opérations de suppression et d’import par confirmation.

## Découpage prévu

### Version 1

- application web responsive ;
- ajout avec photo obligatoire ;
- compression et redimensionnement ;
- dictée vocale du navigateur ;
- description de l’objet et de l’emplacement ;
- recherche textuelle ;
- consultation et modification ;
- suppression avec confirmation ;
- export/import ZIP ;
- installation Ubuntu avec `systemd` ;
- API de base.

### Version 2

- clé API complète pour Codex ;
- amélioration de la recherche ;
- intégration Google Drive ;
- agent Codex pour les requêtes et les modifications.

## Critères de validation de la première version

La première version sera considérée comme testable lorsque :

1. le service démarre automatiquement sur Ubuntu ;
2. l’application est accessible depuis un téléphone avec `http://IP_DU_PC:18765` ;
3. la dictée est accessible en HTTPS après installation du certificat local ;
4. une photo prise avec la caméra peut être associée à un objet ;
5. la photo est redimensionnée et compressée sans changer son ratio ;
6. les deux descriptions peuvent être dictées puis corrigées ;
7. l’objet peut être recherché par objet ou emplacement ;
8. l’objet peut être modifié ;
9. l’objet peut être supprimé après confirmation ;
10. un export ZIP complet peut être créé ;
11. un export ZIP peut être réimporté.
