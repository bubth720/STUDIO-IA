# LOT 03 — Parcours IA de bout en bout (partie code, sans GPU)

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

## Ce qui n'est PAS prouvé

Aucune inférence Real-ESRGAN n'a eu lieu. La qualité visuelle de x4plus, la VRAM, la
vitesse et la réduction Lanczos sur de vraies images restent à mesurer sur GPU (LOT 03
Jour J, puis LOT 04).

## Suite du LOT 03 (sans GPU)

1. Élargir le contrat NN : conteneur **MKV** et **origine PTS non nulle** (T02/T03), déjà
   gérés par la voie CPU.
2. **Reprise** sûre d'une tâche interrompue (frames déjà inférées et vérifiées par hash).
3. Choix du modèle dans l'interface : « Animation » ou « Prises de vue réelles », lié au
   manifeste.
