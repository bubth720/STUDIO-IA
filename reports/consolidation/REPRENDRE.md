# Récupérer la version consolidée sans modifier main

La publication est effective sur `codex/studio-ia-consolidation-v1` et la
[PR #1](https://github.com/bubth720/STUDIO-IA/pull/1) reste en brouillon.
Les anciens 403 sont conservés comme preuves historiques, pas comme statut actuel.
Voir [CLOTURE-PUBLICATION.md](CLOTURE-PUBLICATION.md) pour les tests et distributions.

```sh
git clone --branch codex/studio-ia-consolidation-v1 https://github.com/bubth720/STUDIO-IA.git
cd STUDIO-IA
git status --short
git log --oneline --max-count=20
```

Sans GitHub, utiliser le bundle de la livraison de clôture :

```sh
git clone -b codex/studio-ia-consolidation-v1 STUDIO-IA-cloture.bundle STUDIO-IA-reprise
cd STUDIO-IA-reprise
git fsck --full
git remote set-url origin https://github.com/bubth720/STUDIO-IA.git
```

Vérifier les SHA-256 avec le manifeste livré avant extraction. Les archives de
consolidation antérieures restent des instantanés valides de leurs propres commits.
Le venv de la sauvegarde intégrale est lié à son système ; recréer l'environnement
pour une autre machine. Les applications portables incluent Python et Qt, mais
FFmpeg/ffprobe restent externes ; suivre INSTALLER.md et BUILD_INFO.json.

Ne pas forcer les pushes, réécrire les huit commits M003 ou fusionner dans main.
La préparation documentaire de M004 n'autorise pas son développement lourd.
Aucun accès personnel, secret ou jeton n'est nécessaire dans les fichiers livrés.
