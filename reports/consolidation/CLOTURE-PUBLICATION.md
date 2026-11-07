# STUDIO IA — clôture de consolidation et préparation M004

7 novembre 2026 UTC — **0.3.0a2 ALPHA CPU**. La consolidation est qualifiée sur
Linux et Windows x64 natif. Les permissions GitHub fonctionnent, les huit commits
M003 sont préservés et les nouveaux développements sont publiés sur la branche dédiée.
La PR reste en brouillon ; aucune fusion dans main, aucune installation personnelle.

## Publication et provenance

- [Branche de mission](https://github.com/bubth720/STUDIO-IA/tree/codex/studio-ia-consolidation-v1).
- [PR #1 en brouillon](https://github.com/bubth720/STUDIO-IA/pull/1).
- [CI native réussie](https://github.com/bubth720/STUDIO-IA/actions/runs/42420338324) : source exacte **4d42029f3bdbf260b72a6f2f0f81ed01be1265a9**, arbre propre.
- [Correctif X11](https://github.com/bubth720/STUDIO-IA/commit/c24062dd8289ce2c67d8c0747612ae1a2ec7e881),
  [correctif licences Ubuntu](https://github.com/bubth720/STUDIO-IA/commit/d56915712e9003f7c8df9ffab6e08431ef6be164),
  [correctif installateur Windows](https://github.com/bubth720/STUDIO-IA/commit/a57e389136958aa8a4990a1701b110ec51f995e7),
  [correctif affichage Windows](https://github.com/bubth720/STUDIO-IA/commit/4d42029f3bdbf260b72a6f2f0f81ed01be1265a9).
- Main conservée à **61fe67ebb908da856964e88200e1220f83fc2bb8**.

Le commit de clôture ultérieur ajoute uniquement documentation et preuves. Il
ne modifie ni src, ni scripts applicatifs/build, ni tests, ni workflow. La suite
n'est pas relancée pour ces seuls documents (`[skip ci]`). Chaque ZIP indique
son vrai commit de construction dans BUILD_INFO.json ; aucun build de ce dernier
commit documentaire n'est prétendu. Le manifeste externe donne le HEAD final,
les empreintes des livrables et la vérification de restauration du bundle.

## Résultats réels

| Environnement | Tests automatisés | E2E, GUI gelée et ZIP extrait |
|---|---|---|
| Ubuntu 24.04 x64 / glibc 2.39 / Qt xcb | **61 PASS, 1 SKIP, 0 FAIL**, 43.261 s | PASS, 607 fichiers vérifiés |
| Windows Server 2022 x64 / Qt windows | **59 PASS, 3 SKIP, 0 FAIL**, 65.413 s | PASS, 381 fichiers vérifiés |
| Debian 12 / glibc 2.36, hors réseau | 61 PASS, 1 SKIP, 0 FAIL | PASS, 578 fichiers vérifiés |
| Même ZIP Bookworm sur Debian 13 / glibc 2.41, X11 | parcours natif de l'exécutable extrait | PASS, export + annulation, 485 ticks GUI |

Linux ignore la qualification neuronale absente. Windows ignore aussi deux
contrôles propres à POSIX/Linux (permissions POSIX et renameat2), qui ne valident
pas des ACL Windows ou un disque FAT/exFAT. Les motifs complets restent dans
[les JUnit et JSON](ci/README.md). Les SKIP ne sont jamais comptés comme PASS.

L'E2E traite 8 secondes de vidéo synthétique avec audio : 320×180 vers 640×360,
débruitage hqdn3d et Lanczos, H.264/AAC ou audio copié. Le décodage intégral,
dimensions, durée, cadence, audio/synchronisation et intégrité source sont vérifiés.
Les clics QTest importent, valident, exportent, comparent, puis démarrent et annulent
une autre tâche ; aucune sortie annulée n'est publiée. Le ZIP est extrait puis
son propre exécutable est lancé hors du dossier source et sans PYTHONPATH/venv.
Sur le dernier ZIP, les timers restent actifs : 356 ticks Linux,
755 Windows. Les CRC, SHA-256 des archives et tous les fichiers de
leurs inventaires sont aussi vérifiés localement après téléchargement.

Les installateurs source fournis ont été réellement exécutés dans un nouveau
venv et un chemin avec espaces/caractères japonais, sur Linux puis Windows.
Le module installé Windows est tracé dans [installed-source-gui.json](ci/Windows/installed-source-gui.json) :
export, comparaison et annulation PASS, 726 ticks GUI.
Python 3.12 est nécessaire pour l'installation source, pas pour le ZIP portable.

## Anomalies corrigées pendant la reprise

1. Le premier run Linux s'arrêtait au démarrage de QApplication : dépendances Qt
   X11 explicites, préflight du vrai plugin et démarrage réel avant capture pytest.
2. Ubuntu affichait des annotations `diversion by libreadline8t64` avant le vrai
   propriétaire dpkg : extraction stricte du nom, poursuite des alias si seules
   des annotations sont présentes, six régressions et packaging réel réussis.
3. Pip échouait avec UnicodeEncodeError dans un chemin japonais sous Windows :
   Python UTF-8 activé pour venv, pip et le lanceur source. Le nouveau test natif
   reproduit tout le parcours d'installation, sans changer le codepage du système.
4. La CI utilise le commit exact de branche, plutôt qu'un commit de fusion virtuel
   de PR, et annule les exécutions push/PR concurrentes du même travail.
5. La capture Windows montrait des contrôles comprimés sur un écran peu haut :
   formulaire défilant et hauteur conservée, test à 1024×720, clics réels après
   défilement et nouvelles captures de l'exécutable. Le paquet Bookworm est aussi
   régénéré au même commit pour inclure ce correctif d'affichage.

Les [extraits d'échecs](ci/README.md) et runs précédents sont conservés :
[premier essai](https://github.com/bubth720/STUDIO-IA/actions/runs/42418371751),
[licences Ubuntu](https://github.com/bubth720/STUDIO-IA/actions/runs/42418862389),
[installation Windows](https://github.com/bubth720/STUDIO-IA/actions/runs/42419121669).
L'historique [BILAN-FINAL.md](BILAN-FINAL.md) décrit les corrections applicatives
déjà validées : absence d'écrasement, chemins figés, JSON UTF-8 atomique, publication
avant PASS, annulation/reprise, SQLite, aperçu/historique et environnement FFmpeg.

## Applications et installation

| Distribution | Taille | SHA-256 du ZIP |
|---|---:|---|
| Windows x64, source 4d42029 | 41,852,699 octets | `d171d9b1b7ebcca3e733231f2f7e9d85445f8b58e33033ce1bec20807215ad2f` |
| Ubuntu 24.04 x64 / glibc 2.39, source 4d42029 | 104,430,239 octets | `06f2db51dcdf772d6b18695912d8c24cc7e434316a9fcb6e9234efdbeac29dfe` |
| Linux Bookworm x64 / glibc 2.36, source 4d42029 | 86,327,157 octets | `16b4c3e3796c2a3edffa2477fdef790875078f246d848d2893f4614ceabbb494` |

Les builds Bookworm et CI utilisent le même commit 4d42029, arbre propre.
Les paquets et tests antérieurs restent conservés à leurs propres commits.
Le ZIP Bookworm offre un socle glibc plus ancien ; aucun ZIP Linux universel ou
essai Wayland n'est annoncé. Les notices système réelles accompagnent les paquets.

Sur Windows, vérifier le SHA-256 avec Get-FileHash, extraire tout le ZIP, conserver
_internal et licenses, fournir FFmpeg **et ffprobe 5.1+** dans ffmpeg/bin ou PATH,
puis lancer STUDIO-IA.exe ou Lancer-STUDIO-IA.cmd. Dans l'interface : importer,
choisir Préservation, une nouvelle destination, Vérifier le plan puis Démarrer.
Attendre la validation complète avant d'ouvrir l'export. Les lanceurs et
[INSTALLER.md](../../INSTALLER.md) détaillent aussi Linux et l'installation source.
FFmpeg n'est pas embarqué, téléchargé ou installé automatiquement par l'application.

## Sauvegardes et conservation

Les huit commits M003 sont ancêtres du HEAD publié, sans réécriture. Les dix
livrables initiaux et les seize entrées du manifeste de consolidation ont de
nouveau passé leurs SHA-256 après reprise. Les archives antérieures restent intactes.
La sauvegarde intégrale privée de 439 235 362 octets conserve Git, sources, tests,
venv, applications, preuves et PDF original :
`6d9db1f47b31af99116184fd63da6f8a693a01d636ddbf9e3ee71b8a1405d94a`.
Ses 12 021 fichiers ont été relus ; 228 fichiers suivis correspondent aux blobs
Git et les onze fichiers de livraison inclus sont identiques aux originaux.
Elle reste une archive locale privée ; elle n'est pas poussée sur GitHub.

La clôture dans `/workspace/library-files/cloture-20261107` ajoute les ZIP natifs,
sources + bundle complet, preuves CI et Bookworm, cahier M004, guide, manifeste
et SHA-256. Le bundle final est cloné dans un dossier neuf et vérifié par git fsck.
Le paquet de livraison complet et les liens récupérables figurent dans la réponse
de livraison. Les artefacts Actions expirent après 14 jours : récupérer les fichiers.
Un espace de travail cloud ne remplace pas une copie indépendante téléchargée.

## Fonctionnel et limites précises

Opérationnel : import/analyse ffprobe, plans et réglages CPU, débruitage, Lanczos,
couleurs légères, export MP4/MKV, pistes audio conservées ou AAC, validation complète,
progression, annulation, historique SQLite, relance depuis l'original, journaux,
diagnostic expurgé et comparateur d'images au même instant. Aucun faux succès simulé.

La restauration reste **classique sur CPU**. Real-ESRGAN, Anime4K et RIFE ne sont
pas exécutés ; aucun GPU ou modèle n'est qualifié. Le corpus est synthétique :
aucun gain perceptuel sur films endommagés, visages ou détails perdus n'est prouvé.
HDR/BT.2020, >8 bits, rotation, entrelacement, pixels non carrés, sous-titres,
données et multi-vidéo sont refusés explicitement. Le comparateur est fixe,
pas une lecture A/B continue. Pas de reprise au dernier frame après crash.
FAT/exFAT physiques, partages réseau, Windows 10/11 sur appareil physique et
macOS ne sont pas qualifiés. L'exécutable Windows n'a pas de signature de code
fournie. Aucun écran physique ou appareil personnel n'a été utilisé.
Le transfert d'une installation source par wheels reste non qualifié ; les
installateurs source sont éprouvés avec réseau et l'utilisation portable hors réseau.

## Mission 004 préparée, non développée

[Cahier technique Markdown](../../docs/mission-004/CAHIER-TECHNIQUE.md) et
[PDF de six pages](../../docs/mission-004/CAHIER-TECHNIQUE.pdf), sources officielles,
contrat futur de manifeste et critères NN-01 à NN-15 livrés. Le document décrit
Real-ESRGAN, variante précise Anime4K et RIFE, licences code/poids distinctes,
Vulkan/GPU/mémoire, OOM/annulation, audio/PTS/VFR/coupes, tests et jalons.
Aucun runtime ML, poids, entraînement ou développement neuronal lourd n'est lancé.
La mise en œuvre de M004 reste soumise à la décision du propriétaire.
