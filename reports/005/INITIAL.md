# M005 — audit initial du 10 novembre 2026

Périmètre exclusif : bubth720/STUDIO-IA. Aucun autre projet, aucune fusion.

- Parent repris : PR #5, `feat/studio-ia-m005-temporal-preflight`,
  `8da64ebc519b9a75e6e00cc7316524bc370b0dfd`.
- Anti-banding CPU conservé depuis PR #4, `f9f3805a9d30bb4cdaca351dd356b5f920528874`.
- M004 : PR #3, code `000a9801f16da9a855442eab7d864384570cf5c2`,
  rapport final `fcce196fd176539ba01190b363ed786acdf147c7`.
  [CI M004](https://github.com/bubth720/STUDIO-IA/actions/runs/42644689519) : SUCCESS.
- [CI du parent M005](https://github.com/bubth720/STUDIO-IA/actions/runs/42709678348) :
  SUCCESS Windows/Linux au SHA 8da64eb.
- Baseline locale ciblée au parent : **49 PASS, 1 SKIP**, 195,05 s
  (temporal, policy, pipeline, Qt). Le SKIP concerne Video2X/modèles absents, sans qualification neuronale. Qt est testé en offscreen local ; X11 est qualifié en CI.
- Baseline M004 historique rejouée séparément avant reprise du parent :
  **102 PASS, 1 SKIP**, 179,86 s. Ce nombre ne décrit pas le nouveau code.
- Main observée : `61fe67ebb908da856964e88200e1220f83fc2bb8` ; PR #1–#5
  préservées en brouillon, aucune modification autorisée de ces PR.

Sources prescriptives lues : `docs/mission-004-005/EXECUTION-ORDER.md` sur le parent,
M005 et protocole général sur `docs/roadmap-m004-m017-complete` (`8db4916`).
L'ordre combiné autorise la préparation CPU M005 malgré la gate neuronale M004
fermée, sans autoriser l'activation RIFE.

Laboratoire : Linux x86_64, Python 3.12, FFmpeg/ffprobe 7.1.5, Qt offscreen local.
Aucun périphérique GPU NVIDIA/DRI ; Vulkan ne crée pas d'instance compatible
(ancienne collecte : -9). Ni pilote, ni modèle, ni machine payante installés.
Espace disque local limité : fixtures minuscules et traitements bornés ; les builds
Windows/Linux sont exécutés sur les runners CI existants.

État initial : socle CPU PASS, M004 neuronal BLOCKED, M005 PREPARATION,
M006 NON AUTORISÉE par les critères d'acceptation. Les tests de transport de M004
ne constituent pas une inférence Real-ESRGAN.
