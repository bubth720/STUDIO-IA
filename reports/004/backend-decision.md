# Décision backend M004

Voie prioritaire : **Real-ESRGAN NCNN/Vulkan v0.2.0**, hors processus, un seul modèle natif realesr-animevideov3-x2. L'aide officielle téléchargée a été réellement exécutée ; tous les arguments utilisés figurent dans evidence/ncnn-help.txt. Release, fichiers, tailles et SHA observés dans engines.lock.json. La licence du port NCNN est MIT, distincte du projet Python Real-ESRGAN BSD-3-Clause. Les poids/shaders restent à examiner indépendamment ; l'import refuse une licence absente/non revue. Aucun poids ou moteur embarqué dans Git/ZIP applicatif.

| Solution | Coût et compatibilité | Décision |
| --- | --- | --- |
| FFmpeg CPU 0.3.0a2 | Existant, testé Linux/Windows ; aucun poids/GPU requis | CONSERVER, voie par défaut |
| NCNN v0.2.0 | CLI image/paires param+bin simple, runtime natif et Vulkan ; pas de CUDA/PyTorch, découpage/réassemblage assumés par STUDIO IA | PRIORITAIRE, adaptateur expérimental, GPU BLOCKED |
| Video2X 6.4.0 | Pipeline C++/FFmpeg/NCNN, licences AGPL/dépendances natives et interface différentes ; pas d'installation justifiée du second stack | ALTERNATIVE documentée, non installé |
| Python/PyTorch | Dépendances et mémoire beaucoup plus importantes ; formats de poids et chargeurs à sécuriser | Non retenu |
| Anime4K | Aucun shader installé ; variante/chaîne à identifier avant étiquette CNN ou classique | ABSENT, non qualifié |
| RIFE | Porte M005 exige un vrai E2E neuronal M004 et PTS | Non développé ici |

GPU listé, Vulkan compatible, inférence courte et vidéo entière sont quatre états différents. Le présent hôte ne dépasse pas la présence du chargeur : vkCreateInstance=-9. AVX2 est observé, pas supposé disponible partout. Aucun seuil VRAM ou gain de qualité/performance inventé. Les empreintes de release sont calculées après téléchargement HTTPS officiel ; aucun digest/signature fournisseur disponible n'est prétendu.

Contrat initial volontairement borné : ×2 natif, CFR avec PTS/durées entières vérifiables et origine zéro, MP4, SDR BT.709 limitée déclarée, prétraitement neutre. VFR, HDR/rotation/flux secondaires et modèles arbitraires refusés plutôt que convertis silencieusement. L'agrandissement NCNN remplace Lanczos ; les conversions RGB24/BT709 ne redimensionnent pas. La durée de la dernière frame peut provenir de duration_ts du conteneur si le décodeur ne l'expose pas ; cette origine est tracée, sans cadence arrondie inventée.
