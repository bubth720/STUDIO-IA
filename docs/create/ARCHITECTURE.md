# STUDIO CREATE — fondations (phase C)

13 novembre 2026. Branche dédiée `claude/create-foundations`, autorisée par le propriétaire
(mission maître LOT 03, phase C, option 2). **RESTORE n'est pas modifié** : le paquet
`studio_ia` n'importe pas `studio_create`.

> **Statut CREATE : PARTIAL — fondations livrées et testées sans Unreal ; aucun rendu
> Unreal réel.** Le POC (phase D) attend un PC compatible : Unreal Engine ne fonctionne
> ni sur le Poco X8 Pro, ni dans l'environnement cloud de développement, ni de façon
> réaliste dans la CI GitHub.

## 1. Architecture

```
studio-create (CLI)                       Unreal Engine 5.6–5.8 (installé par l'utilisateur)
  ├─ city.py      ville déterministe        unreal-template/  (projet de démarrage)
  ├─ cameras.py   caméras + séquence          └─ Content/Python/studio_create_unreal/
  ├─ contracts.py project / restore_job /         ├─ build_city.py  (NON EXÉCUTÉ)
  │               create_scene + actions          └─ render.py      (NON EXÉCUTÉ)
  ├─ bridge.py    détection, diagnostic,
  │               projet, fichiers de commande ──► Saved/StudioCreate/commands/*.json
  └─ assemble.py  PNG → MP4 vérifié       ◄── Saved/StudioCreate/renders/<séquence>/*.png
```

**Principe** : toute la logique (géométrie, collisions, caméras, images exactes,
contrats, diagnostic, assemblage vidéo) est en Python pur et testée en CI. Les scripts
côté Unreal sont des **exécutants minces** d'une liste d'actions plates
(`new_level`, `box`, `lamp`, `lighting`, `camera`, `sequence`, `save_level`). C'est la
seule partie non vérifiable sans Unreal, et elle est volontairement réduite au minimum.

**Communication** : fichiers de commande JSON validés, sans port réseau
(`network: NO_PORT_OPENED`), et `bRemoteExecution=False` dans le modèle.

## 2. Contrats (schema_version 1, validateurs dans `contracts.py`)

| Fichier | Contenu | Refus |
|---|---|---|
| `project.json` | id, mode `restore`/`create`, chemins **relatifs**, réglages, journal des exécutions | chemin absolu ou `..`, état inconnu |
| `restore_job.json` | source relative, profil `animation`/`live-action`, nom + SHA-256 du manifeste, paramètres, sorties, état `pending/running/failed/completed` | profil ou état inconnu, chemin hors projet |
| `create_scene.json` | level_id, générateur `city-v0`, seed, disposition complète + `layout_sha256`, zones, caméras, séquence, preset de rendu | empreinte modifiée, disposition non reproductible depuis la seed, caméra absente |

## 3. City Builder V0 (`city.py`)

- Plan en **grille** : `blocks_x × blocks_y` îlots, routes, trottoirs, lots par densité
  (`low` 2×2, `medium` 3×3, `high` 4×4), bâtiments `box`/`stepped`/`tower`, lampadaires,
  heure du jour (`dawn/day/dusk/night`).
- Unités : **cm**, axes Unreal (X avant, Y droite, Z haut), origine au centre de la ville.
- **Déterministe** : même seed + mêmes paramètres + `city-v0` donnent la même ville à l'octet
  près (`layout_sha256`). Les identifiants sont stables (`bld-bx-by-lx-ly`).
- **Contrôlé** : aucun bâtiment sur la chaussée ou le trottoir, aucune collision entre
  bâtiments, lampadaires hors chaussée. Vérifié sur 12 combinaisons seed × densité en CI.
- Régénération : les acteurs générés portent le tag `StudioCreate:generated`. Une
  régénération les remplace et **conserve les acteurs placés à la main**.
- Pas encore : plan radial ou manuel, relief, végétation PCG, météo, HLOD (missions futures).

## 4. Caméras et séquence (`cameras.py`)

Presets `travelling` (au-dessus de l'avenue), `orbit`, `wide`, `crane` ; focale, ouverture,
distance de mise au point. Séquence de 1 à 8 plans enchaînés par des coupes, cadences 24, 25,
30, 24000/1001 et 30000/1001. Les **bornes de plans sont des nombres d'images exacts** (refus
sinon) ; les images clés intérieures sont arrondies à l'image la plus proche.

## 5. Unreal Bridge (`bridge.py`, CLI `studio-create`)

| Commande | Comportement |
|---|---|
| `studio-create doctor` | Cherche les installations dans `STUDIO_CREATE_UNREAL_ROOTS`, puis `Program Files/Epic Games/UE_*` (Windows) ou `~/UE_*`, `~/UnrealEngine*`, `/opt` (Linux). Lit `Build.version`, vérifie les deux exécutables et les quatre plugins moteur. Statuts : `NOT_FOUND`, `INCOMPATIBLE`, `READY_FOR_MANUAL_TEST` (jamais « rendu validé ») |
| `studio-create new-project <dossier neuf>` | Copie le modèle dans un **dossier neuf** (refus si non vide), renomme le `.uproject`, écrit `project.json` ; copie atomique via un dossier temporaire |
| `studio-create scene <sortie.json>` | Ville + caméras + séquence (`--seed`, `--blocks-x`, `--camera NOM:PRESET`…) |
| `studio-create build-city <projet> <scène>` | Écrit le fichier de commande. Avec `--launch` seulement : lance `UnrealEditor-Cmd -run=pythonscript` et journalise |
| Rendu | `render_payload()` prépare le job Movie Render Queue (séquence PNG). `assemble.py` assemble en MP4 et vérifie images, cadence et durée avant publication |

Matrice de compatibilité (cible, **non testée**) :

| OS | Unreal | Python intégré | Plugins requis | Statut |
|---|---|---|---|---|
| Windows 11 | 5.6 / 5.7 / 5.8 | celui du moteur | PythonScriptPlugin, EditorScriptingUtilities, SequencerScripting, MovieRenderPipeline | NON TESTÉ |
| Linux | 5.6 / 5.7 / 5.8 (binaire Epic ou compilation) | celui du moteur | idem | NON TESTÉ |

## 6. Licences, coûts, matériel

- **Unreal Engine** : gratuit à l'usage ; **redevance de 5 %** seulement au-delà de
  **1 million de dollars** de revenus bruts cumulés par produit (contrat Epic en vigueur, à
  relire au moment de l'installation). Les règles de licence par poste ne concernent que les
  entreprises au-delà d'un seuil de revenus. Le moteur n'est **ni inclus ni redistribué** par
  ce kit.
- Le contrat Epic interdit de combiner le moteur avec du code sous licence **GPL/LGPL** : le kit
  n'en contient pas (STUDIO IA est sous MIT).
- **Aucun asset tiers** : seulement les formes de base du moteur et des matériaux générés.
- **Matériel** (recommandation officielle Epic) : Windows 11, 32 Go de RAM, GPU avec au moins
  8 Go de mémoire. CREATE est **plus exigeant que RESTORE** : pour un même PC, viser
  32 Go de RAM et 12 à 16 Go de mémoire graphique.

## 7. Démonstration CREATE en 10 minutes (à faire sur le PC, NON EXÉCUTÉE)

Prérequis : Unreal Engine 5.8 installé via Epic Games Launcher, STUDIO IA installé, PC
conforme au §6.

1. `studio-create doctor` → attendu `READY_FOR_MANUAL_TEST` (version 5.8 et 4 plugins trouvés).
2. `studio-create new-project "D:\Studio\Ville démo"` → projet créé, `project.json` présent.
3. `studio-create scene ville.json --seed 2048 --blocks-x 6 --blocks-y 1` → 2 caméras (travelling
   de 12 s au-dessus de l'avenue, orbite), 576 images à 24 i/s.
4. `studio-create build-city "D:\Studio\Ville démo" ville.json --launch` → niveau
   `/Game/Maps/City_2048` et séquence `/Game/Sequences/SEQ_Ville_City_2048`.
   **Premier point à vérifier** : journal `Saved/StudioCreate/build_city.log`.
5. Ouvrir le projet dans Unreal, contrôler la ville et les deux caméras dans Sequencer.
6. Lancer `render.py` depuis l'éditeur → images PNG dans `Saved/StudioCreate/renders/`.
7. Assembler en MP4 (`assemble.py`) → fichier lisible, 576 images, 24 i/s, 24 s.

Résultat attendu : **CREATE POC GO** seulement si les étapes 4 à 7 réussissent réellement,
avec journaux et vidéo conservés.

## 8. Blocages (liste fermée)

| ID | Blocage | Preuve | Responsable | Résolution |
|---|---|---|---|---|
| C-B1 | Pas de PC compatible Unreal | Poco X8 Pro (Android) ; conteneur cloud sans GPU | Propriétaire | Achat du PC (§6) |
| C-B2 | Scripts Unreal jamais exécutés | Aucun éditeur disponible ; appels API écrits d'après la documentation 5.x | Développement | Démonstration §7 sur le PC, corrections |
| C-B3 | Rendu sans éditeur ouvert non validé | L'exécuteur PIE demande l'éditeur ; le mode `-game` n'est pas testé | Développement | Mesure sur le PC |
| C-B4 | Pas d'intégration dans l'interface STUDIO IA | Choix volontaire : aucune régression RESTORE | Développement | Après POC GO, onglet CREATE |

## 9. Feuille de route

| Phase | Contenu | Gate | État |
|---|---|---|---|
| C — fondations | Ce document, contrats, ville V0, caméras, bridge, modèle, assemblage | Kit et diagnostic local en CI | **Livré (sans Unreal)** |
| D — POC | Ville + 2 caméras + 1 séquence **rendue dans Unreal** | Rendu Unreal réel vérifié | Attend le PC |
| E — extensions | Bibliothèque d'assets, PCG, personnages, montage, IA de scène | Missions séparées | Non commencé |

Sources : [tarifs Unreal Engine (Epic)](https://www.unrealengine.com/blog/we-are-updating-unreal-engine-twinmotion-and-realitycapture-pricing-in-late-april),
[configuration matérielle Epic](https://dev.epicgames.com/documentation/unreal-engine/hardware-and-software-specifications-for-unreal-engine),
[Unreal Engine 5.8](https://www.unrealengine.com/news/unreal-engine-5-8-is-now-available).
