# Plan de travail : Poco X8 aujourd'hui, PC demain

12 novembre 2026. Contexte : le propriétaire n'a pas encore de PC ni de carte graphique.
Il pilote le projet depuis un **Poco X8** (Android) et achètera un PC plus tard.
Règles inchangées : **100 % local, 100 % gratuit**, aucune dépense engagée par ce plan.

**Principe directeur** : la cible de la V1 reste le **PC de bureau (Windows prioritaire,
Linux maintenu)**. Le téléphone sert de **poste de pilotage**. Il peut aussi servir de
**petit laboratoire GPU facultatif**, mais il n'est **jamais une cible produit**
(Android est hors V1). Tout ce qui est développé maintenant doit fonctionner tel quel
le jour où le PC arrive.

## Phase A — Maintenant, depuis le Poco X8

### Comment on travaille

| Besoin | Outil (gratuit) | Ce que ça prouve |
|---|---|---|
| Écrire et modifier le code | Sessions Claude Code dans le cloud, pilotées depuis le téléphone | — |
| Tester Windows + Linux | CI GitHub Actions (gratuite pour un dépôt public) | Qualification CPU, interface Qt, paquets ZIP |
| Récupérer les applications | Artefacts CI téléchargeables depuis le téléphone (14 jours) | Archives vérifiées par SHA-256 |
| Garder une trace | `reports/` dans le dépôt + PR brouillon | Preuves traçables |

### Lots qu'on peut faire sans GPU (aucune perte de temps)

| Lot | Travail possible maintenant | Reste pour le PC |
|---|---|---|
| **LOT 03** — parcours IA | Intégrer `realesrgan-x4plus` (manifeste, contrat ×4 → sortie ×2), élargir MKV / PTS non nul (T02/T03), annulation et reprise, tests avec moteur simulé **étiqueté non neuronal** | Première vraie vidéo inférée (G3) |
| **LOT 04** — qualité | Outils de comparaison et de métriques, protocole de revue, liste du corpus autorisé | Comparaisons sur rendus réels |
| **LOT 05** — interface | Parcours importer → profil → estimation → comparer → exporter ; boutons IA grisés + diagnostic clair tant que le GPU n'est pas qualifié ; tests Qt en CI | Essai sur écran physique |
| **LOT 06** — paquet | Installateur Windows, guide utilisateur, `BUILD_INFO`, notices de licences (dont BSD-3 des poids), contrôle hors ligne | Installation propre sur le vrai PC (T16) |

Les étapes G3 à G6 restent **NO-GO** tant qu'aucun rendu n'a été produit sur un vrai GPU
de PC. Aucun test CI ne sera présenté comme une preuve d'IA.

### Laboratoire GPU facultatif sur le téléphone

Appareil du propriétaire : **Poco X8 Pro 5G**, puce MediaTek Dimensity 8500-Ultra, GPU
**Mali-G720 MC8**, 12 ou 16 Go de RAM LPDDR5X selon la version (fiche constructeur).
NCNN/Vulkan — **le même moteur que sur PC** — fonctionne sur Android.

- Option simple : l'application libre **RealSR-NCNN-Android** (licence MIT, tumuyan).
  Elle exécute en local les modèles Real-ESRGAN officiels, sans compte ni paiement.
  Usage : voir de ses propres yeux, sur **ses propres images**, ce que donnent
  `realesr-animevideov3` et `realesrgan-x4plus` avant d'acheter le PC.
- Ce que ça **prouve** : faisabilité visuelle des modèles choisis sur un vrai GPU.
- Ce que ça **ne prouve pas** : le fonctionnement de STUDIO IA sur PC, la VRAM du PC, la
  vitesse sur PC, ni l'étape G3.
- Installer une application sur le téléphone reste **le choix du propriétaire**. Ce plan
  ne l'exige pas.

## Phase B — Choisir le PC (quand le budget le permet)

Exigences tirées du moteur choisi (NCNN/Vulkan). Les seuils de mémoire graphique sont
**des estimations à confirmer** par les mesures du LOT 02/03 ; aucune n'a encore été mesurée.

| Élément | Minimum | Recommandé | Pourquoi |
|---|---|---|---|
| Système | Windows 11 64 bits | idem | Cible prioritaire de la V1, CI déjà qualifiée |
| Carte graphique | Toute carte NVIDIA, AMD ou Intel avec pilote **Vulkan 1.2** à jour (y compris GPU intégré récent, lent) | Carte **dédiée** avec **12 Go** de mémoire ou plus | `realesrgan-x4plus` est ×4 : plus de mémoire = tuiles plus grandes = plus rapide |
| Mémoire vive | 16 Go | 32 Go | Vidéo + images temporaires + interface |
| Stockage | SSD 512 Go | SSD NVMe 1 To ou plus | Les images intermédiaires d'une vidéo prennent beaucoup de place |
| Processeur | 6 cœurs | 8 cœurs ou plus | FFmpeg (décodage, encodage, audio) |

Conseils :
- Les trois marques de cartes conviennent grâce à Vulkan. **Ne pas** acheter pour CUDA :
  le projet n'en dépend pas.
- Privilégier la **mémoire de la carte graphique** plutôt que la puissance brute.
- Comparer les prix au moment de l'achat. Ce plan n'en fixe aucun.

## Phase C — Le jour où le PC arrive (« Jour J »)

Objectif : passer **G2 puis G3** en une session, sans rien redévelopper.

1. Mettre à jour le **pilote graphique** depuis le site du fabricant (gratuit).
2. Récupérer la dernière application **ALPHA Windows** produite par la CI, et vérifier son SHA-256.
3. Télécharger les deux archives officielles et vérifier leurs empreintes
   (`engines.lock.json`) :
   - moteur `realesrgan-ncnn-vulkan-v0.2.0-windows.zip` ;
   - modèles `realesrgan-ncnn-vulkan-20220424-windows.zip`.
4. Placer `manifests/realesr-animevideov3-x2.json` à côté des fichiers `.param/.bin`.
5. Lancer `studio-ia doctor neural --binary <moteur> --json diag.json`.
   Attendu : un GPU **physique** détecté.
6. Lancer `python scripts/qualify_neural.py --output jourJ --run --binary <moteur> --manifest <manifeste> --models <dossier>`.
   Résultat attendu : **première vidéo réellement restaurée par IA** (G3), avec journaux,
   empreintes, durée et mémoire.
7. Rapport `reports/lot03/JOUR-J.md`, puis LOT 04 (qualité) sur un corpus autorisé.

Rien dans le code ne dépend du téléphone. Le passage au PC ne demande donc aucune migration.

## Décisions en attente du propriétaire

1. ~~GO LOT 03 côté code~~ : accordé le 12/11/2026, voir `reports/lot03/REPORT.md`.
2. Facultatif : essayer RealSR-NCNN-Android sur le Poco X8 pour juger les modèles à l'œil.
3. ~~Préciser le modèle du Poco X8~~ : X8 Pro 5G (12/11/2026).
