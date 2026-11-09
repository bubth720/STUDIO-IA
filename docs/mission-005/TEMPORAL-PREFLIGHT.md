# STUDIO IA — M005.01 : diagnostic temporel exact (préparation indépendante)

**Statut :** développement préparatoire à la M005 ; RIFE et M004 neuronale non qualifiés.  
**Base :** PR #4 (anti-banding CPU + M004 NCNN en attente).  
**Branche :** \`feat/studio-ia-m005-temporal-preflight\`.  
**Domaine :** lecture seule, aucun changement d'image, de FPS, de PTS ou de son.

## Pourquoi ce module existe

Le pipeline M004 initial exige des timestamps CFR contigus à PTS zéro. La M005 devra au contraire traiter les cadences variables, des sources démarrant à un PTS non nul, les coupes et les pistes audio décalées. Il faut donc **mesurer fidèlement le temps d'abord**, sans normaliser involontairement le média.

Le nouveau module \`src/studio_ia/temporal.py\` n'est **ni un interpolateur ni une validation RIFE**. Il est isolé pour pouvoir être vérifié indépendamment du matériel GPU, sans ouvrir prématurément la porte M005.

## Contrat M005.01 (implémentation présente)

- Décode les \`best_effort_timestamp\` de ffprobe comme **entiers**.
- Conserve \`time_base\` en \`fractions.Fraction\`, sans calculer les PTS en \`float\`.
- Accepte les PTS négatifs, non nuls et les intervalles irréguliers.
- Rejette les PTS dupliqués ou non croissants, les durées non positives et le JSON invalide.
- Préserve un dernier intervalle **inconnu** lorsque FFprobe ne le fournit pas.
- L'examen reste **borné** : 1 à 10 000 frames, par défaut 3 000.
- Une analyse dont la totalité des frames n'est pas démontrée retourne **PARTIAL_PREFIX**, pas PASS.
- Un changement de pas PTS n'est pas un diagnostic VFR certain : l'arrondi à la timebase d'un CFR rationnel peut alterner les pas.
- Traite uniquement un **fichier local** avec la liste de protocoles \`file,pipe\`; pas de flux réseau.
- N'écrit aucun média et ne reconstitue aucun timestamp.

**Commande de diagnostic :**

\`\`\`bash
python -m studio_ia.temporal /chemin/vers/video.mp4 --max-frames 3000
\`\`\`

Sortie JSON : \`status\`, base rationnelle, nombre de frames, premier/dernier PTS, durée lorsque connue, indicateur de pas non uniformes, limites explicites.

## Stratégie de validation

Tests unitaires : CFR 25fps, origine à +250 et -80 ticks, cadences irrégulières, durée finale inconnue, lecture préfixe, PTS répétés/inversés, champs malformés, limites et incohérence du total de frames.

Test d'intégration \`test_real_ffprobe_timeline_is_read_only\` : utilise la fixture vidéo du projet ; exécute réellement ffprobe, contrôle la progression des PTS et compare le hash source avant/après.

Validation à reproduire :

\`\`\`bash
python -m pytest -q tests/test_temporal_m005.py
python -m ruff check src/studio_ia/temporal.py tests/test_temporal_m005.py
python -m ruff format --check src/studio_ia/temporal.py tests/test_temporal_m005.py
\`\`\`

Puis rejouer les jobs Windows et Ubuntu du workflow \`verify.yml\`, comprenant la régression CPU/Qt et les exports vidéo.

## Prochaines tâches **non réalisées** dans ce lot

- M005.02 : segmentation des plans et garde anti-morphing.
- M005.03 : intégration de RIFE opt-in ×2 **sur GPU qualifié uniquement**.
- M005.04 : test réel de la coupe et des occlusions.
- M005.05 : mesure temporelle de la super-résolution.
- M005.06 : comparaison temporelle synchronisée.
- M005.07 : audit de conservation des pistes et offsets audio.
- M005.08 : campagne 30 secondes / 3 minutes avec preuves et revue humaine.

**Porte de validation : M004 reste BLOCKED.** La présente PR constitue uniquement un développement préparatoire M005.01. Elle ne doit pas être fusionnée comme une M005 complète, ni déclencher une prétendue qualification RIFE. Toute inférence GPU, achat, moteur cloud payant, publication de poids tiers, fusion dans \`main\` ou installation personnelle reste soumise aux règles du projet.

## Références

- \`docs/roadmap-v2/missions/M005.md\` sur la branche documentaire \`docs/roadmap-m004-m017-complete\`.
- \`reports/004/FINAL.md\` sur la branche \`codex/studio-ia-m004-neural-local\`.
- PR #1 CPU; PR #2 programme; PR #3 NCNN; PR #4 anti-banding.
