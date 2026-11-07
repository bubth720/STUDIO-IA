# STUDIO IA / M003 / G4 — robustesse et qualité

Date UTC : 2026-11-07. Agent : Codex. Branche de mission, base main `61fe67e`.
Dernier jalon UI : `7e94421` ; modifications de robustesse testées avant ce commit.
Preuve finale source : **41 PASS, 0 FAIL, 1 SKIP en 52,57 s**, pytest 9.0.3.
`evidence/pytest-qualified.xml` et rapports d'audit joints. Ruff + format + mypy
(core/media/pipeline/jobs) PASS. Le hash exact de livraison est celui du commit
contenant ce rapport ; les preuves finales de packaging identifieront leur HEAD.

| Fixture / erreur | État | Preuve / politique |
|---|---|---|
| F01 8 s, audio, 2×, débruitage | PASS | décodage vidéo/audio complet, dimensions, durée, hash |
| F02 5 s muette | PASS | export MKV sans piste audio |
| F03 accents, espaces, ponctuation | PASS | arguments sans shell, vrais fichiers |
| F04 tronquée | PASS | rejet ffprobe, pas de réussite fictive |
| F05 portrait | PASS | ratio à l'arrondi pair près |
| F06 deux audios | PASS | deux pistes exportées/décodées |
| F06 sous-titres | PASS du refus | aucune suppression silencieuse, export non pris en charge |
| F07 VFR | PASS | même nombre de frames, PTS comparés à 1 ms |
| F08 tags BT.2020 | PASS du refus | pas une validation perceptuelle HDR |
| F09/F10 restauration/interpolation IA | NON EXÉCUTÉ | moteurs/modèles non qualifiés |
| Audio PCM → AAC / audio retardé | PASS | codec, canaux, fréquence, offset A/V à 100 ms |
| Paramètres, fichier absent, audio seul | PASS | erreur explicite |
| ffprobe absent, encodeur/filtre absents | PASS | refus avant traitement |
| Filtre invalide effectivement exécuté | PASS | FFmpeg échoue, aucune sortie promue |
| Destination existante / hardlink / concurrence | PASS | octets existants inchangés |
| Source modifiée pendant traitement | PASS | échec, pas d'export |
| Destination non inscriptible | PASS Linux | permissions POSIX ; SKIP motivé prévu sur Windows |
| Disque plein / décodage final échoué | PASS | injections de panne, export non finalisé |
| Annulation active + file d'attente | PASS | arrêt réel, absence de sortie finale |
| Timeout réel | PASS | processus temps réel arrêté après limite de test |
| Redémarrage + verrou d'instance | PASS | INTERRUPTED, pas de SUCCEEDED inventé |
| Confidentialité diagnostic | PASS | liste blanche exclut chemins/metadata/erreurs brutes |
| Hors ligne CPU + Qt offscreen | PASS | sandbox sans réseau, proxies inutilisables et sockets Python interdits en test CPU |

Défauts trouvés puis corrigés :

1. Fermeture après retrait d'historique : tokens terminaux purgés, état terminal
   et temps final écrits ensemble.
2. Tags HDR incomplets dans une fixture : la matrice BT.2020 est aussi un signal
   de refus, pas seulement les primaires/transfer. Pas de conversion implicite.
3. Hash de gros fichiers : vérification d'annulation à chaque bloc de 1 Mio.
4. Vérification audio : canaux/codec/fréquence et offset relatif vidéo contrôlés
   lorsque les timestamps sont disponibles, y compris zéro et valeurs négatives.
5. Provenance applicative enregistrée dans les tâches, doctor et résultats.

## Dépendances

Audit PyPI réel (`pip-audit==2.9.0`) : runtime PySide6-Essentials/Shiboken6 6.8.3,
zéro avis connu. Audit de l'environnement initial : 7 avis, 6 pour pip 25.0.1
et 1 pour pytest 8.3.5. Correctifs appliqués : pip 26.3 et pytest 9.0.3.
Nouvel audit : **zéro avis connu**, STUDIO IA ignoré par l'auditeur car paquet local
non publié sur PyPI (code revu/testé séparément). Rapports avant/après conservés.
`pip check` PASS avant mise à jour ; à relire sur l'environnement final.
Cela ne certifie pas l'absence de vulnérabilités natives de Qt/FFmpeg/OS.

Licences : code MIT ; Qt/PySide LGPL-3.0 dynamique et remplaçable, textes et notices
officiels archivés. FFmpeg/ffprobe, Video2X et modèles non redistribués.
Les sources Qt/PySide correspondantes sont référencées ; lien PySide HTTP 200,
QtBase redirige vers le miroir officiel. Aucun script distant exécuté.

Limites de qualité : fixtures synthétiques, aucun visage ou média privé ; ni score
VMAF/SSIM ni amélioration perceptuelle universelle revendiqués. Le décodage valide
la technique, pas la beauté. Tests neuraux IA-01/02/03 non réalisés ; un test pytest
SKIP explicite matérialise l'absence de qualification IA. Pas d'optimisation GPU.

Publication toujours BLOCKED : API création de branche retestée, HTTP 403.
Main distante reste à la base ; aucune fusion. Prochain jalon : binaire Linux
réellement lancé, workflow Windows disponible mais à exécuter après accès d'écriture.
