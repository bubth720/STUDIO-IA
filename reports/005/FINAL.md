# M005 — livraison CPU qualifiée, restauration neuronale BLOCKED

Édition du 10 novembre 2026. **M005 reste PREPARATION/BLOCKED. M006 : NO_GO.**
Le code CPU réalisable est développé, testé et publié. Aucun rendu Real-ESRGAN ou
RIFE n'a été produit ou présenté comme fonctionnel. Aucune fusion dans main,
aucune installation sur appareil personnel, aucun service payant engagé.

## Révision et preuves principales

Code fonctionnel livré : **7841ccd2767a6bb24e483e3c355be0a16ef138e1**.
La révision documentaire de clôture ajoute ce rapport et les preuves, sans changer
les modules, tests ou scripts des exécutables. Les binaires ALPHA gardent le numéro
historique 0.3.0a2 ; leur BUILD_INFO.json identifie exactement le commit 7841ccd et
`source_dirty=false`.

[CI consolidée Windows/Linux réussie](https://github.com/bubth720/STUDIO-IA/actions/runs/42798671790).
Les [jobs](evidence/ci-jobs-7841ccd.json), [artefacts et empreintes](evidence/ci-artifacts-7841ccd.json),
XML et reçus d'extraction sont conservés dans `reports/005/evidence/` et les archives.

| Vérification | Résultat | Révision et portée |
|---|---|---|
| Suite complète Linux CI, Qt X11 réel | **164 PASS, 1 SKIP**, 89,253 s | 7841ccd, 165 cas |
| Suite complète Windows CI, Qt natif | **162 PASS, 3 SKIP**, 159,995 s | 7841ccd, 165 cas |
| Suite complète locale, Qt offscreen | **164 PASS, 1 SKIP**, 474,22 s | 277c50b, avant dernier renforcement audio |
| Dernier renforcement audio + CLI local | **4 PASS**, 11,89 s | 7841ccd, puis suite complète en CI |
| CPU E2E historique et anti-banding | **PASS** | Rejoués dans les deux jobs CI |
| Build, lancement figé, ZIP extrait | **PASS Windows/Linux** | 382 fichiers Windows / 610 Linux vérifiés |
| Aperçu temporel et audit dans le binaire extrait | **PASS CPU** | Exécutables lancés hors sources/venv |
| Installeur source Windows en chemin Unicode | **PASS** | Runner Windows, aucun appareil personnel |
| Inférence Real-ESRGAN / RIFE | **BLOCKED / NOT_RUN** | Aucun GPU ni moteur neuronal qualifié |

Le SKIP commun concerne Video2X/modèles absents ; les deux SKIP Windows supplémentaires
concernent les permissions POSIX et le fallback Linux renameat2. Les tests de stockage
ou de transport NCNN avec fixtures synthétiques ne sont pas des inférences neuronales.

## Fonctionnalités réellement développées

| Lot | État livré | Fonction et limite |
|---|---|---|
| M5.01 | **PASS CPU** | FrameRecord immuable, PTS/timebase/durées rationnels, NTSC, origine non nulle, VFR inspectée, EOF borné vérifié ; durée finale inconnue jamais inventée |
| M5.02 | **PASS sur corpus contrôlé** | FFmpeg scdet, seuil réglable, candidats coupe/fondu/flash, limites ajoutées/exclues manuellement et journalisées |
| M5.03 | **PREPARATION ; RIFE BLOCKED** | Planning ×2 opt-in N→2N, ancres aux PTS d'origine, dernière tranche HOLD_LAST ; aucun backend RIFE activé |
| M5.04 | **PASS pour la garde du planning** | HOLD_SOURCE et journal d'intervalles à chaque transition détectée ; occlusions et morphing d'un vrai rendu RIFE non qualifiés |
| M5.05 | **PASS diagnostic CPU** | Translation SAD bornée, mesures après alignement, transitions exclues, cas ambigu inconnu ; aucune correction de flicker ni qualité neuronale prétendue |
| M5.06 | **PASS aperçu CPU** | Inspection Qt par PTS effectivement décodés, source/référence, loupe, saut aux transitions, un worker et une demande regroupée, six paires en cache |
| M5.07 | **PASS contrôles CPU AAC/PCM** | Pistes, langues, canaux, offsets, priming, cadence interne et données audio contrôlés ; aucune perte ni drift introduite dans les remux testés |
| M5.08 | **PASS contrôles CPU bornés** | 30 s/3 min, mesures réelles, annulation, CI, builds et extraction ; aucune qualification NN/HD/4K |
| Compléments M004 | **PASS CPU** | Registre verrouillé entre processus, libération après crash, conservation des registres invalides, plans mal typés refusés par StudioError |

Les outils sont intégrés à la CLI et à l'application empaquetée. L'interface propose
**Inspection temporelle** après import ; elle réutilise Comparison de la GUI existante.
Le moteur CPU, l'audio, l'historique et l'anti-banding de la PR #4 sont conservés.

## Expériences réelles et limites

Le corpus est synthétique et reproductible, sans vidéo privée ni poids tiers.
Une coupe à l'image 100 est détectée ; le planning neutralise sa paire adjacente.
Un flash à l'image 20 et son retour 21 sont protégés. Le split-screen stationnaire
ne produit aucune coupe ; le fondu est déclaré candidat graduel. Le panorama texturé
produit **un faux positif conservateur**, conservé dans [cuts.json](cuts.json).
Ces résultats ne garantissent pas la détection de toutes les transitions réelles.
Une coupe manquée exige correction du seuil ou limite manuelle.

Le fichier `NON_NEURAL_REPEAT_CONTROL.mp4` est réellement encodé et entièrement
décodé : 200 images deviennent 400 répétitions à 50 fps, durée exacte 8 s. Tous les
hashes du plan d'analyse répété correspondent aux images source. Ce témoin vérifie
le transport et les répétitions ; il ne satisfait pas la gate RIFE.

Les remux CFR et VFR 15/24/30 utilisent deux pistes synthétiques AAC/PCM étiquetées
fra/eng. Le PCM démarre exactement +200 ms ; le priming AAC est rapporté sans
arrondi artificiel. PTS vidéo, séquences de données audio et cadence relative restent
identiques, drift initial/final nulle dans le corpus. Le comparateur refuse aussi un
changement de disposition des canaux, de priming ou de cadence interne des paquets.
La qualification porte sur les pistes mono testées, pas sur tous les layouts multicanaux.
Voir [av-sync-report.json](av-sync-report.json).

Les métriques de mouvement retrouvent une translation contrôlée et un changement
de luminance connu. Un plan uniforme reste non observable, sans score zéro inventé.
Aucun masque dense d'occlusion, aucune preuve de ghosting ou de qualité perceptuelle
n'est fourni. La stabilité de super-résolution sur visages/mains/rotations rapides
reste **NON QUALIFIÉE**. Voir [temporal-metrics.json](temporal-metrics.json).

Le QTest effectue 31 requêtes rapides puis contrôle le cache LRU. À 6 s, la source
25 fps présente l'image 150 et la référence répétée 50 fps l'image 300. Les PTS réels
sont affichés, le timer Qt reste actif et les captures sont conservées. L'aperçu est
borné à 640×360 ; la loupe n'ajoute pas de détail natif. Les sources sans recouvrement
PTS sont refusées et aucun rééchantillonnage VFR→CFR/60fps n'est automatique.

Les mesures de 750 / 4 500 images concernent des vidéos **64×48**, sur les machines
répertoriées dans `evidence/*-7841ccd-resources.json`. Temps, CPU et pics RSS observés
sont conservés ; les pics Python et enfants sont séparés. Le pic mémoire des enfants
Windows et toute VRAM restent inconnus. Ces mesures ne prédisent pas le débit HD/4K
ou celui d'un modèle neuronal et ne démontrent pas une optimisation sans baseline.

## Blocages et critères d'acceptation

Le diagnostic matériel local relève Vulkan **vkCreateInstance=-9**, aucun périphérique
compatible et aucune inférence. Les licences et fichiers exacts de vrais poids
Real-ESRGAN/RIFE ne sont pas qualifiés. Aucun pilote, modèle ou GPU payant installé.

- **M004 NN reste BLOCKED** : NN01 image puis NN02 vidéo entière, droits des poids,
  audio/PTS, qualité et pannes sur matériel compatible restent à valider.
- **AC-005-01 BLOCKED** : RIFE n'a jamais été réellement exécuté.
- **AC-005-02 partiel CPU / BLOCKED RIFE** : durée, PTS et AV vérifiés sur contrôles CPU,
  pas sur un export RIFE.
- **AC-005-03 préparation vérifiée / BLOCKED RIFE** : demande explicite et segments
  neutralisés implémentés ; moteur opt-in réel non qualifié.
- **M006 ne peut pas être lancée.** Priorité suivante : qualifier M004 réellement sur
  GPU Vulkan autorisé avec moteur/poids/licences exacts, puis qualifier RIFE. Les
  autorisations de matériel, dépense ou installation personnelle ne sont pas présumées.

## Commits et pile de PR en brouillon

| Commit | Développement | PR |
|---|---|---|
| 02a8754 + e879b6e | Scènes, FrameRecord, garde et compatibilité Windows | [#6](https://github.com/bubth720/STUDIO-IA/pull/6) |
| 1b50d48 | Mouvement, audio, contrôles longs | [#7](https://github.com/bubth720/STUDIO-IA/pull/7) |
| 7d2f028 | Inspection temporelle Qt | [#8](https://github.com/bubth720/STUDIO-IA/pull/8) |
| 24e6c56 | Compléments M004 registre/plans | [#9](https://github.com/bubth720/STUDIO-IA/pull/9) |
| 277c50b + 7841ccd | Qualification binaire, extraction et renforcement audio | [#10](https://github.com/bubth720/STUDIO-IA/pull/10) |

Pile conservée : #5 → #6 → #7 → #8 → #9 → #10. Les PR #1–#5 sont intactes et en
brouillon ; main reste `61fe67ebb908da856964e88200e1220f83fc2bb8`.
Le premier échec Windows (encodage du test/fins de ligne) et sa correction ne sont
pas masqués ; les liens sont dans `evidence/ci-history.json`.

## Archives et reproduction

Les instructions utilisateur sont dans [INSTALLER.md](../../INSTALLER.md) et
[TEMPORAL-PREVIEW.md](../../docs/mission-005/TEMPORAL-PREVIEW.md).

```bash
python -m pytest -q -ra
python scripts/run_temporal_checks.py --output artifacts/temporal
python -m studio_ia.cli temporal-audit source.mkv --motion --audio --json nouveau-rapport.json
python -m studio_ia.cli interpolation-plan source.mp4 --x2 --cut 100
python -m studio_ia.cli temporal-preview source.mp4 --reference export.mp4
```

Dans l'exécutable extrait, remplacer `python -m studio_ia.cli` par
`STUDIO-IA.exe --cli` (Windows) ou `./STUDIO-IA --cli` (Linux). FFmpeg/ffprobe restent
externes ; aucun modèle neuronal n'est embarqué.

La livraison récupérable comprend sources, bundle Git autonome, patch des commits,
preuves CI brutes, fichiers synthétiques des tests et exécutable Windows 7841ccd.
La sauvegarde Linux utilise un différentiel Zstandard contre l'archive M004
préservée : sa reconstruction a été comparée **octet pour octet** au ZIP CI,
avec SHA-256 et CRC des deux couches ZIP. `Restaurer-Linux.py --verify-only` vérifie
la reconstruction sans créer le gros ZIP ; `--output nouveau.zip` le restitue sans
écraser un fichier. Python et une commande zstd existante sont nécessaires à cette
restauration ; rien n'est installé automatiquement. Le ZIP Linux complet reste aussi
récupérable dans les artefacts de la CI jusqu'au 24 novembre 2026.

Les 14 fichiers de la livraison M004 ont été rehashés PASS et conservés. Les
archives de la première qualification 277c50b sont également préservées. Les
SHA-256 et reçus sont dans le dossier de livraison, séparé des sources Git.

Une [release de sauvegarde en brouillon](https://github.com/bubth720/STUDIO-IA/releases/tag/untagged-7fd9eb6626ecde2a9f38)
a été créée ; **aucun asset n'y est téléversé** : `uploads.github.com` renvoie HTTP 401,
alors que l'API et les pushes Git fonctionnent. Elle n'est pas publiée. Ce blocage
n'affecte pas les archives récupérables ni les résultats CI ; les artefacts Actions
ont une rétention de 14 jours, d'où leur sauvegarde indépendante.
