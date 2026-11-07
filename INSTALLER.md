# STUDIO IA 0.3.0a2 — ALPHA expérimentale consolidée

Application de bureau Windows x64 / Linux x64. Cette archive n'est pas une APK.
Consulter BUILD_INFO.json et BUILD_SMOKE.json pour la plateforme et l'essai réel.
Seules les plateformes accompagnées d'une preuve sont qualifiées.

## Archive portable

1. Télécharger le ZIP et son fichier `.sha256`. Windows : `Get-FileHash fichier.zip -Algorithm SHA256`.
   Linux : `sha256sum -c fichier.zip.sha256`.
2. Extraire tout le dossier, en conservant `_internal` et `licenses`.
3. FFmpeg **et ffprobe** 5.1 ou plus récents doivent être disponibles localement. Aucun binaire n'est
   téléchargé automatiquement. Si nécessaire, obtenir une compilation depuis
   https://ffmpeg.org/download.html, vérifier ses empreintes puis indiquer les deux
   binaires dans `ffmpeg/bin/` à côté de l'application, ou sélectionner FFmpeg
   dans « Chemins FFmpeg… » (ffprobe sera détecté à côté) ; aucune installation personnelle n'a été faite
   par cette mission. Les builds CPU requièrent libx264, AAC, hqdn3d, scale, eq.
4. Windows : lancer `STUDIO-IA.exe` ou `Lancer-STUDIO-IA.cmd`. Linux :
   `chmod +x STUDIO-IA Lancer-STUDIO-IA.sh` puis `./Lancer-STUDIO-IA.sh`.
   Linux nécessite glibc au moins aussi récente que le système de construction
   (voir le champ `glibc` de BUILD_INFO), ainsi qu'un affichage X11/Wayland et les dépendances Qt du système.
   Le build de compatibilité Bookworm vise glibc 2.36 ; consulter ses preuves effectives.
   Sous Debian/Ubuntu, les dépendances d'affichage peuvent être préparées avec
   `sudo apt-get install libegl1 libgl1 libdbus-1-3 libfontconfig1 fonts-dejavu-core libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-image0 libxcb-render-util0 libxcb-xinerama0`.
   Ces commandes sont des instructions pour l'utilisateur ; la mission ne les
   exécute que dans les environnements de test gérés.
5. Importer une vidéo, choisir Préservation, vérifier une destination nouvelle,
   cliquer « Vérifier le plan » puis « Démarrer ». Attendre la validation complète.
6. Comparer source/export au même instant avec le curseur ; « Ouvrir l'export »
   utilise le lecteur installé. Aucun lecteur tiers n'est fourni.

Les paramètres personnalisés permettent débruitage, Lanczos, luminosité/contraste/
saturation légers, CRF 12–28. Ce traitement classique n'est pas une IA neuronale.
Un agrandissement 4K n'atteste aucun nouveau détail fiable.

## Depuis les sources (alternative et développement)

Python 3.12 et FFmpeg/ffprobe locaux sont nécessaires.

```sh
python -m venv .venv
# Linux : source .venv/bin/activate
# Windows PowerShell : .venv\Scripts\Activate.ps1
python -m pip install pip==26.3
python -m pip install -e ".[gui,dev,build]"
studio-ia doctor
studio-ia-gui
```

L'installation des dépendances demande Internet ; l'utilisation fonctionne hors ligne.
Pour éviter les commandes de création/activation du venv, les scripts
`Installer-sources.sh` (Linux) et `Installer-sources.ps1` (Windows) installent
uniquement dans `.venv` du dossier source. Ils nécessitent Python 3.12 préalable.
Les lanceurs `Lancer-sources.sh` / `.ps1` ouvrent ensuite l'interface. Les scripts
Windows restent à qualifier sur runner Windows ; ne pas désactiver globalement
la politique d'exécution PowerShell pour les lancer.
Pour une installation sans réseau, préparer les wheels à l'avance sur le même OS :
`python -m pip download -r requirements-runtime.lock -d wheels` ; installer ensuite
avec `--no-index --find-links wheels`. Pour le paquet portable Python est déjà fourni.

## Dépannage et limites

- Erreur moteur : lancer `STUDIO-IA --cli doctor` (Windows : `.exe`) ou utiliser Diagnostic.
  Variables possibles : `STUDIO_IA_FFMPEG`, `STUDIO_IA_FFPROBE` (chemins locaux).
- Destination existante, lien ou source identique : choisir un autre nom. Aucun écrasement.
- HDR/BT.2020, rotation, entrelacement, >8 bits, pixels non carrés, sous-titres et
  données secondaires : refus explicite de l'export MVP pour éviter toute perte.
- MP4/MKV, toutes les pistes audio ; AAC copié en MP4, sinon conversion AAC.
  MKV conserve les codecs audio. Temporalité VFR conservée, progression indéterminée.
- Annuler attend l'arrêt réel et retire les temporaires possédés. Après un crash,
  la tâche devient INTERROMPUE et peut être relancée depuis l'original vers un nouveau
  nom ; aucune reprise au dernier frame. Des dossiers `.studio-ia-*` orphelins peuvent
  subsister après un arrêt brutal ; ne pas supprimer un dossier d'une instance active.
- Finalisation sans remplacement : lien dur, ou renommage Windows / Linux
  `renameat2(RENAME_NOREPLACE)` si disponible. Le repli Linux est testé par injection
  d'indisponibilité des liens, sur un vrai système local ; les supports physiques
  FAT/exFAT et les partages réseau restent non qualifiés. Aucun repli vers un
  renommage POSIX qui écraserait la destination.
- Historique/journaux locaux : `%LOCALAPPDATA%\STUDIO-IA` sur Windows,
  `$XDG_STATE_HOME/studio-ia` ou `~/.local/state/studio-ia` sur Linux.
  `STUDIO_IA_HOME` permet un dossier différent. Les chemins sont privés : relire
  les journaux avant de les partager. Le dépôt/CI ne contient que du synthétique.
- Désinstaller : supprimer le dossier portable et éventuellement l'historique local.
  Les médias source et exports ne sont pas supprimés avec l'historique.
- Temps CPU dépendant du média et du matériel ; aucune estimation universelle.
  Pas de création vidéo, compte, télémétrie, service réseau, APK ou modèle inclus.
