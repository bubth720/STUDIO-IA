# STUDIO IA — consolidation V1 et préparation de la Mission 004

> Instantané historique établi avant le rétablissement des écritures GitHub.
> Les blocages de publication et de qualification Windows décrits ci-dessous ont
> été traités ensuite. Consulter le [bilan actuel](CLOTURE-PUBLICATION.md) et ses
> preuves pour le statut de livraison ; ce document conserve le constat initial.

Date : 7 novembre 2026 UTC. Version livrée : **0.3.0a2 ALPHA CPU**.
Statut : sauvegardes et qualification Linux terminées ; **publication GitHub et
qualification Windows bloquées**, malgré la reconnexion confirmée par l'utilisateur.
Aucun développement neuronal lourd, aucune fusion main, aucune installation personnelle.

## 1. Sauvegardes récupérables et vérifiées

Les huit commits M003 jusqu'à `61dc911ac105be2fb8b7259114a6516e125466c6` sont conservés
comme ancêtres de tous les nouveaux commits. Leur branche initiale n'a pas été
supprimée ni réécrite ; les archives initiales restent inchangées.

- Bundle initial : intégrité Git et autonomie vérifiées ; restauration déjà éprouvée.
- Dix fichiers référencés par l'ancien SHA256SUMS : tous conformes, à nouveau après consolidation.
- Tous les ZIP initiaux : CRC PASS.
- Sauvegarde intégrale : `STUDIO-IA-M003-sauvegarde-integrale.tar.gz`, **439 235 362 octets**.
- SHA-256 : `6d9db1f47b31af99116184fd63da6f8a693a01d636ddbf9e3ee71b8a1405d94a`.
- 12 021 fichiers ordinaires relus dans le flux gzip/tar ; CRC/intégrité PASS.
- 228 fichiers suivis comparés aux blobs Git du commit initial : tous identiques.
- 11 fichiers de la livraison initiale, dont SHA256SUMS, comparés à l'intérieur du tar : PASS.

L'archive intégrale inclut .git, venv, source/tests, builds, preuves et PDF original.
Elle est une sauvegarde locale complète, **pas un fichier à pousser sur GitHub**.
Le venv archivé est lié à son environnement ; pour une autre machine, recréer
l'environnement depuis les sources et dépendances plutôt que copier ce venv.
Les nouveaux bundle/sources/preuves et l'application consolidée sont livrés séparément
avec un manifeste et des empreintes, sans remplacer les archives M003.
Les fichiers téléchargeables doivent être récupérés pour une conservation indépendante
de cet espace de travail ; aucune sauvegarde distante GitHub n'est prétendue.

## 2. Publication et permissions GitHub

Dépôt réel : https://github.com/bubth720/STUDIO-IA .
Main initiale et finale relue par l'API : **61fe67ebb908da856964e88200e1220f83fc2bb8**.
Branche locale : **codex/studio-ia-consolidation-v1**.

Git push et création de branche via le connecteur renvoient tous deux **HTTP 403**,
« Resource not accessible by integration ». Le compte est propriétaire, mais cela
ne donne pas automatiquement les mêmes droits au jeton d'intégration.
L'en-tête serveur exige `contents=write`, et `workflows=write` pour les workflows.

L'installation identifiée est https://github.com/settings/installations/167943396 .
L'utilisateur a confirmé la mise à jour et la reconnexion ; de nouvelles tentatives
après cette confirmation et après reprise à 15:27 UTC restent refusées. La lecture
fonctionne, mais l'écriture effective n'est pas rétablie dans cette session.
Ces droits serveur ne peuvent pas être augmentés avec le jeton actuellement refusé.
Aucun secret n'a été demandé/affiché, aucun accès hérité n'a été contourné.

**Aucun nouveau commit distant, aucune branche distante de mission, aucune PR et
aucun run Actions** ne sont annoncés comme existants. L'API montre main seule et
0 run : https://github.com/bubth720/STUDIO-IA/actions . La publication reste à faire
dans une connexion Codex/GitHub disposant effectivement des droits ci-dessus.
Le bundle permet de la reprendre avec tous les commits, sans refaire le développement.

## 3. Corrections apportées à la version actuelle

| Anomalie ou limite | Consolidation et preuve |
|---|---|
| Symlink ajouté après validation pouvait rediriger la destination | Source/destination canoniques figées ; la dernière composante n'est plus résolue après validation ; test réel de refus |
| Rapport PASS écrit avant publication, même si conflit final | Journal VERIFIED_NOT_COMMITTED distinct ; result.json seulement après publication réussie |
| Nettoyage refusé transformait une vidéo valide en échec | Succès technique conservé, avertissement explicite et persistant ; temporaire possédé signalé |
| `--json` pouvait écraser source/rapport existant | Chemin séparé vérifié avant traitement, publication JSON sans remplacement, tests de préservation |
| JSON et consoles dépendants du codepage Windows | Fichiers UTF-8 atomiques, stdout JSON échappé ; caractères japonais/accents et stdout ASCII testés |
| Mauvaise configuration JSON pouvait lever une erreur interne | Schéma minimal objet/chemins vérifié et erreur utilisateur compréhensible |
| Chargement d'historique conservait un ancien plan | Plan invalidé avant et après chargement ; bouton Démarrer désactivé jusqu'à revalidation |
| Réglages modifiables pendant le job / image de résultat périmée | Contrôles verrouillés pendant le job ; aperçu de résultat invalidé au démarrage |
| Connexions SQLite et tokens terminaux | Fermeture explicite des connexions et purge synchronisée des tokens |
| Dépendance stricte aux liens durs | Renommage Windows sans remplacement ; repli Linux renameat2 sans remplacement, testé sur primitive réelle |
| Bibliothèques du paquet polluaient l'environnement FFmpeg externe | Chemins de bibliothèques PyInstaller restaurés pour les processus externes ; binaire Bookworm testé sur Debian 13 |
| Notices système introuvables entre /lib et /usr/lib | Recherche d'alias de propriété dpkg, éprouvée pendant le build Debian 12 |

Les trois premiers défauts ont été reproduits avec **3 FAIL avant correctif**,
puis corrigés. Les tests positifs appellent réellement FFmpeg/ffprobe. Les tests
de panne utilisent des injections explicitement identifiées, pas de faux succès vidéo.

## 4. Application et simplicité d'installation

Archive : **STUDIO-IA-0.3.0a2-linux-x86_64-ALPHA.zip**, **86 326 285 octets**.
SHA-256 : **addf036b46f11255f524d87c34ac79b42f372a3ef4d77d1618afb56dc374743c**.
Source exacte compilée : **f36fa05481c488558db258b2723cd3d51653e919**, arbre propre.
Les commits ultérieurs de clôture ne changent pas le code applicatif testé.

La construction de compatibilité utilise l'image officielle Python 3.12.14 Bookworm
fixée par digest. Le socle glibc passe de **2.41 à 2.36**. L'archive est plus petite
que la première livraison ; ce n'est toutefois pas un paquet Linux universel.
Tests effectifs : Debian 12/glibc 2.36 sans réseau, puis Debian 13/glibc 2.41 avec
X11 virtuel. Aucun écran physique ou ordinateur personnel n'a été testé.

Le ZIP inclut Python/Qt, les licences, l'inventaire, un guide de premier lancement
et les lanceurs. FFmpeg et ffprobe **5.1+ restent externes** : on peut les placer dans
`ffmpeg/bin/` à côté du programme, les garder dans PATH ou sélectionner FFmpeg dans
l'interface, qui détecte ffprobe à côté. Pas de téléchargement surprise au lancement.

Les scripts Installer-sources.sh / Lancer-sources.sh et leurs variantes PowerShell
créent/utilisent uniquement un venv local. L'installateur Linux a été exécuté dans
un dossier avec espaces et caractères japonais, puis l'application installée a
effectué un vrai parcours GUI d'export et d'annulation sans réseau. Les scripts
PowerShell sont préparés mais **non exécutés/qualifiés sous Windows**.

L'ancienne 0.3.0a1 est conservée comme historique récupérable ; privilégier la
0.3.0a2 consolidée pour les correctifs de sécurité des fichiers décrits ci-dessus.

## 5. Résultats exacts de qualification

| Vérification | Résultat |
|---|---|
| Suite Bookworm finale, source f36fa05 | **54 PASS, 0 FAIL, 1 SKIP**, 55 cas, 73,285 s |
| Lint Ruff / format | PASS, 31 fichiers |
| mypy core/media/pipeline/jobs/files | PASS, 5 modules |
| E2E synthétique CPU | PASS, toutes assertions interprétées |
| Packaging et exécutable gelé dans Bookworm sans réseau | PASS, source_dirty=false |
| ZIP extrait et réexécuté dans Bookworm | PASS, **578 empreintes**, CRC et inventaire complets |
| Même ZIP extrait sur Debian 13, Qt xcb | PASS, export + annulation, 530 ticks GUI |
| Installation Linux source dans un chemin Unicode | PASS, venv propre créé par le script fourni |
| GUI de cette installation, hors réseau | PASS, export + annulation, 493 ticks GUI |
| Original M003 et sauvegardes | PASS, hashes, CRC, blobs Git, bundle |
| Cahier M004 PDF | PASS, 6 pages, 13 sections et NN-15 relus dans le texte extrait |
| Contrat futur JSON Schema M004 | Syntaxe validée avec Draft202012Validator ; aucune inférence |
| GitHub CI / Windows natif | **NON EXÉCUTÉS**, publication refusée |
| Restauration neuronale | **SKIP**, aucun moteur/modèle qualifié ou téléchargé |

Le seul SKIP de la suite finale est la qualification neuronale absente. Les tests
Windows auraient des contrôles spécifiques/ignorés selon les primitives OS ; aucun
résultat Windows hypothétique n'est compté. Le passage des tests sous Linux n'est
pas une validation Windows.

Fixture : 8 s, 320×180, 25 fps, sinus audio ; débruitage léger, Lanczos vers 640×360,
H.264/AAC, décodage complet de la vidéo et des pistes audio, cadence/durée, canaux,
fréquence, offset A/V et hash original contrôlés. Le corpus comprend aussi vidéo
muette, portrait, multi-audio, VFR, chemins Unicode et erreurs réelles.
Les empreintes peuvent différer entre FFmpeg 5.1.9 Bookworm et 7.1.5 hôte ; on
compare les propriétés attendues, pas un hash d'encodage universel.

Historique des essais : une première exécution Docker a atteint la limite disque
du driver vfs avant création du conteneur. Le build a été réorganisé pour qualifier
dans une étape sans réseau puis exporter seulement archives/preuves. Un autre
essai a passé 54 tests mais échoué sur les notices libexpat ; l'alias dpkg a été
corrigé. Les logs d'échecs sont conservés ; seul le dernier build complet est livré.
Deux extractions redondantes de l'ancien ZIP ont été supprimées après comparaison
de tous leurs fichiers à l'inventaire ; le ZIP original et le tar intégral restent intacts.
Seuls des caches Docker identifiés de cette mission ont été nettoyés.

## 6. Windows et GitHub : travail préparé, limite restante

Le workflow versionné contient un runner natif **windows-2022 x64**, Python 3.12,
FFmpeg épinglé, lint/types, tests réels, E2E CPU, packaging et vérification du ZIP
extrait, avec artefacts et empreintes. Les écritures GitHub refusées empêchent
son démarrage. L'environnement fourni est Linux ; Docker Linux n'est pas un
runner Windows. Aucun .exe Windows compilé en croisé ou simulé n'est livré.

Après publication effective : lancer la CI, corriger les échecs natifs, télécharger
le ZIP Windows, vérifier son manifeste/SHA et son parcours réel. Une qualification
sur machine personnelle reste une opération distincte nécessitant l'autorisation
du propriétaire. Ne pas fusionner la PR ou créer de release stable automatiquement.

## 7. Mission 004 préparée, non lancée

Livrés : cahier Markdown et **PDF de six pages**, références officielles consultées,
matrice d'acceptation NN-01 à NN-15, corpus N01 à N08 et contrat futur de manifeste.
Le cahier décrit Real-ESRGAN, Anime4K et RIFE, les versions/poids/licences à figer,
Vulkan/GPU, mémoire/tuiles, annulation/OOM, audio/PTS/VFR/coupes de scène, aperçu et
comparaison temporelle, validation/packaging et jalons futurs.

Anime4K est qualifié par variante exacte CNN ou shader classique, pas par son nom.
Les licences de code consultées ne sont pas supposées couvrir automatiquement
tous les poids. Video2X 6.4.0 est une référence documentaire observée, pas un moteur
installé. Aucun runtime ML, modèle neuronal, téléchargement de poids, entraînement
ou traitement neural n'a été lancé. Les gates GitHub/Windows de consolidation
restent des préconditions à la mise en œuvre lourde de M004.

## 8. Limites et conservation

La restauration reste classique sur CPU. Les gains perceptuels universels,
restauration de visages, interpolation RIFE et super-résolution neuronale ne sont
pas revendiqués. HDR/BT.2020, >8 bits, rotation, entrelacement, pixels non carrés,
sous-titres/données/multi-vidéo restent refusés explicitement. Le comparateur
travaille sur images fixes au même temps demandé, pas sur une lecture A/B continue.

FAT/exFAT physiques et partages réseau restent non qualifiés malgré le nouveau
repli de finalisation. Après arrêt brutal, des temporaires privés peuvent subsister.
Un nettoyage/rapport refusé est désormais signalé sans transformer une vidéo
techniquement validée en faux échec ; un rapport absent ne doit pas être confondu
avec une exécution non vérifiée.

La qualification technique synthétique et les hashes ne constituent pas une
expertise de sécurité complète de Qt/FFmpeg/OS. Les versions runtime restent
épinglées et les notices/source correspondantes sont incluses ; aucun nouveau
scan exhaustif des vulnérabilités natives n'est prétendu.

Les livraisons sont dans `/workspace/library-files/consolidation-20261107` :
sauvegarde intégrale, ZIP Linux consolidé, sources + bundle, preuves, cahier M004,
vidéo/capture, rapport et manifeste SHA-256. Les anciens fichiers de livraison
restent disponibles à leur emplacement initial. Le manifeste final externe donne
le HEAD de clôture et l'empreinte de chaque fichier, sans hash autoréférentiel.
