# STUDIO IA — livraison Windows V0 (13 novembre 2026)

Branche `claude/studio-windows-v0` (RESTORE de la PR #11 + CREATE + intégration Windows).
Rien n'est fusionné dans `main`. Les branches `ccr-d9ef863a-4ykxu5` (PR #11) et
`claude/create-foundations` restent intactes.

## Lancement en 3 étapes (Windows 10/11, 64 bits)

1. Télécharger l'artefact **STUDIO-IA-ALPHA-Windows-…** de la dernière exécution CI réussie
   de cette branche (onglet *Actions* du dépôt, compte GitHub requis). Le dézipper : il
   contient `STUDIO-IA-0.3.0a2-windows-AMD64-ALPHA.zip` et son `.sha256`.
2. Extraire ce ZIP dans un dossier, par exemple `Documents\STUDIO-IA`.
3. Double-cliquer sur **`Lancer-STUDIO-IA.cmd`**. Ouvrir l'onglet **Matériel et diagnostic**.

Lire aussi `PREMIER-LANCEMENT.txt` dans le dossier extrait.

## Ce qui fonctionne sans configuration

| Fonction | État | Preuve |
|---|---|---|
| Fenêtre unique en français : onglets RESTORE / CREATE / Matériel et diagnostic | Fonctionne | Tests Qt Windows + Linux, captures |
| Diagnostic matériel (processeur, RAM, disque, cartes Vulkan et leur mémoire, capacités, limites), export JSON | Fonctionne | Exécutable extrait lancé en CI Windows (`--machine`) |
| CREATE : ville procédurale, 4 caméras, plan 2D, séquence, `create_scene.json`, projet Unreal prêt | Fonctionne sans Unreal | Exécutable extrait lancé en CI Windows (`--create scene`, `new-project` dans un dossier accentué, `build-city`) |
| RESTORE classique (CPU) : import, plan, traitement, annulation, historique, export vérifié | Fonctionne **avec FFmpeg** | Parcours réel figé en CI Windows (vérifier, démarrer, annuler) |
| Comparaison avant/après : rideau, zoom synchronisé, déplacement, résolutions, export côte à côte | Fonctionne | Tests Qt |
| Paramètres, historique et journaux conservés dans `%LOCALAPPDATA%\STUDIO-IA` | Fonctionne | Hérité des lots précédents, testé |

FFmpeg n'est **pas inclus** (choix de licence et de taille, à décider par le propriétaire) :
placer `ffmpeg.exe` et `ffprobe.exe` dans `STUDIO-IA\ffmpeg\bin\`, ou utiliser « Chemins FFmpeg… ».

## Ce qui demande encore un GPU, Unreal ou des modèles

| Fonction | Ce qui manque | Comment l'essayer sur ce PC |
|---|---|---|
| **Restauration IA** (Animation / Vidéos réelles) | GPU Vulkan physique + modèles officiels (environ 50 Mo, téléchargés seulement avec accord) | `Premier-test-IA.cmd` : demande « OUI », vérifie les empreintes, puis lance l'inférence courte pour les 2 modèles et écrit les rapports |
| Mesure mémoire maximale de l'IA | Non instrumentée | Durée mesurée seulement ; à ajouter |
| Restauration IA d'une vidéo entière, qualité | Dépend du test précédent | Interface : choisir le modèle, « Aperçu neuronal », puis traitement |
| **CREATE dans Unreal** (construction, rendu) | Unreal Engine 5.6 à 5.8 installé séparément ; scripts **NON EXÉCUTÉS** | Bouton « Construire dans Unreal (expérimental) » quand Unreal est détecté |
| Installateur Windows (setup.exe) | Non fait ce soir : version portable seulement | Suppression du dossier = désinstallation ; les paramètres restent dans `%LOCALAPPDATA%` |

## Adaptation au matériel (aucune supposition)

- **GPU** : la carte dédiée est préférée à la carte intégrée (cas fréquent sur les PC portables
  de jeu). Les périphériques Vulkan logiciels (CPU) sont refusés comme GPU.
- **Taille des tuiles IA** selon la mémoire graphique détectée (estimation à confirmer par
  mesure) : moins de 1 Gio, IA refusée ; 1 Gio, 32 px ; 1,5 Gio, 64 ; 3 Gio, 128 ; 6 Gio, 256.
- **Budget disque** des traitements IA : 50 % de l'espace libre, au plus 16 Gio.
- **Avertissements** : moins de 8 Gio de RAM, moins de 10 Gio libres, matériel sous la
  recommandation Epic pour Unreal (CREATE reste utilisable en préparation de scène).

Remarque : la gamme Lenovo IdeaPad Gaming 3 date de 2020 et plus, pas de 2017. Le modèle exact
sera lu par l'onglet *Matériel et diagnostic*.

## Tests disponibles (sans résultat inventé)

- Local (Linux, en root) : **236 PASS / 1 SKIP / 1 FAIL**. Le FAIL est l'artefact root connu,
  PASS en utilisateur normal.
- CI Windows Server 2022 + Ubuntu 24.04 sur `3b6b4f9` : **succès** de toutes les étapes, dont la
  nouvelle étape « exécutable Windows extrait : profil matériel + CREATE ». Run 43449541369.
- CI sur `f0557bd` (script de test IA) : voir le run 43451193626.
- **Aucune inférence IA ni aucun rendu Unreal n'a été exécuté** : aucun GPU ni Unreal disponible
  dans les environnements de développement et de CI.
