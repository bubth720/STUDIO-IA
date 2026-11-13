# LOT 03 — Parcours IA de bout en bout (partie code, sans GPU)

> Étapes 1 à 3 livrées sans GPU. Étape 4 (vraie restauration IA) : **NO-GO tant
> qu'aucun GPU physique n'est disponible** (voir `docs/PLAN-POCO-VERS-PC.md`).

12 novembre 2026. GO du propriétaire le même jour. **Statut : PARTIAL**.
Le modèle « prises de vue réelles » est intégré et testé par contrats. La première vraie
vidéo inférée (G3) attend un GPU physique de PC (voir `docs/PLAN-POCO-VERS-PC.md`).

## Étape 1 livrée : `realesrgan-x4plus` dans le moteur

| Fichier | Changement |
|---|---|
| `src/studio_ia/models.py` | Catalogue **fermé** `CATALOG` (nom → échelle native, noms exacts `.param/.bin`) à la place du modèle unique codé en dur ; `native_scale()` |
| `src/studio_ia/neural.py` | `-s` NCNN = échelle native ; essai court attendu en 32×native ; budget disque calculé sur les frames natives (×16 pixels pour ×4) ; contrôle de chaque frame à la taille native ; **réduction Lanczos ×4 → ×2** à l'assemblage, uniquement si native ≠ 2 ; politique `scaling` et avertissement inscrits dans le plan |
| `schemas/model-manifest-v2.json` | Accepte les deux modèles, avec échelle et fichiers liés au nom |
| `manifests/realesrgan-x4plus.json` | Manifeste revu (licences MIT / BSD-3-Clause / MIT, tailles et SHA-256 officiels) |

Inchangé : sortie V1 toujours ×2, MP4, CFR, SDR BT.709 ; binaire épinglé ; refus sans GPU
physique ; aucun repli CPU silencieux ; chemin `realesr-animevideov3` identique (aucun
filtre ajouté quand l'échelle native vaut 2).

## Preuves

- `studio-ia model-check` sur les **fichiers officiels** (archive v0.2.5.0, SHA-256
  `e5aa6eb1…40c96`) : les deux manifestes donnent **`VERIFIED_LOCAL_FILES`**
  (`700d39e6…eaca4` pour l'anime, `c71857c2…09b80` pour x4plus) et sont inscrits dans
  le même registre.
- 11 nouveaux tests `tests/test_neural_x4plus.py`, avec un **double FFmpeg explicitement non
  neuronal** :
  - acceptation de x4plus ;
  - refus des échelles 2/3/4.0/"4" ;
  - refus de noms mélangés ou inconnus ;
  - `-s 4` et `-n realesrgan-x4plus` passés au vrai constructeur de commande ;
  - plan avec `LANCZOS_TO_OUTPUT` et budget ×16 ;
  - transport 8 s, deux pistes audio : sortie 128×96 (×2 de 64×48), PTS exacts, source
    intacte, aucun temporaire ;
  - refus de frames qui ne sont pas ×4.
- Local (Python 3.13, en root) : ruff, format, mypy PASS ; suite complète **174 PASS /
  1 SKIP / 1 FAIL**. Le FAIL est `test_unwritable_destination`, artefact connu de
  l'exécution en root, PASS en utilisateur normal (voir LOT 01).
- CI Windows/Linux : celle de la PR #11 sur ce commit.

## Étape 2 livrée : MKV et origine PTS non nulle (T02/T03)

| Fichier | Changement |
|---|---|
| `src/studio_ia/plans_v2.py` | `frame_table` accepte une origine PTS **positive** et la consigne (`origin_pts`) ; origine négative et VFR toujours refusés |
| `src/studio_ia/neural.py` | Export **MP4 ou MKV** ; options MP4 (`video_track_timescale`, `faststart`) seulement en MP4 ; si l'origine est non nulle : `-copyts` et décalage exact des images inférées (`-itsoffset`, µs) ; chemin à origine nulle **inchangé** |

La vérification reste stricte : `compare_timing` exige l'**égalité exacte** de chaque PTS et
de chaque durée en secondes rationnelles, origine comprise. Un arrondi qui dériverait
serait refusé, jamais publié.

Tests `tests/test_neural_timing.py` (même double FFmpeg non neuronal) :

| Cas | Résultat |
|---|---|
| T03 : MP4 30000/1001, vidéo démarrant 15 images (≈0,5 s) après l'audio, 2 pistes AAC | PASS, PTS absolus identiques, synchro audio conservée |
| T03b : MP4 25 i/s avec décalage global de 1 s | PASS, PTS absolus identiques |
| T02 : MKV 25 i/s, deux pistes `fra`/`eng`, la seconde à +0,2 s, sortie MKV | PASS, langues et synchro conservées, 128×96 |
| MKV en 30000/1001 | **Refus explicite** : la base de temps 1/1000 du MKV ne peut pas représenter ces durées exactement (VFR apparent), pas de rééchantillonnage silencieux |
| Destination `.avi` | Refus |

Suite complète locale après l'étape 2 : **179 PASS / 1 SKIP / 1 FAIL** (le même artefact root).

Limite connue : une source **MKV** à cadence NTSC (29,97 / 23,976 i/s) est refusée en mode IA.
Elle reste traitable en mode CPU. Une remuxe préalable en MP4 ne suffit pas, car les
horodatages MKV sont déjà arrondis à la milliseconde.

## Étape 3 livrée : types de contenu « Animation » / « Vidéos réelles »

Autorisée par le propriétaire le 13/11/2026 (mission maître LOT 03, phase A).

| Fichier | Changement |
|---|---|
| `src/studio_ia/content_profiles.py` (nouveau, sans Qt) | Deux profils, **chacun lié à un seul modèle du catalogue** : Animation → `realesr-animevideov3`, Vidéos réelles → `realesrgan-x4plus` ; explication courte ; message de résolution concret (manifeste, fichiers, archive, GPU) ; préférence enregistrée de façon atomique dans `restore-settings.json`, avec retour aux valeurs par défaut si le fichier est corrompu |
| `src/studio_ia/neural.py` | `build_neural_plan(content_profile=…)` : profil déduit du modèle s'il est absent, **refus explicite** s'il ne correspond pas ; profil écrit dans le plan (`content_profile`), donc dans le job, `result.json` et le rapport ; un plan dont le profil a été altéré est refusé à l'exécution |
| `src/studio_ia/cli.py` | `neural-plan --profile animation\|live-action` |
| `src/studio_ia/ui.py` | Deux choix exclusifs « Contenu (IA) », explication, message de résolution en orange tant qu'aucun modèle n'est qualifié ; choix mémorisé à la réouverture ; modifiable avant lancement, verrouillé pendant un traitement ; un modèle déjà diagnostiqué qui ne correspond plus au profil est retiré et le moteur IA reste grisé |

Le libellé « Contenu (IA) » évite la confusion avec le « Profil » existant (préréglages CPU).
L'explication ne prétend rien de faux : les deux types utilisent réellement deux modèles
différents.

Tests `tests/test_content_profiles.py` (9) : liaison profil ↔ modèle, refus d'un profil
inconnu, message de résolution, persistance (chemin Unicode, fichier corrompu, valeur
inconnue), profil inscrit dans le plan puis dans `result.json`, refus d'un profil
incompatible, refus d'un plan altéré, test d'interface (exclusivité, mémorisation après
fermeture et réouverture, modification, moteur IA toujours grisé sans modèle qualifié).

Captures : [Vidéos réelles](evidence/lot03-profile-live-action.png),
[Animation](evidence/lot03-profile-animation.png). La CI les régénère à chaque exécution.
Un défaut de mise en page (texte coupé, barre de défilement horizontale d'un pixel) a
été vu sur les captures et corrigé avant livraison.

Suite complète locale : **188 PASS / 1 SKIP / 1 FAIL** (le même artefact root). Pas de
régression sur MKV, origine PTS non nulle, audio, chemins Unicode ni interface existante.

## Ce qui n'est PAS prouvé

Aucune inférence Real-ESRGAN n'a eu lieu. La qualité visuelle de x4plus, la VRAM, la
vitesse et la réduction Lanczos sur de vraies images restent à mesurer sur GPU (LOT 03
Jour J, puis LOT 04).

## Suite du LOT 03 (sans GPU)

1. ~~MKV et origine PTS non nulle (T02/T03)~~ : livré (étape 2).
2. **Reprise** sûre d'une tâche interrompue (frames déjà inférées et vérifiées par hash).
3. ~~Choix du modèle dans l'interface~~ : livré (étape 3).
