# Tests reproductibles et preuves

Installer `.[dev,gui,build]`, FFmpeg/ffprobe avec libx264/AAC. Les tests synthétiques
n'utilisent aucun média utilisateur. Windows : terminal avec environnement Python
activé ; Linux avec affichage : utiliser `xvfb-run -a` si aucun bureau n'est actif.

```sh
ruff check src tests scripts
ruff format --check src tests scripts
mypy src/studio_ia/core.py src/studio_ia/media.py src/studio_ia/pipeline.py src/studio_ia/jobs.py
pytest -q -ra --junitxml=artifacts/pytest.xml
python scripts/run_e2e.py --output artifacts/e2e
python scripts/gui_smoke.py --output artifacts/gui
python scripts/package.py
```

Sur un environnement limité sans X11, `QT_QPA_PLATFORM=offscreen` permet le rendu
réel Qt et les clics QTest ; cela ne représente pas un essai sur écran physique.
Les preuves enregistrent `qt_platform`. Chaque script média refuse d'écraser une
précédente preuve : choisir un nouveau dossier à chaque exécution.

F01 : 8 s 320×180 25 fps + sinus ; débruitage + 2× Lanczos + audio + vérification.
F02 : 5 s 640×360 muette ; F03 : noms accentués/espaces/ponctuation ; F04 : fichier
tronqué ; F05 : portrait 360×640 ; F06 : deux pistes audio et refus des sous-titres ;
F07 : VFR synthétique, nombre de frames et timestamps comparés ; F08 : tags BT.2020
et refus conservateur (ce n'est pas un corpus HDR perceptuel). F09–F10 et IA-01–03
ne sont pas qualifiés, faute de moteur/modèle/GPU validés.

Tests négatifs : outils/capacités absents, corruption, paramètres, conflit de
destination, fichier créé concurremment, source modifiée, disque plein injecté,
décodage final échoué injecté, annulation réelle, redémarrage et verrou d'instance.
Les injections sont des tests de gestion d'erreur ; les succès vidéo exécutent
toujours FFmpeg/ffprobe. Un test IA est SKIP explicite, jamais un faux PASS.

Le smoke Qt importe, valide, clique Démarrer, attend un vrai SUCCEEDED, compare
les images, capture le widget, mesure les événements UI, démarre et annule une
seconde tâche. Le packaging répète cela dans **l'exécutable gelé**, avec un autre
dossier courant, sans PYTHONPATH/venv et avec journaux/JSON.

Le workflow versionné lance lint/types/tests/E2E/build sur Ubuntu et Windows.
Artefacts conservés 14 jours : JSON, logs, clips synthétiques, captures, ZIP et
SHA-256. Un fichier workflow seul ne prouve pas une CI passée : consulter le
rapport final et les numéros/URLs des runs réellement exécutés.

Examen visuel : comparer à 0 s, 1 s et au milieu du clip ; observer petits détails,
contours, aplats, halos, saturation, scintillement et mouvement sur plusieurs
frames. Le synthétique prouve la validité technique, pas la restauration d'un
visage réel ou de détails perdus. Aucun gain perceptuel universel n'est annoncé.
