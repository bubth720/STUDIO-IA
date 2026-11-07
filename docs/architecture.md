# Architecture et politique du MVP

Qt appelle un gestionnaire Python local. Un worker de traitements, SQLite WAL
transactionnel, UUID par tâche ; une instance par historique (verrou OS). Pas de
serveur, socket, télémétrie ou appel de service distant à l'exécution.

`core.py` résout les binaires, vérifie les capacités, lance des listes d'arguments
et annule les processus. `media.py` analyse ffprobe JSON. `pipeline.py` valide les
requêtes, fige le plan, exécute les filtres, vérifie et finalise. `jobs.py` persiste
les tâches ; `ui.py` traite les signaux Qt ; `preview.py` extrait de vraies images.
La CLI et Qt utilisent le même planner/runner/verifier.

États : CREATED → VALIDATING → QUEUED → RUNNING → VERIFYING → SUCCEEDED.
FAILED et CANCEL_REQUESTED → CANCELLED sont des sorties contrôlées. Au redémarrage,
tout état non terminal devient INTERRUPTED. Le relancement repart de l'original.
Le temps d'encodage vient de `out_time_us`, jamais d'un minuteur fictif ; VFR ou
durée absente → barre indéterminée. Aucune estimation de temps restant inventée.

## Profil et ordre

Préservation AUTO : hqdn3d léger, résolution native, couleurs inchangées, CRF 18.
Il s'agit d'une règle proposée et visible, pas d'une détection neuronale du bruit.
Personnalisé : débruitage off/léger/modéré → correction eq bornée → scale Lanczos
(dimensions paires) → encodage H.264 → vérification complète. Témoin : aucun filtre.
Les dimensions paires peuvent ajuster le ratio de moins de 2 pixels par axe.
Pas de modification implicite vers 60 fps ou 4K. Maximum 8,3 Mpixels.

MP4 : copie AAC, sinon AAC 192 kbit/s pour chaque piste. MKV : audio copié.
Toutes les pistes audio sont mappées. Sous-titres/données, multi-vidéo, HDR/BT.2020,
rotation, entrelacement, >8 bits et SAR non carré sont refusés en amont. Les champs
rationnels de cadence et time base restent dans MediaInfo. `-fps_mode passthrough`.

Sortie temporaire dans un sous-dossier privé du dossier destination ; décodage
intégral vidéo **et toutes les pistes audio**, résolution, codec, pixel format,
couleurs connues, durée (tolérance max de 250 ms ou 2 frames), audio, hash source.
Finalisation par lien dur atomique sans remplacement ; nécessite un FS compatible.
L'annulation et la finalisation partagent un verrou pour décider une issue cohérente.
On demande d'abord `q`, puis SIGTERM/TerminateProcess, puis arrêt forcé du groupe.
Le journal est conservé ; les temporaires possédés sont nettoyés après un arrêt géré.

## Limites et sécurité

Les entrées sont non fiables. Protocoles FFmpeg limités à `file,pipe`, shell jamais
utilisé, paramètres bornés, chemins résolus, destination existante refusée (symlinks
et hardlinks inclus), contrôle d'espace, deux threads FFmpeg, délai de 24 h.
Un décodeur de média n'est pas une sandbox ; tenir FFmpeg/Qt à jour et limiter
la taille des fichiers selon la machine. Analyse ffprobe limitée à 30 s, aperçu
à 120 s ; sources énormes et certains médias inhabituels peuvent être refusés.

La comparaison extrait le premier frame décodable au temps demandé ; les lecteurs
et conteneurs peuvent quantifier aux PTS disponibles. Le curseur compare ces images
réelles, sans noter une qualité perceptuelle. PSNR/SSIM/VMAF non qualifiés.

Le registre local vérifie provenance/licence/version/SHA d'un fichier de modèle
sélectionné, sans l'exécuter. La découverte Video2X lit seulement version/aide.
Contrat d'adaptateur préparé ; aucun `run` neuronal disponible ni bouton IA fictif.
