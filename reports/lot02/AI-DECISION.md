# AI-DECISION — Sélection des modèles (12 novembre 2026)

Sélection faite par délégation explicite du propriétaire, sous deux critères **non
négociables** : **100 % local** (aucun service cloud ni Internet après installation) et
**100 % gratuit** (aucun abonnement, crédit ou paiement). Critères ajoutés par la mission :
licence explicite, provenance traçable aux auteurs, réutilisation du moteur déjà intégré,
compatibilité matérielle la plus large possible.

## Choix du moteur : NCNN + Vulkan (conservé)

NCNN/Vulkan fonctionne hors ligne sur les GPU **NVIDIA, AMD et Intel** (y compris les GPU
intégrés récents), sous Windows et Linux, sans CUDA, sans PyTorch et sans Python côté
moteur. Les poids sont des paires `.param/.bin` qui ne sont pas des fichiers exécutables
(pas de pickle). C'est le moteur déjà intégré, épinglé et testé par contrats
(`src/studio_ia/neural.py`). Aucun coût, aucune dépendance réseau à l'exécution.

## Modèles retenus

| Rôle | Modèle | Licence code / poids | Format | État |
|---|---|---|---|---|
| **Animation** (V1) | `realesr-animevideov3` ×2 | MIT / **BSD-3-Clause** | NCNN officiel | Intégré ; manifeste vérifié par l'application ; inférence GPU à faire |
| **Prises de vue réelles** (V1) | `realesrgan-x4plus` ×4 | MIT / **BSD-3-Clause** | NCNN officiel, même archive | Sélectionné ; intégration au LOT 03 |
| Animation, alternative | Real-CUGAN (nihui) | MIT / **MIT** (bilibili) | NCNN officiel | Réserve, non installé |
| Interpolation (P2, hors V1) | RIFE (nihui) | MIT / **MIT** (hzwer) | NCNN officiel | Réserve P2 |

Hashes des fichiers : `engines.lock.json` (`selected_models_v1`) et
[PREPARATION.md](PREPARATION.md). Tous proviennent de l'archive officielle
`realesrgan-ncnn-vulkan-20220424-ubuntu.zip` (SHA-256 `e5aa6eb1…40c96`), retéléchargée et
recontrôlée le 12/11/2026.

Pourquoi `realesrgan-x4plus` pour la vidéo réelle : c'est le seul modèle généraliste
(photos et vidéos réelles) distribué en NCNN par l'auteur lui-même. Il est ×4 natif : pour
une sortie ×2, l'application devra réduire proprement en aval. Il est plus lourd que le
modèle anime ; le découpage en tuiles de NCNN borne la VRAM (à mesurer sur GPU).

## Décision sur la licence des poids Real-ESRGAN (blocage B2)

**Acceptée sous délégation du propriétaire.** Les poids sont publiés uniquement par le
titulaire des droits (Xintao Wang) dans les releases du dépôt `xinntao/Real-ESRGAN`, dont
le fichier `LICENSE` est **BSD-3-Clause** (texte relu le 12/11/2026). Aucun terme distinct ou
plus restrictif n'existe pour les poids. Risque résiduel : l'absence de clause explicite
propre aux poids. Mesure : conserver la notice BSD-3 (copyright + avertissement) dans toute
redistribution, et ne jamais embarquer les poids sans cette notice.

## Exclus, et pourquoi

| Candidat | Motif d'exclusion |
|---|---|
| CodeFormer (visages) | NTU S-Lab License 1.0 : **usage non commercial uniquement** |
| GFPGAN (visages) | Pile PyTorch lourde ; données FFHQ CC-BY-NC-SA, statut des poids incertain ; pas de NCNN officiel |
| `realesr-general-x4v3` | Excellent petit modèle BSD-3, mais **pas de NCNN officiel** ; à reconsidérer en V1.1 avec une conversion faite et tracée par le projet |
| Conversions NCNN tierces (OpenModelDB, etc.) | Licences au cas par cas, conversions non traçables jusqu'aux auteurs |
| Video2X | AGPL-3.0 et second moteur natif, inutile |
| Services en ligne / API payantes | Contraires aux deux critères |

Conséquence V1 : **aucun modèle spécialisé visages**. Le test T06 portera sur l'absence de
déformation par `realesrgan-x4plus`, pas sur une reconstruction faciale.

## Vérifications faites dans ce conteneur (sans GPU)

- `studio-ia model-check manifests/realesr-animevideov3-x2.json` sur les fichiers officiels :
  **`VERIFIED_LOCAL_FILES`** (manifeste SHA-256 `700d39e6…eaca4`).
- `studio-ia doctor neural` avec Vulkan logiciel (Mesa llvmpipe) installé : l'application voit
  le périphérique, le classe `physical_gpu: false` et reste **`BLOCKED / NO_PHYSICAL_VULKAN_GPU`**,
  `inference: NOT_RUN`. Le garde-fou contre un faux succès fonctionne
  ([preuve](evidence/doctor-neural-lavapipe.json)).
- Aucun binaire tiers exécuté, aucune protection modifiée.

## Ce qui reste pour G2 / G3

1. **GPU physique** : seule condition restante pour le modèle anime. Sur le PC cible :
   `studio-ia doctor neural --binary <realesrgan-ncnn-vulkan> --json diag.json`, puis
   `python scripts/qualify_neural.py --output campagne --run --binary <binaire> --manifest manifests/realesr-animevideov3-x2.json --models <dossier models>`.
2. **LOT 03** : étendre le contrat (`schemas/model-manifest-v2.json`, `models.py`, `neural.py`)
   à `realesrgan-x4plus` ×4, avec tests, puis qualification sur GPU.
