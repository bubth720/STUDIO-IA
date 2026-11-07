# STUDIO IA / M003 / G5–G7 — livraison vérifiable

Date UTC : 2026-11-07. Responsable : Codex. Version : **0.3.0a1 ALPHA**.
Branche locale : `codex/studio-ia-m003-first-verifiable-build`.

Une application Linux réelle est livrée, avec sources, historique Git récupérable,
vidéos synthétiques, captures et rapports. **La mission n'est pas clôturée GREEN** :
la publication est refusée par les deux accès GitHub disponibles, donc la PR,
la CI distante et le build Windows n'ont pas pu être exécutés. Niveau formel du
dossier : **RED (absence de publication de code)** malgré le MVP local validé.

## Provenance et GitHub

- Dépôt réel : https://github.com/bubth720/STUDIO-IA
- Main : https://github.com/bubth720/STUDIO-IA/tree/main
- SHA main initial **et final relu par API** : `61fe67ebb908da856964e88200e1220f83fc2bb8`.
- CI réelle : https://github.com/bubth720/STUDIO-IA/actions — API : **0 run**.
- Branche distante de mission : **non créée** ; SHA distant de mission : **aucun**.
- PR brouillon : **non créée**, corps prêt dans `PULL_REQUEST.md`.
- Push Git : HTTP 403 « Permission to bubth720/STUDIO-IA.git denied ».
- Création de branche connecteur : HTTP 403 « Resource not accessible by integration ».
  Les droits du compte owner ne prouvent pas les scopes du jeton d'intégration.
- L'utilisateur a indiqué mettre à jour les droits ; les vérifications ultérieures
  restent refusées. Aucun secret demandé dans le chat, aucun contournement.
- Main n'a jamais été modifiée/fusionnée ; aucun force push, suppression de branche,
  release stable, déploiement public ou installation personnelle.

La connexion doit autoriser **Contents écriture** sur ce dépôt et **Workflows
écriture** pour publier le workflow. Le bundle évite de perdre le travail tant
que cet accès n'est pas disponible ; voir `HANDOFF.md` pour un prochain agent.

## Commits locaux conservés

| Commit | Livré |
|---|---|
| `95696ba2e27b4e13485063cba89dfea1aefde358` | audit, fondation Python/CLI |
| `35a780f4742a931536a61880e33fb10532468cc9` | premier pipeline vidéo et preuves CPU |
| `7e94421fd7594076fbc0a846cd1153d5986ae1ce` | interface Qt, tâches, persistance, annulation |
| `2e7a070e45d007be19c539a7fdb0e1f1e908b2a8` | robustesse médias, erreurs, correctifs d'audit |
| `44051e739a169cb27b84752ad1d670be85e85eff` | packaging, CI Linux/Windows, guides |
| `0f627a1a580249f2727a73ed7f2d0617a452f397` | inventaire licences des bibliothèques réelles |
| `843efdde4a6aeeb7f11fa94b440e2cb80c15c1ec` | notices nettoyées ; **source exacte du paquet final** |

Le commit de clôture ajoute ce rapport, les dernières preuves et l'outil de
vérification du ZIP. Son SHA exact figure dans `DELIVERY-MANIFEST.json`, livré
à côté du bundle et des archives. Les SHA ci-dessus sont **locaux**, pas des
liens de commits prétendument publiés. Tous descendent du main d'origine.

## Application livrée

Archive : `STUDIO-IA-0.3.0a1-linux-x86_64-ALPHA.zip`, **96 352 665 octets**.
SHA-256 : `36d66a6482844b8ae6016a12808420fd436f413b659f699d1315e26d5f42e0a8`.

Contenu : exécutable `STUDIO-IA`, runtime Python/Qt dans `_internal`, INSTALLER.md,
licences/mentions, BUILD_INFO.json, BUILD_SMOKE.json, BINARY_LICENSES.json et
FILES_SHA256.json. **FFmpeg/ffprobe externes**, aucun modèle inclus.

Construction sur Linux x64/glibc 2.41 ; il faut un environnement Linux compatible
et un affichage X11/Wayland. Ce n'est ni un exécutable Windows, ni une APK, ni un
paquet Linux universel. Aucun essai sur ordinateur/téléphone personnel.

Le binaire final a été lancé sur X11 virtuel (`xcb`) depuis un autre dossier,
sans PYTHONPATH/venv : import → plan → clic Démarrer → vraie vidéo 640×360 avec
audio → décodage complet → comparaison → seconde tâche annulée. **PASS**,
497 ticks GUI, aucun export annulé finalisé. `frozen=true`, code chargé depuis
`_internal/studio_ia/smoke.pyc`, source `843efdd`, `source_dirty=false`.

Puis **le ZIP lui-même** a été extrait dans `/workspace/studio-ia-archive-verified` :
SHA archive et CRC PASS, **538 empreintes de fichiers vérifiées**, aucun fichier
non inventorié. Le binaire extrait a répété le parcours complet en Qt offscreen
dans le sandbox **sans réseau** : PASS, 409 ticks GUI, annulation sûre. Ce test
vérifie le livrable distribué, pas seulement les imports Python.

Licences : 82 bibliothèques système copiées issues de 75 paquets sont rattachées
à leurs copyrights, versions et sources correspondantes. QtBase/QtSvg/QtWayland,
ICU, Python et bootloader ont leurs mentions distinctes. Pas de binaire FFmpeg
redistribué. Les empreintes et notices ne constituent pas une qualification de
sécurité native exhaustive de Qt/FFmpeg/OS.

## Résultats reproductibles

| Contrôle | Résultat |
|---|---|
| Suite complète Linux / pytest 9.0.3 | **41 PASS, 0 FAIL, 1 SKIP**, 72,91 s au dernier run identifié |
| Ruff lint + format (25 fichiers avant ajout de check_archive) | PASS ; dernier outil également linté/formaté |
| mypy core/media/pipeline/jobs | PASS |
| pip check | PASS, aucune dépendance cassée |
| Audit runtime PyPI | 0 avis connu pour PySide6-Essentials/Shiboken6 |
| Audit environnement après correctifs pip/pytest | 0 avis connu ; projet local non auditable sur PyPI |
| F01 E2E source, commit propre `44051e7` | PASS, toutes assertions interprétées |
| Qt source offscreen et X11 | PASS, vrais clics QTest et processus FFmpeg |
| Binaire gelé X11, commit propre `843efdd` | PASS |
| Archive extraite, binaire gelé sans réseau | PASS, 538 empreintes |
| CLI gelée analyze / process / verify | PASS, FFmpeg/ffprobe réels |
| GitHub Actions Linux/Windows | **NON EXÉCUTÉ**, publication refusée |
| Windows `.exe` | **NON CONSTRUIT / NON TESTÉ**, pas de runner Windows accessible |
| Restauration neuronale | **SKIP**, Video2X/modèles non qualifiés |

La suite complète a été exécutée au commit `44051e7`, arbre propre ; aucun code
applicatif ni test n'a changé entre ce commit et `843efdd` (comparaison Git vide
sur `src/studio_ia` et `tests`). Les changements intermédiaires concernent seulement
licences et packaging. Le packaging final a ensuite été réellement retesté.

Fixture principale : 8 s, 320×180, 25 fps, sinus 48 kHz ; hqdn3d léger → Lanczos
640×360 → H.264 CRF 18 → AAC conservé. Source SHA-256 :
`c5121233b22b532e5e940b3d312c14e87900325f64ac343bd99895a710f318d5`.
Sortie SHA-256 : `dfab7a182d6497169e1e0a154a10eefc5483d1c0a5f16fdece592cda30b3f3f6`.
Le test final vérifie dimensions, codec/pixel format, cadence, durée, nombre de
pistes audio, canaux/fréquence/codec, offset A/V à 100 ms, décodage complet et
hash source inchangé. Aucune exigence de hash identique entre versions d'encodeurs.

Le seul SKIP pytest Linux est le test de qualification neuronale : Video2X et
modèles absents. F09/F10 et IA-01/02/03 ne sont pas exécutés/qualifiés ; aucun gain
IA, score perceptuel ou GPU n'est revendiqué. Windows aurait en plus un SKIP du
test de permissions POSIX (il ne teste pas les ACL Windows), mais **aucun résultat
Windows n'est inventé**.

## Bilan fonctionnel

| Fonction | Statut |
|---|---|
| Import ffprobe, dimensions/cadences rationnelles/durée/audio/avertissements | **OPÉRATIONNEL**, corpus synthétique |
| Réencodage témoin, débruitage léger/modéré, Lanczos, couleurs légères | **OPÉRATIONNEL CPU**, pas d'IA |
| Export MP4/MKV, vidéo muette/portrait, plusieurs audios, PCM→AAC | **OPÉRATIONNEL**, tests réels |
| VFR | **OPÉRATIONNEL sur F07**, PTS et nombre de frames conservés ; progrès indéterminé |
| Original intact, refus d'écrasement y compris liens/concurrence | **OPÉRATIONNEL**, hashes et tests négatifs |
| Vérification complète avant finalisation | **OPÉRATIONNEL**, toute piste audio/vidéo décodée |
| Progression réelle, annulation active/file, timeout, UI réactive | **OPÉRATIONNEL** |
| Historique SQLite, relancement, interruption, journal | **OPÉRATIONNEL**, reprise depuis l'original |
| Comparateur coulissant | **OPÉRATIONNEL images fixes**, temps demandé commun ; pas de lecteur A/B continu |
| Diagnostic exportable masqué | **OPÉRATIONNEL**, champs autorisés seulement |
| AUTO | **OPÉRATIONNEL à règles simples**, proposition visible et confirmée, pas d'analyse neurale du bruit |
| Paquet Linux | **OPÉRATIONNEL EXPÉRIMENTAL sur environnement testé**, installation FFmpeg séparée |
| Workflow et packaging Windows | **CODÉS NON TESTÉS**, bloqués par publication |
| HDR/BT.2020, rotation, >8 bits, entrelacement, SAR non carré | **NON PRIS EN CHARGE**, refus avant export |
| Sous-titres/données/multi-vidéo | **NON PRIS EN CHARGE**, refus pour éviter toute perte silencieuse |
| Registre de modèles, découverte Video2X, contrat adaptateur | **PARTIEL / PRÉPARÉ**, intégrité locale testée, pas de run IA |
| Super-résolution/interpolation neuronale | **NON COMMENCÉE en exécution**, conditionnelle, pas de faux bouton |
| Métriques avancées, optimisation GPU, Android natif | **NON RÉALISÉS** |
| Création vidéo | **EXCLUE**, aucune fonction développée |

Limites supplémentaires : finalisation exige un système de fichiers à liens durs
(NTFS/ext4, pas FAT/exFAT) ; limite de 8,3 Mpixels ; après crash brutal des
temporaires privés peuvent subsister ; reprise par relancement complet ;
durées/timestamps inhabituels et métadonnées inconnues peuvent limiter les
assertions. Les preuves techniques synthétiques ne prouvent pas un gain visuel
sur toutes les vidéos réelles. Procédure visuelle documentée dans `docs/testing.md`.

## Portes d'acceptation

| AC | État | Preuve / manque |
|---|---|---|
| 01 branche distante | BLOCKED | HTTP 403, bundle local |
| 02 main préservée | PASS | SHA API initial/final identique |
| 03 diagnostic réel | PASS | doctor-report.json, versions exécutées |
| 04 import/ffprobe | PASS | F01 et CLI réelle |
| 05 débruitage réel | PASS | FFmpeg exécuté, sortie décodée |
| 06 upscale classique | PASS | 640×360 contrôlé |
| 07 audio | PASS | pistes et propriétés contrôlées/décodées |
| 08 original intact | PASS | hashes identiques |
| 09 GUI reliée | PASS | Qt native + offscreen, captures et JSON |
| 10 annulation sûre | PASS | processus réel, export absent |
| 11 CI E2E | BLOCKED | workflow versionné, aucun run distant |
| 12 distribution | PASS Linux / PARTIEL cible primaire | archive lancée et extraite ; Windows non construit |
| 13 rapport honnête | PASS | PASS/FAIL/SKIP et blocages explicités |

## Reproduction et corrections prioritaires

```sh
python -m pip install pip==26.3
python -m pip install -e ".[gui,dev,build]"
studio-ia doctor
QT_QPA_PLATFORM=offscreen pytest -q -ra
python scripts/run_e2e.py --output artifacts/nouvel-e2e
python scripts/package.py                         # affichage actif ou xvfb-run -a
QT_QPA_PLATFORM=offscreen python scripts/check_archive.py dist/ARCHIVE.zip --output DOSSIER_NEUF
```

Dans l'environnement cloud utilisé, `STUDIO_IA_HOME` et `XDG_CACHE_HOME` pointent
dans `/workspace` car le home du sandbox est en lecture seule. Les chemins par
défaut sont ceux de l'OS sur un poste utilisateur normal. Guides : INSTALLER.md,
docs/architecture.md, docs/testing.md, docs/offline.md, docs/engines.md et notices.

Priorité 1 : rétablir l'accès d'écriture et publier le bundle sans force push,
ouvrir la PR brouillon, laisser tourner les deux jobs CI et corriger tout échec.
Priorité 2 : qualifier le ZIP Windows sur runner puis, séparément et après accord,
sur poste utilisateur ; élargir le corpus (durées, formats, ACL, stockage).
Priorité 3 / Mission 004 : adapter Video2X réellement installé, modèles/licences/GPU,
corpus visuel et qualité temporelle, uniquement après fermeture des portes CI/build.

Les fichiers de livraison sont également copiés dans `/workspace/library-files` :
ZIP Linux et SHA, ZIP sources+bundle Git, ZIP preuves et vidéo MP4 de résultat.
`DELIVERY-MANIFEST.json` identifie les noms, tailles, empreintes et HEAD final.
Pas de liens vers des runs/commits/PR inexistants ni de publication prétendue.
