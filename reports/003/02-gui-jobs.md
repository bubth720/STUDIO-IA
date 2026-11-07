# STUDIO IA / M003 / G3 — Qt et tâches

Date UTC : 2026-11-07. Agent : Codex.
Base main : `61fe67ebb908da856964e88200e1220f83fc2bb8`.
Jalon CPU local : `35a780f` ; publication encore refusée 403 lors du dernier essai.

Réel : interface française Qt reliée au planner/runner commun avec la CLI ;
analyse/preview/traitement hors thread graphique ; profils Préservation,
Personnalisé et Témoin ; réglages bornés ; vérification du plan puis exécution ;
progrès native FFmpeg ; annulation ; comparaison coulissante d'images extraites
au même temps demandé ; ouverture export, journal et historique SQLite.
Relancement depuis l'original, retrait d'entrée sans effacer les médias,
rechargement d'un résultat après contrôle des hashes, diagnostic exportable
sur liste blanche sans chemins ni métadonnées libres.

Un seul worker intensif ; verrou OS d'instance ; états persistés en transactions.
Un état non terminal récupéré au démarrage devient INTERRUPTED, jamais SUCCEEDED.
Annulation propre puis escalade contrôlée si le processus ne répond pas.

Preuves : `evidence/gui-x11.json`, `evidence/gui-success.png`.

- Smoke hors écran : PASS, Qt `offscreen`, vrais clics QTest et FFmpeg.
- Smoke affichage X11 virtuel : PASS, Qt `xcb`, 400 événements timer observés.
- Vidéo 8 s exportée en 640×360, audio présent, décodage complet et hash source PASS.
- Deuxième traitement lancé puis annulé par le bouton : CANCELLED, aucune sortie.
- Les images ne sont ni maquettes ni captures d'un démonstrateur préenregistré.
- Pas d'essai humain sur écran physique ni sur appareil personnel.

Commande native réellement exécutée :

```sh
DISPLAY=:99 QT_QPA_PLATFORM=xcb STUDIO_IA_HOME="$PWD/artifacts/state" \
  .venv/bin/python scripts/gui_smoke.py --output artifacts/gui-x11-verified
```

Xvfb Debian 21.1.16-1.3+deb13u4 extrait dans `/workspace/studio-test-tools`, sans
installation système ou personnelle. Paquet officiel SHA-256 :
`893d87bf159b6de077a929fc796a73c39f837d45310b2076e3eeebebb80552b6`.
Le sandbox interdit la connexion au socket d'affichage ; l'essai X11 a été fait
hors sandbox avec TCP désactivé. Les tests hors écran fonctionnent sans réseau
dans le sandbox. La compétence cloud-desktop a confirmé que le contrôle du bureau
partagé nécessitait un outil `js` absent de la session ; Xvfb a servi d'alternative.

Bug détecté/corrigé : fermeture après retrait d'une entrée d'historique, due à un
token de job terminal conservé. Tests ciblés jobs : 3 PASS après correction.
Les preuves intermédiaires précèdent les derniers ajouts de diagnostic/historique ;
la suite et le binaire finaux seront retestés sur une révision identifiée.

Limites : lecture via le lecteur du système ; comparaison d'images fixes, pas de
lecture A/B synchronisée en continu. Relancement complet, pas reprise au frame.
Après crash brutal des temporaires privés peuvent subsister (jamais promus seuls).
Prochain jalon : matrice négative, packaging, licences et CI.
