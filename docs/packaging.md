# Choix de distribution expérimentale

`pyside6-deploy --help` 6.8.3 a été réellement exécuté et confirme les modes
`onefile` et `standalone` via Nuitka. Le mode dossier autonome est retenu.
Cette mission utilise PyInstaller 6.13.0 comme autre empaqueteur éprouvé pour
limiter les étapes de compilation C et rendre l'essai reproductible sur les deux
runners. Aucun échec Nuitka imaginaire n'est rapporté : aucune compilation Nuitka
n'a été tentée. Le choix est explicite et les commandes sont versionnées.

`python scripts/package.py` construit un dossier, copie licences/instructions,
écrit version/SHA/dirty/plateforme, lance le binaire gelé pour doctor et le parcours
Qt vidéo + annulation, vérifie le JSON, inventorie les hashes puis archive.
Un échec de smoke interdit l'archive finale. `source_dirty=true` est une preuve de
travail intermédiaire ; le paquet final doit être régénéré après commit propre.

Pas de compilation croisée Windows depuis Linux. Le workflow Windows natif est
fourni ; sans run Windows réussi, aucun `.exe` Windows n'est annoncé testé.
FFmpeg/ffprobe et modèles sont externes, sans téléchargement automatique.
Le ZIP Linux dépend de la glibc du système de construction ; il est expérimental,
pas un AppImage universel. La distribution Qt reste dynamique et remplaçable.

L'inventaire PyInstaller révèle aussi QtSvg/QtWayland et ICU dans les plugins.
Leurs notices sont incluses. Sur Debian/Ubuntu, `collect_binary_licenses.py`
résout chaque bibliothèque système effectivement copiée, récupère son copyright
dpkg et sa version source, ajoute les textes communs et un lien aux sources
correspondantes dans `BINARY_LICENSES.json`. Cette collecte doit réussir avant
l'archivage. Le premier inventaire local compte 82 bibliothèques et 75 paquets.
