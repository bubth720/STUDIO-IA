# STUDIO CREATE — projet de démarrage Unreal (V0)

**Statut : NON EXÉCUTÉ.** Ce modèle et ses scripts n'ont encore été ouverts dans aucun
Unreal Engine : aucun PC compatible n'était disponible (voir `docs/create/ARCHITECTURE.md`).

- Cible : Unreal Engine 5.6 à 5.8, installé séparément par l'utilisateur (licence Epic).
- Aucun asset tiers : uniquement les formes de base du moteur (`/Engine/BasicShapes`).
- Le moteur n'est ni inclus ni redistribué.
- `Content/Python/studio_create_unreal/` : exécutants minces des commandes JSON produites
  par `studio-create` (toute la logique est testée en CI côté Python pur).

Créer une copie de travail : `studio-create new-project "<dossier neuf>"` (refuse un dossier
non vide), puis l'ouvrir dans Unreal.
