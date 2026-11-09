# STUDIO IA — Ordre combiné M004-clôture + M005-préparation

Édition : 9 novembre 2026. **Document exécutable pour Codex**, complémentaire du PDF intégral. Les contrats détaillés officiels restent sur la branche documentaire \`docs/roadmap-m004-m017-complete\`.

## 0. État initial à ne pas déformer

- M003 CPU \`0.3.0a2\` : import, traitement classique, audio et Qt qualifiés Windows/Linux en CI.
- M004 PR [#3](https://github.com/bubth720/STUDIO-IA/pull/3) : registre sûr, plans v2, pipeline NCNN, CLI/Qt, tests de transport **développés**, mais validation de Real-ESRGAN **BLOCKED** sur GPU. Aucun rendu neuronal réel vérifié.
- M004 CPU [#4](https://github.com/bubth720/STUDIO-IA/pull/4) : anti-banding classique qualifié en CI.
- M005 [#5](https://github.com/bubth720/STUDIO-IA/pull/5) : développement préparatoire M005.01 (analyse temporelle read-only rationnelle), **non RIFE**.
- Branche \`main\` intacte à \`61fe67e\`. PR #1/#2/#3/#4/#5 en brouillon, sans fusion.
- Codex doit rafraîchir HEAD, CI et versions au démarrage; les SHA dans les anciens rapports ne sont pas immuables.

## 1. Deux voies d’exécution

**Voie A – clôture M004** : si et seulement si une machine avec GPU Vulkan réellement compatible et autorisé existe, qualifier le vrai backend Real-ESRGAN NCNN, les licences du moteur ET des poids, l’inférence image, puis une vidéo entière avec audio, PTS, contrôle de qualité et pannes. Sinon rendre les résultats BLOCKED sans prétendre que les tests de doubles non neuronaux ont qualifié l’IA.

**Voie B – préparation M005 sans GPU** : faire progresser M005.01 (déjà commencée), M005.02 (coupes), garde anti-morphing déterministe, fixtures et tests de timebase/audio. **Ne pas activer le backend RIFE pour l'utilisateur** avant M004 PASS et qualification RIFE réelle. M005 reste en état PREPARATION.

Les deux voies ne se gênent pas : toute modification doit être isolée, testée et publiée en PR Draft.

## 2. Mission M004 restante — procédure bloquante

1. Lire \`reports/004/FINAL.md\`, \`reports/004/hardware.json\`, \`reports/004/nn-e2e-001.json\` et \`docs/engines.md\` sur \`codex/studio-ia-m004-neural-local\`.
2. Confirmer les capacités réelles du GPU et de Vulkan; \`vkCreateInstance=-9\` sur les anciennes machines n'est pas un PASS.
3. Verrouiller release/commit/binaires SHA et manifeste multi-fichiers du modèle; établir séparément droits d'utilisation/redistribution des poids.
4. NN01 : image réellement inférée avec \`Real-ESRGAN NCNN\`, décodeur de sortie, dimensions, hash, timings, logs et comparaison CPU.
5. NN02 : vidéo synthétique contrôlée 8 s SDR CFR BT.709, inférence de chaque frame, reconstitution PTS exacte, remappage audio, hash source inchangé, décodage intégral, no-clobber. Ajouter ensuite une source réelle légalement autorisée.
6. Vérifier sortie/cancellation/OOM/disque plein et fonctionnement hors ligne après installation autorisée, sans annonce de matériel non testé.
7. Revue visuelle authentique : contours/texte/visages/halos/scintillement; PSNR/SSIM seulement avec vraie référence alignée.
8. Une gate NN non exécutée = BLOCKED, pas PASS. Le socle CPU ne doit pas régresser.

## 3. Mission M005 — préparation déjà codée

- Lire \`src/studio_ia/temporal.py\`, \`tests/test_temporal_m005.py\`, \`docs/mission-005/TEMPORAL-PREFLIGHT.md\` sur cette branche.
- Conserver les timestamps sous forme d'entiers et \`Fraction\`; PTS non nul et VFR conservés à l'analyse. Refuser les PTS dupliqués, budgets déraisonnables, durées manquantes inventées et couverture incomplète déclarée PASS.
- M005.02 : détecter coupes franches/fondus/flashs, avec fixtures et faux positifs quantifiés; marquer toute paire traversant une coupe comme non interpolable.
- M005.04 : concevoir une politique d'intervalle neutralisé avec journal de décision; jamais d'image fusionnant deux scènes.
- M005.07 : contrôler pistes audio, offsets et timebase; ne jamais convertir VFR à 60fps par défaut.
- Ne commencer M005.03 RIFE réel qu'après M004 PASS; inspecter modèle et binaire \`rife-ncnn-vulkan\` sur machine autorisée, confirmer conventions N→2N/2N−1; 25→50fps sans changer la durée ni désynchroniser l'audio.

## 4. Vérifications minimales M005.01 (CPU uniquement)

\`\`\`bash
python -m pytest -q tests/test_temporal_m005.py
python -m ruff check src/studio_ia/temporal.py tests/test_temporal_m005.py
python -m ruff format --check src/studio_ia/temporal.py tests/test_temporal_m005.py
python -m studio_ia.temporal /chemin/vers/video.mp4 --max-frames 3000
\`\`\`

Puis rejouer **toute** la CI CPU + Qt + packaging Windows et Ubuntu. Aucun résultat simulé ne doit être ajouté aux tests neuronaux.

## 5. Gouvernance obligatoire

- Ne pas merger dans \`main\`, ne pas altérer PR #1–#5, ne pas supprimer les sauvegardes existantes.
- Pas de GPU cloud payant, de pilote, d'installation sur appareil personnel, de modèle tiers embarqué ou de téléchargement silencieux sans approbation.
- Pas de vidéos privées dans GitHub, logs personnels expurgés, SHA/source inchangée, aucun écrasement.
- Rapports distincts pour M004 et M005 : PASS / FAIL / SKIP / BLOCKED / IMPLEMENTED_UNVERIFIED par critère et SHA.
- Sauvegarder les artefacts CI importants hors des pages temporaires GitHub Actions.

## 6. Critères de passage

**M004 TERMINÉE** = Real-ESRGAN exécuté sur GPU réel + vidéo entière décodable/audio/PTS, évaluation honnête et sécurité de processus vérifiées. Sans cela, **M004 BLOCKED**.

**M005 TERMINÉE** = RIFE réel opt-in, coupes protégées, cadence/durée/AV vérifiés, régressions CPU inexistantes. Sans cela, **M005 PREPARATION/BLOCKED**.

**M006** ne peut commencer avant M005 acceptée.

## 7. Instructions aux agents

Exécuter réellement les lots réalisables dans le dépôt \`bubth720/STUDIO-IA\` ; ouvrir une branche distincte pour chaque sous-lot et une PR Draft ciblant la branche parent appropriée ; publier commits, tests et journaux ; conserver la pile de PRs. Ne pas simplement reformuler le cahier. En cas d'absence de GPU : livrer les composants préparatoires CPU et un rapport GPU BLOCKED.

**Documents complémentaires :**
- [M004 technique](https://github.com/bubth720/STUDIO-IA/blob/docs/roadmap-m004-m017-complete/docs/roadmap-v2/missions/M004.md)
- [M005 technique](https://github.com/bubth720/STUDIO-IA/blob/docs/roadmap-m004-m017-complete/docs/roadmap-v2/missions/M005.md)
- [Protocole général](https://github.com/bubth720/STUDIO-IA/blob/docs/roadmap-m004-m017-complete/docs/roadmap-v2/EXECUTION_PROTOCOL.md)
- [RIFE NCNN Vulkan](https://github.com/nihui/rife-ncnn-vulkan)
- [ffprobe officiel](https://ffmpeg.org/ffprobe.html)
