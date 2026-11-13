# STUDIO IA / M003 / G0 — audit, 2026-11-07 UTC

Responsable : Codex. Source : dossier Mission 003 joint (25 pages, lu intégralement).

- Dépôt autorisé : https://github.com/bubth720/STUDIO-IA
- Base `main` : `61fe67ebb908da856964e88200e1220f83fc2bb8`.
- API GitHub : droits pull/push ; une branche `main`, aucun PR, run Actions ou release.
- Clone Git effectué ; statut initial propre, un commit initial, seul actif :
  `README.md` (11 octets). Titre conservé et historique préservé.
- Aucun code Mission 001/002 dans les références disponibles ou `/workspace`.
- Protection de branche : lecture API refusée 403 par l'intégration, donc inconnue.
- Aucun secret dans le contenu initial. Aucun autre dépôt consulté/modifié.
- Environnement cloud Debian x64, Python 3.12.14, 3 CPU exposés, environ 7,5 Gio libres.
- FFmpeg/ffprobe système 7.1.5, compilation GPL avec libx264. Pas de redistribution
  de ce binaire. Qt absent avant installation dans le venv du projet.
- Réseau via proxy cloud ; clone dans le sandbox impossible, même clone autorisé
  hors sandbox réussi. Rien installé sur les appareils personnels.
- Branche créée : `codex/studio-ia-m003-first-verifiable-build`.
- Commandes : `git clone`, `git status --short`, `git log --all`, `git remote -v`,
  `ffmpeg -version`, `python --version`, API repo/branches/PR/runs/releases.

Premier commit : fondation, packaging, CLI version, test et tableau de tâches.
Le SHA distant sera consigné au jalon suivant après relecture distante.
G0 ne prétend à aucun traitement vidéo encore validé.

Politique : sources du projet MIT ; dépendances distinctes à inventorier.
CPU en premier, Qt puis CI et build ; Video2X seulement après preuve CPU.
`main` ne sera ni modifiée ni fusionnée.
