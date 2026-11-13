# Qualification des moteurs

## Développement M004 — 9 novembre 2026

Le tableau plus bas est l'instantané historique M003. La réception actuelle est
dans [reports/004/FINAL.md](../reports/004/FINAL.md). CPU 0.3.0a2 reste la voie par
défaut ; l'adaptateur NCNN est expérimental et **la mission neuronale reste BLOCKED**.
Les CI Windows/Linux CPU ne prouvent pas une exécution GPU.

L'interface permet de choisir un manifeste local v2 puis un binaire NCNN local
épinglé, inspecte intégrité/licences déclarées et tente une véritable inférence
courte seulement si Vulkan expose un GPU physique compatible. L'entrée NCNN reste
désactivée sinon. Anime4K est absent/non qualifié ; RIFE est réservé à M005.
Aucun téléchargement ou pilote n'est installé à l'ouverture ou au traitement.

Dans un laboratoire autorisé, avec les dépendances source déjà installées :

```sh
studio-ia doctor neural --json hardware.json
studio-ia doctor neural --binary /chemin/realesrgan-ncnn-vulkan --json diagnostic.json
studio-ia model-check manifeste.json /racine/modeles --register registre.json
studio-ia neural-plan source.mp4 nouvelle_sortie.mp4 --manifest manifeste.json --model-root /racine/modeles --binary /chemin/realesrgan-ncnn-vulkan --json plan-v2.json
studio-ia preview-neural plan-v2.json nouveau_dossier_apercu --seconds 0.2 --duration 1 --json apercu.json
studio-ia process-neural plan-v2.json --json traitement.json
studio-ia verify plan-v2.json nouvelle_sortie.mp4
```

Ces commandes ne téléchargent rien ; elles refusent un modèle absent, corrompu,
non conforme au schéma ou sans licences code/poids/shaders déclarées séparément
et revues. Un champ de licence n'est pas une attestation juridique automatique.
Les fichiers acceptés sont seulement les paires NCNN exactes param/bin du
catalogue fermé (`CATALOG`, `src/studio_ia/models.py`) : `realesr-animevideov3`
×2 natif (animation) et, depuis le LOT 03, `realesrgan-x4plus` ×4 natif (prises de
vue réelles) réduit en Lanczos vers la sortie ×2. Manifestes revus prêts à l'emploi :
`manifests/`. Les fichiers Python/PTH/pickle et les commandes arbitraires
ne sont pas chargés. Voir [schéma](../schemas/model-manifest-v2.json),
[plan v2](plan-v2.md) et [lock](../engines.lock.json).

Sur l'hôte de mission : chargeur Vulkan présent, mais vkCreateInstance=-9 ; aucune
inférence n'a été réalisée. Les poids officiels ont été inspectés, mais leurs droits
n'ont pas été établis séparément : aucun manifeste productif prêt n'est fourni.
Le binaire du port NCNN est MIT ; ne pas le confondre avec le projet Python BSD-3-Clause,
les poids, shaders ou dépendances. Les hashes observés ne remplacent pas une signature
éditeur absente. Aucun moteur/poids tiers n'est inclus dans les distributions.

La qualification reproductible est explicite :

```sh
python scripts/qualify_neural.py --output nouveau_rapport
# Seulement sur un laboratoire compatible avec un modèle/licences préparés :
python scripts/qualify_neural.py --output nouvelle_campagne --run --binary /chemin/realesrgan-ncnn-vulkan --manifest manifeste.json --models /racine/modeles
```

La première commande produit le diagnostic et retourne 2/BLOCKED sans moteur/GPU
qualifié. Le second mode crée une séquence synthétique de huit secondes/deux pistes
audio et tente NN01 ; il ne valide pas à lui seul NN02, la revue visuelle ou M005.
`tests/test_neural_*` utilise des doubles explicitement non neuronaux pour qualifier
le transport et les refus ; ces tests ne constituent jamais une preuve GPU.

## Instantané M003 conservé

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
