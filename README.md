# STUDIO-IA

Application locale de restauration vidéo — Mission 003, **ALPHA expérimentale**.

Travail sur `codex/studio-ia-m003-first-verifiable-build`, sans fusion dans `main`.
Le moteur CPU FFmpeg est prioritaire ; aucune restauration neuronale n'est encore
validée. Les preuves seront publiées dans `reports/003/` et les artefacts CI.

Installation depuis les sources (Python 3.12) :

```sh
python -m venv .venv
# Linux : source .venv/bin/activate
# Windows : .venv\Scripts\activate
python -m pip install -e '.[dev,gui]'
studio-ia --version
pytest
```

FFmpeg et ffprobe sont des dépendances locales externes. Aucun téléchargement
de média ou modèle, aucun compte ni service réseau à l'exécution.

Voir [l'audit](reports/003/00-audit.md) et [les tâches](reports/003/tasks.md).
