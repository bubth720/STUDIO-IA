# STUDIO IA — M004 : livraison des développements, qualification neuronale BLOCKED

9 novembre 2026 UTC. **M004 n'est pas acceptée ; M005 ne peut pas être lancée.**
Le socle CPU fonctionne et les raccordements neuronaux sont développés et testés
au niveau des contrats. Aucun GPU compatible ou rendu neuronal réel n'est qualifié.

## Code et publication

- [PR #3 en brouillon](https://github.com/bubth720/STUDIO-IA/pull/3), vers `codex/studio-ia-consolidation-v1`.
- [Branche M004](https://github.com/bubth720/STUDIO-IA/tree/codex/studio-ia-m004-neural-local).
- `1956ba16c390443281b098146c2d5991c0230bf1` : registre multi-fichiers, schéma2, modèles sûrs, plans immuables et diagnostic Vulkan.
- `3a62bb17fe544c0e0aa637a703148235f428899b` : pipeline NCNN, CLI, tâches/Qt, aperçu/comparateur et tests de transport/pannes.
- `000a9801f16da9a855442eab7d864384570cf5c2` : CI de disponibilité matérielle séparée. **SHA exact des tests et des exécutables remis.**

Le commit final de documentation ajoute ce bilan et les preuves, sans changer
ces sources exécutées. Il n'a pas de qualification binaire distincte. Les 18 commits
du socle, main `61fe67ebb908da856964e88200e1220f83fc2bb8`, consolidation `24f5c21`,
branche documentaire `8db4916` et anciennes PR restent conservés. Aucune fusion,
installation personnelle, intervention sur un autre projet, pilote ou ressource payante.

## Ce qui fonctionne et ce qui reste non qualifié

| Domaine | Résultat actuel |
| --- | --- |
| CPU import/analyse/export/validation, audio, annulation, historique, comparaison | PASS, parcours réels Linux/Windows et exécutable extrait |
| Manifeste modèle2, hashes, snapshots, refus fichiers/archives/chargeurs dangereux | PASS logiciel ; la provenance déclarée ne suffit pas à une approbation juridique ou de sûreté |
| Plan2, replay CPU1, schémas futurs, restauration depuis JSON | PASS ; aucune migration SQLite ou réinterprétation des anciens filtres |
| CLI/Qt/gestionnaire reliés au backend, sélection par capacités | PASS contrats ; NCNN désactivé tant que l'essai réel n'a pas réussi |
| Transport 8s/deux pistes, PTS exacts, aperçu et comparaison, pannes | PASS avec un double **explicitement non neuronal** et vrais processus FFmpeg ; aucune qualification Real-ESRGAN déduite |
| Real-ESRGAN NCNN : inférence courte et vidéo entière | BLOCKED ; adaptateur IMPLEMENTED_UNVERIFIED sur GPU |
| Revue NN, métriques, stabilité perceptuelle/temporelle | BLOCKED / NOT_RUN, aucun avis humain inventé |
| Anime4K | ABSENT, aucun shader/variante exécuté ou qualifié |
| RIFE | NOT_STARTED : mission M005 fermée |

Les modèles et deux binaires officiels ont été inspectés, leurs hashes calculés,
et l'aide NCNN Linux exécutée. Le port NCNN est MIT, distinct du projet Python
Real-ESRGAN BSD-3-Clause. Les droits des poids inspectés n'ont pas été établis
séparément : aucun manifeste productif approuvé n'est fourni. Les archives de
modèles et les binaires tiers ne sont pas embarqués ou republiés avec l'application.

## Tests et builds effectivement reçus

[CI native finale 42644689519 SUCCESS](https://github.com/bubth720/STUDIO-IA/actions/runs/42644689519),
arbre propre à 000a980, workflow M003 inchangé :

| Plateforme | pytest | Parcours et distribution |
| --- | --- | --- |
| Ubuntu24.04 x64, glibc2.39, Python3.12.16, FFmpeg6.1.1 | **102 PASS / 1 SKIP / 0 FAIL** | E2E CPU, Qt X11, gel/extraction/relance PASS ; 609 hashes de contenu vérifiés |
| Windows Server2022 x64, Python3.12.10, FFmpeg7.1.1 | **100 PASS / 3 SKIP / 0 FAIL** | E2E CPU, Qt natif, gel/extraction/relance et installateur source Unicode PASS ; 381 hashes vérifiés |
| Laboratoire local Linux/glibc2.41, Python3.12.14, FFmpeg7.1.5, Qt offscreen | **102 PASS / 1 SKIP**, puis 8 tests UI ciblés PASS après derniers raccordements | ruff/format/mypy PASS ; écran physique et GPU non testés |

Le SKIP commun correspond à la qualification neuronale historique indisponible.
Windows conserve deux SKIP propres aux contrôles POSIX/Linux ; cela ne qualifie pas
ACL, FAT/exFAT ou partages réseau. Les 41 nouveaux tests ne sont jamais comptés
comme 41 preuves d'inférence : voir les noms/scopes dans [faults.json](faults.json).

La [baseline 42638932666](https://github.com/bubth720/STUDIO-IA/actions/runs/42638932666)
a également requalifié le socle inchangé : Linux61/1 et Windows59/3. Son commit
21b11b3 est un commit CI vide avec le même arbre que 24f5c21, car le message
documentaire original contient skip ci. Le premier lot 1956ba1 a passé une autre
CI native. Le push final annulé par la concurrence n'est pas présenté comme un
échec de tests ou additionné au run de PR retenu.

## Matériel et blocages exacts

Local : Xeon Platinum8370C/AVX2, chargeur Vulkan présent mais `vkCreateInstance=-9`
(`VK_ERROR_INCOMPATIBLE_DRIVER`), aucun périphérique /dev/dri. Linux distant : même
échec d'instance Vulkan ; Windows distant : vulkan-1.dll indisponible. Aucun pilote
installé, aucune limite VRAM inventée et aucune inférence tentée après ces refus.

[Readiness 42644668149](https://github.com/bubth720/STUDIO-IA/actions/runs/42644668149)
est vert pour **la collecte du diagnostic uniquement** : les deux rapports sont
BLOCKED avec zéro test neuronal PASS et `m005_allowed=false`. Le rapport local
[nn-e2e-001.json](nn-e2e-001.json) est produit au commit propre 000a980 et retourne
2/BLOCKED avant création d'une vidéo neuronale. Les diagnostics antérieurs de
working tree sont conservés comme tels, sans leur attribuer une qualification.

Les tests de panne couvrent mutations/binaire perdu, concurrence, disque insuffisant,
annulation d'un vrai processus enfant, exit137 injecté et destination concurrente.
Cet exit137 ne prouve pas un véritable OOM GPU. Annulation en pleine inférence
native, RAM/VRAM/latence neuronales, offline NN complet et vidéo longue restent
non exécutés. Les tests offline démontrent Python/transport FFmpeg local, pas un
réseau physiquement coupé pendant une inférence inexistante.

## Limites et éléments à requalifier

La voie NN initiale refuse VFR, origine vidéo non nulle, MKV, HDR/rotation, pixels
non carrés, flux secondaires et couleur autre que SDR BT.709 limitée déclarée.
Seul le modèle animevideov3 ×2 natif, débruitage désactivé/couleurs neutres, est
implémenté. La RAM/VRAM n'a pas de plafond OS universel garanti ; tuiles, frames
et stockage sont bornés, avec arrêt et absence de faux succès en cas d'erreur.
Les sous-processus ne sont pas une sandbox complète de sécurité.

Les images affichées sont des captures Qt/offscreen ou CI, pas une réception sur
écran physique. Aucun PSNR/SSIM/VMAF neuronal, gain perceptuel ou performance GPU
n'est annoncé. Voir [visual-review.md](visual-review.md) et [contrat plan2](../../docs/plan-v2.md).
Les ZIP sont toujours **0.3.0a2 ALPHA CPU avec raccordements M004 expérimentaux**,
pas une version neuronale qualifiée ou une release stable.

## Archives et reproduction

Les quatre artefacts CI ont été téléchargés et leurs SHA-256/CRC vérifiés, ainsi
que CRC des ZIP applicatifs internes et BUILD_INFO source propre 000a980.
[FINAL-VERIFICATION.json](evidence/FINAL-VERIFICATION.json) et
[ci-artifacts.json](evidence/ci-artifacts.json) donnent tailles, hashes, fichiers,
identités et liens réels. Les 22 fichiers de la livraison antérieure ont repassé
leurs SHA sans modification. Le bundle final et les archives récupérables sont
fournis séparément avec manifeste et contrôle de restauration.

SHA-256 des ZIP applicatifs **internes** : Linux
`e936958b5eb848b2e67ea60bacc19cc4094c2d6f082ad62ec7ab2f8e0869b1b0`,
Windows `24df7255ee1ac88bb5de40294b706697f00fbdf0b05cc09595f88b6d04ab1d24`.
Les fichiers récupérables sont des enveloppes Actions contenant ce ZIP et son
fichier .sha256 : leurs hashes externes sont différents et figurent au manifeste.
Les artefacts natifs expirent le 23 novembre ; readiness expire le 7 février2027.
Les copies récupérables ne sont pas une release publiée ni une garantie de
conservation permanente du workspace ; les télécharger pour conservation indépendante.

Depuis un clone propre dans un laboratoire autorisé : utiliser Python3.12,
installer les dépendances source existantes `[dev,gui]`, fournir FFmpeg/ffprobe,
puis `pytest -q -ra`, `python scripts/run_e2e.py --output artifacts/e2e`.
Linux sans écran : `QT_QPA_PLATFORM=offscreen` ou Xvfb ; définir STUDIO_IA_HOME
vers un dossier de laboratoire accessible. Les [commandes NCNN](../../docs/engines.md)
ne téléchargent rien. En GUI, le manifeste doit être placé à côté de la paire
param/bin, qui définit sa racine ; la CLI permet une racine explicite.

## Porte de passage

| Critère | État |
| --- | --- |
| AC-004-01 : vrai E2E neuronal sur machine compatible | **BLOCKED** |
| AC-004-02 : socle CPU et protection des médias | **PASS dans les environnements testés** |
| AC-004-03 : qualité NN évaluée honnêtement | **BLOCKED** |

**M005 : NO_GO.** Prochaine étape : un laboratoire existant et autorisé avec GPU
Vulkan réellement compatible et droits des poids établis, puis inférence courte,
NN01/NN02 complets, contrôle PTS/AV et revue visuelle/temporalité. Rejouer également
les pannes GPU et l'exécution hors réseau. Aucun achat, pilote, installation
personnelle ou saut de porte n'est engagé par cette recommandation.
