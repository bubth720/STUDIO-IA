# STUDIO IA — ORDRE DE LANCEMENT M004 (8 novembre 2026)
## Première restauration neuronale réelle — exécution contrôlée

**Dépôt** : \`bubth720/STUDIO-IA\`  
**Référence CPU** : 0.3.0a2, commit applicatif testé \`4d42029f3bdbf260b72a6f2f0f81ed01be1265a9\`, clôture \`24f5c211cc96d7d6956d9e7452c4dc025693caa4\`.  
**Documentation active** : \`docs/roadmap-v2/EXECUTION_PROTOCOL.md\`, \`docs/roadmap-v2/missions/M004.md\`.  
**Ancienne référence complémentaire** : \`docs/mission-004/CAHIER-TECHNIQUE.md\`.  
**Statut à ce jour** : M004 NON COMMENCÉE ; les succès CPU/Qt/packaging ne prouvent aucune restauration neuronale.

> **Commande pour Codex :** Exécute M004 du dépôt \`bubth720/STUDIO-IA\` à partir de cette fiche, du protocole et du cahier \`M004.md\`. Développe et teste réellement. Publie des commits et une PR Draft. Aucun merge, aucune installation personnelle, aucun média privé téléversé et aucune ressource cloud payante sans autorisation. Distingue rigoureusement PASS, FAIL, SKIP et BLOCKED. Ne présente jamais un filtre classique ou un mock comme une inférence IA.

### Préflight obligatoire

1. Lire le dépôt distant, les PR #1 et #2, le bilan \`reports/consolidation/CLOTURE-PUBLICATION.md\`, le README, le code des modules \`engines.py\`, \`pipeline.py\`, \`jobs.py\`, \`media.py\` et le cahier M004. Vérifier HEAD, runs et artefacts au moment du démarrage. Ne pas réutiliser des SHAs comme vérités si la branche a évolué.
2. Conserver \`main\`, la PR #1, la PR #2, les branches historiques, les sources, les tests, les journaux et les sauvegardes. Ne jamais installer de pilote ou de programme sur les appareils personnels du propriétaire.
3. Développer sur une nouvelle branche \`codex/studio-ia-m004-neural-restoration\` depuis \`docs/roadmap-m004-m017-complete\` si cette branche reste la référence documentaire la plus récente. Ouvrir une PR en brouillon **vers cette branche documentaire** pour cette pile de branches, sans fusion. Sinon documenter explicitement la nouvelle base autorisée et la relation entre les PR.
4. Rejouer la baseline CPU/Qt et l'E2E hors réseau. La preuve de non-régression doit être enregistrée à un SHA exact : Windows, Linux, import, analyse, FFmpeg, audio, historique, comparaison, annulation, préservation des originaux et export sans écrasement.

### M004-A — Décision du moteur et provenance (livrable même sans GPU)

- Auditer versions, licences, commandes CLI et conditions réelles de \`Video2X\`, \`Real-ESRGAN-ncnn-vulkan\` ou autre backend équivalent officiellement maintenu. Choisir **un seul backend principal de super-résolution** et un modèle précisément identifié avant toute extension ; vérifier versions et options sur le binaire installé, sans recopier des flags historiques.
- Faire la différence entre exécutable, moteur, runtime GPU, shaders et poids de modèle. Documenter pour chacun source officielle, release ou commit figé, licence (code ET poids), empreinte, taille, dépendances, distribution autorisée ou externe seulement.
- Étendre \`model-manifest-v2\` ; entrée locale explicitement choisie, validation SHA-256, multi-fichiers si requis, chemins sûrs, refus des archives malformées et d'une substitution de fichier après contrôle. Aucun chargement arbitraire de code Python par des modèles non vérifiés.
- Établir les statuts machine : ABSENT, DETECTED, HASH_VERIFIED, COMPATIBLE, SHORT_TEST_PASS, VIDEO_E2E_PASS. Les statuts de détection ne valent jamais qualification.
- Protéger intégralement le parcours CPU, y compris les anciens jobs SQLite. Introduire un plan v2 versionné sans modifier silencieusement l'interprétation des plans v1.

**Preuves** : décision du backend, licences, version/\`--help\` réellement lus, schéma+tests négatifs, CI CPU verte.

### M004-B — Traitement neuronal bout-en-bout sur matériel compatible

- Examiner OS/arch, instructions CPU, GPU précis, pilote, Vulkan réellement utilisable, mémoire/VRAM observable et espace disque. Un GPU listé par le système ne prouve pas que l'inférence fonctionne.
- Tester une inférence **courte et réelle** avec modèle local qualifié. Consigner stdout/stderr expurgés, code de sortie, durée et mémoire lorsque mesurables. Aucun coût cloud ni utilisation GPU payante sans accord.
- Étendre l'adaptateur moteur et le pipeline : source non modifiée -> extraction ou flux frame selon backend -> upscale neuronal -> encodage -> remappage audio -> contrôle complet -> publication sans écrasement.
- Préserver cadence, timebase et PTS d'origine hors interpolation ; audio, offsets, nombre de frames, durée et colorimétrie selon politique explicitement supportée. Les formats HDR, 10 bits et flux secondaires non qualifiés doivent rester refusés, jamais convertis silencieusement.
- Tester une vidéo synthétique complète (au minimum 8 s) avec audio, et une référence haute résolution dégradée de façon reproductible. Comparer source, filtre CPU et résultat neuronal aux mêmes instants. Détecter halos, déformations, inventions de textures et instabilité temporelle ; ne pas promettre la récupération d'une vérité historique.
- Tester interruption en cours d'inférence, OOM, disque plein, binaire/modèle absent, source corrompue et changement du modèle après validation. Aucun résultat partiel ne doit être promu \`SUCCEEDED\`.

**Gate bloquante** : aucun \`VIDEO_E2E_PASS\` sans vidéo réellement inférée sur un matériel compatible, décodage intégral, audio/PTS validés et hash source inchangé. Les métriques PSNR/SSIM nécessitent une référence vraiment alignée. Absence de GPU = \`BLOCKED\` pour cette gate, pas \`PASS\`.

### M004-C — Interface, distribution et clôture

- Conserver l'interface française existante et ses comportements Qt. Ajouter une sélection explicite moteur + modèle + statut, estimation de stockage lorsqu'elle est mesurable, possibilité de prévisualiser un extrait source, comparaison avant/après (CPU vs NN) et des explications claires des risques.
- Le mode CPU doit rester disponible même si le moteur neuronal est absent. Aucun bouton "IA" actif sans modèle réellement compatible.
- Lancement hors réseau **après installation locale** obligatoire. Tests de permissions, absence de téléchargement silencieux, journal et diagnostic sans fuite de chemins privés.
- Maintenir la CI Windows/Linux sans GPU. N'utiliser une machine GPU que si effectivement disponible et autorisée; enregistrer les preuves GPU à part. Construire des ZIP de test seulement pour les plateformes réellement qualifiées, avec inventaire et SHA-256.
- Produire \`reports/004/INITIAL.md\`, \`TASKS.md\`, \`reports/004/evidence/\`, \`FINAL.md\` et un manifeste PASS/FAIL/SKIP/BLOCKED. Les liens vers la PR, la CI, les builds et les artefacts doivent exister réellement. Archiver une copie indépendante des artefacts éphémères lorsque possible.

### Critères de clôture, sans raccourci

1. Baseline M003 CPU toujours PASS sur environnements Windows et Linux appropriés, zéro régression de protection des fichiers.
2. Schéma de modèles et registre implémentés avec tests de corruption, licence absente, chemins non sûrs, remplacement de fichier et version incompatible.
3. Moteur/model exacts, provenance et licences documentées; test d'inférence réel, si matériel compatible.
4. Vidéo neuronale complète exportée avec audio, PTS/durée, résolution, décodage et SHA source vérifiés ; **sinon mission partiellement livrée, gate NN BLOCKED**.
5. UI et CLI n'annoncent aucun moteur incompatible comme opérationnel.
6. Rapport détaillé avec matériel, modèle, métriques, échecs et limitations; PR en brouillon; aucune fusion dans \`main\`.
7. Recommander la M005 uniquement après confirmation de la gate neuronale et des timings. Sinon fournir les travaux préparatoires réels et la liste exacte du matériel manquant.

### Ne pas faire pendant M004

- Ne pas inclure RIFE/interpolation avancée ou la stabilisation temporelle comme objectif principal : c'est le périmètre de **M005**.
- Ne pas développer la génération de scènes, le montage, la diffusion cloud ou une application Android.
- Ne pas promettre 4K photoréaliste, restauration parfaite des visages ou performances temps réel sans mesures.
- Ne pas altérer la PR #1 ni fusionner la PR #2. Le fait que la CI soit verte ne confère pas une autorisation de merge.

**Instruction finale** : produire le maximum de code réel et de preuves dans la session d'exécution. En cas de manque de GPU, livrer les composants logiciels testables et un rapport BLOCKED honnête, sans prolonger artificiellement une exécution ou prétendre qu'un modèle a traité une vidéo.
