# STUDIO IA 0.3.0a1 — ALPHA expérimentale

Application de bureau Windows x64 / Linux x64. Cette archive n'est pas une APK.
Consulter BUILD_INFO.json et BUILD_SMOKE.json pour la plateforme et l'essai réel.
Seules les plateformes accompagnées d'une preuve sont qualifiées.

## Archive portable

1. Télécharger le ZIP et son fichier `.sha256`. Windows : `Get-FileHash fichier.zip -Algorithm SHA256`.
   Linux : `sha256sum -c fichier.zip.sha256`.
2. Extraire tout le dossier, en conservant `_internal` et `licenses`.
3. FFmpeg **et ffprobe** doivent être disponibles localement. Aucun binaire n'est
   téléchargé automatiquement. Si nécessaire, obtenir une compilation depuis
   https://ffmpeg.org/download.html, vérifier ses empreintes puis indiquer les deux
   binaires dans « Chemins FFmpeg… » ; aucune installation personnelle n'a été faite
   par cette mission. Les builds CPU requièrent libx264, AAC, hqdn3d, scale, eq.
4. Windows : lancer `STUDIO-IA.exe`. Linux : `chmod +x STUDIO-IA` puis `./STUDIO-IA`.
   Linux nécessite glibc au moins aussi récente que le système de construction
   (voir BUILD_INFO), ainsi qu'un affichage X11/Wayland et les dépendances Qt du système.
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
- FAT/exFAT et partages sans liens durs : finalisation refusée ; utiliser NTFS/ext4
  ou un système acceptant les liens durs dans le dossier de destination.
- Historique/journaux locaux : `%LOCALAPPDATA%\STUDIO-IA` sur Windows,
  `$XDG_STATE_HOME/studio-ia` ou `~/.local/state/studio-ia` sur Linux.
  `STUDIO_IA_HOME` permet un dossier différent. Les chemins sont privés : relire
  les journaux avant de les partager. Le dépôt/CI ne contient que du synthétique.
- Désinstaller : supprimer le dossier portable et éventuellement l'historique local.
  Les médias source et exports ne sont pas supprimés avec l'historique.
- Temps CPU dépendant du média et du matériel ; aucune estimation universelle.
  Pas de création vidéo, compte, télémétrie, service réseau, APK ou modèle inclus.
