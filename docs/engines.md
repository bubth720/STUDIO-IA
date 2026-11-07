# Qualification des moteurs

| Moteur / opération | Détection | Compatibilité | Vidéo réelle |
|---|---|---|---|
| FFmpeg 7.1.5 local Linux | versions, filtres et encodeurs exécutés | CPU libx264/AAC/hqdn3d/eq/scale | PASS, F01–F07 et GUI |
| FFmpeg sur Windows | workflow prévu, version Chocolatey 7.1.1 | non vérifié sans run natif | NON VÉRIFIÉ tant que CI absente |
| Video2X | absent du PATH de cet environnement | GPU/API et runtime non qualifiés | SKIP |
| Real-ESRGAN / Real-CUGAN / Anime4K / RIFE | aucun modèle local qualifié | dépend de Video2X installé et aide réelle | NON EXÉCUTÉ |

`studio-ia doctor` est la source de vérité de la machine utilisée ; les listes de
filtres/encodeurs proviennent des binaires réellement exécutés. « Présent » ne vaut
ni compatible, ni testé, ni validé sur vidéo. Aucun résultat neuronal dans la mission.

`engines.py` prépare un contrat d'adaptateur et interroge seulement `--version` /
`--help` de Video2X s'il est installé. Aucun ancien flag d'upscale n'est supposé.
Le registre local `inspect_model`/`save_model_record` exige nom/version/provenance/
licence/moteur/SHA et vérifie taille/intégrité du fichier choisi. L'import n'exécute
pas le fichier et l'intégrité ne vaut pas preuve de sûreté ni de qualité du modèle.
Ce registre est une API préparatoire, sans sélecteur de modèle ni traitement IA
actif dans la GUI.

Mission 004 proposée : choisir une version Video2X et un matériel Vulkan/GPU réels,
vérifier licences/empreintes des modèles, implémenter l'adaptateur selon son aide,
exécuter IA-01/02/03, contrôler stabilité temporelle/halos/mouvement et audio.
Ne pas conditionner la fiabilité CPU à une intégration neuronale non validée.
