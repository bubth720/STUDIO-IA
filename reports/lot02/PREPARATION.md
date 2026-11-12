# LOT 02 — Préparation de la qualification du moteur neuronal

12 novembre 2026. **Statut : BLOCKED** (G2). Ce document consigne ce qui a pu être
vérifié sans GPU physique, sans dépense et sans décision du propriétaire.
Aucun binaire tiers n'a été exécuté, aucune protection du code n'a été modifiée.

> **Mise à jour du même jour** : sur délégation du propriétaire, la licence des poids
> (B2) est tranchée et les modèles sont sélectionnés. Voir [AI-DECISION.md](AI-DECISION.md).
> Seul le GPU physique (B1) bloque encore G2 pour le modèle anime intégré.

## 1. Provenance vérifiée (téléchargement HTTPS officiel GitHub, recalcul SHA-256)

| Fichier officiel | SHA-256 recalculé | Valeur épinglée dans le dépôt | Résultat |
|---|---|---|---|
| `Real-ESRGAN-ncnn-vulkan` v0.2.0 `realesrgan-ncnn-vulkan-v0.2.0-ubuntu.zip` | `d0e8e1cf…6e919` | `engines.lock.json` `release_zip_sha256_observed` | **IDENTIQUE** |
| binaire Linux `realesrgan-ncnn-vulkan` (dans le ZIP ci-dessus) | `22c2296a…cdbda9` | `TRUSTED_BINARIES` (`src/studio_ia/neural.py`) | **IDENTIQUE** |
| `Real-ESRGAN` v0.2.5.0 `realesrgan-ncnn-vulkan-20220424-ubuntu.zip` (modèles) | `e5aa6eb1…40c96` | `engines.lock.json` `models_archive_sha256_observed` | **IDENTIQUE** |
| `realesr-animevideov3-x2.bin` / `.param` | `548a36f9…ab2d` / `b88ff4f0…0a04` | `engines.lock.json` model_files | **IDENTIQUE** |

URL :
- https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases/download/v0.2.0/realesrgan-ncnn-vulkan-v0.2.0-ubuntu.zip
- https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip

Les fichiers téléchargés sont restés dans un dossier de travail jetable, hors du dépôt et
hors de toute distribution. Aucun digest ou signature éditeur n'existe : l'authenticité
repose sur l'URL officielle HTTPS et la stabilité des hashes depuis M004 (9/11/2026).

## 2. Modèles disponibles dans l'archive officielle (candidats pour B3)

| Modèle | Usage annoncé | `.bin` SHA-256 | `.param` SHA-256 |
|---|---|---|---|
| realesr-animevideov3-x2 (**intégré**) | Animation, vidéo | `548a36f9c3f4ab8da56cd3b13badf23968bee207b396dad14d04b830e5f2ab2d` | `b88ff4f00ebf019a7fdac17fdd45a7fd3665d37509efc5baf2e4da2e24420a04` |
| realesr-animevideov3-x3 | Animation | identique au x2 | `d1a5755008791d09b57e3425fc9dd0bd26b00fdf79c606210bc0e693f8230881` |
| realesr-animevideov3-x4 | Animation | identique au x2 | `850a248e7c14c27e5bd8cf7265113a9441036a7db63963bb8aa5169d788a435e` |
| **realesrgan-x4plus** | Images réelles, généraliste | `713ee713b0353afaa27976f0563a64a5043bd70b9bd8936c2e26e25ebcdbcddf` | `35330ececcea33b6c397a72548e788d5d53becee4734c50b7fada36e89f10a86` |
| realesrgan-x4plus-anime | Illustrations | `fe01c269cfd10cdef8e018ab66ebe750cf79c7af4d1f9c16c737e1295229bacc` | `2b8fb6e0ae4d2d85704ca08c119a2f5ea40add4f2ecd512eb7f4cd44b6127ed4` |

Observation : les trois variantes animevideov3 partagent **le même fichier de poids** ;
seul le graphe `.param` diffère. `realesrgan-x4plus` est le seul candidat généraliste
(prises de vue réelles, T05/T06) de l'archive ; il est ×4 natif, donc plus coûteux en
calcul et en mémoire que le ×2 intégré. Son intégration exige d'élargir le contrat
`neural.py` (aujourd'hui limité à animevideov3 ×2) : travail du LOT 03, après GO.

## 3. Licences

| Élément | Constat | Statut |
|---|---|---|
| Port NCNN (binaire) | Fichier `LICENSE` MIT, © 2021 Xintao Wang, dans le ZIP v0.2.0 | Établi |
| Projet Real-ESRGAN (code Python) | BSD-3-Clause (dépôt amont) | Établi, mais ne couvre pas explicitement les poids |
| Poids (`.bin/.param`) | **Aucun fichier ni mention de licence** dans l'archive v0.2.5.0 (README sans clause) | **NON ÉTABLI — décision du propriétaire (B2)** |

Le code refuse déjà à juste titre un manifeste sans licence des poids revue ; ce
comportement n'a pas été assoupli.

## 4. Essai d'inférence

- Ce conteneur n'a pas de GPU physique. Mesa lavapipe (Vulkan logiciel, `deviceType = CPU`)
  a pu être installé dans le conteneur jetable, et `vulkaninfo` le détecte.
- **L'exécution du binaire tiers a été refusée par la politique de permissions de la
  session (code externe).** Elle n'a pas été contournée. Aucune inférence n'a eu lieu.
- Même réussi, un essai lavapipe n'aurait **pas** satisfait G2/G3 (GPU physique exigé) ;
  il aurait seulement servi à valider le parcours de bout en bout.

## 5. Conditions de déblocage de G2

1. **B1 GPU** : machine avec GPU physique et pilote Vulkan, autorisée par le propriétaire
   (option A recommandée : son propre PC). Commande prévue, sans téléchargement :
   `python scripts/qualify_neural.py --output campagne --run --binary <binaire épinglé> --manifest <manifeste> --models <racine>`.
2. **B2 Licence des poids** : décision écrite du propriétaire, ou choix d'un autre modèle
   sous licence explicite.
3. **B3 Modèle généraliste** : valider `realesrgan-x4plus` (hashes ci-dessus) comme second
   modèle, puis l'intégrer au LOT 03.
4. Facultatif (laboratoire) : autoriser l'exécution du binaire épinglé sur Vulkan logiciel
   pour un essai de faisabilité, étiqueté NON-GPU.
