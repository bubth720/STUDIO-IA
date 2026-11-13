# Fonctionnement local et confidentialité

Après préparation des dépendances, la CLI, Qt, l'historique et les traitements
s'exécutent localement. Pas de service réseau, compte, téléversement, télémétrie
ou vérification de licence distante. L'application ne télécharge ni FFmpeg ni
modèles. Le code ne crée aucun socket et FFmpeg n'accepte que `file,pipe`.

Preuve locale : E2E et tests Qt offscreen exécutés dans le sandbox de l'environnement
cloud avec namespace réseau isolé. Un test CPU interdit aussi les sockets Python
et configure des proxies inutilisables. Le smoke X11 utilise un serveur X virtuel
local sans TCP ; cette connexion d'affichage exige de sortir du sandbox.

L'installation/build/audit de vulnérabilités demande Internet. Pour un poste hors
ligne, utiliser le ZIP compatible et préparer FFmpeg/ffprobe séparément, ou préparer
les wheels du même OS avec `pip download -r requirements-runtime.lock`.

SQLite et les journaux restent dans STUDIO_IA_HOME ou le dossier de données de
l'utilisateur. Ils peuvent contenir des chemins privés et des métadonnées média.
Le bouton d'export diagnostic utilise une liste blanche de champs et supprime ces
données libres ; les noms de fichiers et hashes restent présents, à relire avant
partage. Aucun journal personnel n'est ajouté automatiquement à Git ou CI.
Seul du synthétique est distribué avec les preuves de cette mission.
