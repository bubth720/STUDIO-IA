# STUDIO IA / M003 / G1–G2 — CPU réel

Date UTC : 2026-11-07. Agent : Codex.
Branche : `codex/studio-ia-m003-first-verifiable-build`.
Base : `61fe67ebb908da856964e88200e1220f83fc2bb8`.
Fondation locale : `95696ba2e27b4e13485063cba89dfea1aefde358`.

## Réalisé et testé

CLI doctor/analyze/process/verify ; découverte et exécution FFmpeg/ffprobe ; plan
borné ; H.264/yuv420p ; débruitage léger/modéré ; Lanczos ; corrections de couleurs
conservatrices ; MP4/MKV ; audio AAC copié si compatible, sinon réencodé en AAC.
Un export n'est finalisé qu'après ffprobe, assertions et décodage intégral.
Un lien dur atomique empêche l'écrasement, même si une autre application crée
la destination après la validation. Source hashée avant/après ; temporaires privés.

Commande réelle :

```sh
STUDIO_IA_HOME="$PWD/artifacts/state" .venv/bin/python scripts/run_e2e.py --output artifacts/first-e2e
STUDIO_IA_HOME="$PWD/artifacts/state" .venv/bin/pytest -q
```

Premier lot : **22 PASS, 0 FAIL, 0 SKIP** en 25,03 s. F01 : 8 s, 320×180, 25 fps,
audio sinusoïdal → 640×360, H.264, AAC conservé ; décodage complet PASS, source intacte.

- Source SHA-256 : `c5121233b22b532e5e940b3d312c14e87900325f64ac343bd99895a710f318d5`.
- Sortie SHA-256 : `dfab7a182d6497169e1e0a154a10eefc5483d1c0a5f16fdece592cda30b3f3f6`.
- Encodage + vérification mesurés : 4,44 s, uniquement pour cette fixture/machine.
- Preuves complètes locales : `artifacts/first-e2e/` ; JSON synthétique joint au dépôt.
- Le premier JSON enregistre le HEAD de fondation : le code CPU était alors en
  cours d'écriture. La validation finale sera régénérée sur un commit identifié.

Tests négatifs réels : corruption, source absente, paramètres, nom accentué et
ponctuation, annulation de processus, conflit destination ; injection contrôlée
de panne disque/décodage et capacités absentes pour vérifier les refus.

## Publication et limites

Push Git refusé HTTP 403 ; création de branche via connecteur GitHub également
refusée HTTP 403 (« Resource not accessible by integration »), malgré les droits
du compte annoncés par l'API. L'utilisateur met à jour les droits de connexion.
**Aucun SHA distant de mission, aucune CI ni PR encore prouvés.**
Référence distante conservée : `main` au SHA de base ; aucune mutation de main.
Les portes de publication restent BLOCKED jusqu'à relecture d'un commit distant.

HDR/BT.2020, rotation, entrelacement, pixels non carrés, >8 bits et sous-titres/
flux secondaires sont refusés explicitement. Pas de tone mapping ou suppression
invisible. Les métriques perceptuelles et l'IA ne sont pas validées par ces tests.
Prochain jalon : Qt, persistance, annulation depuis l'interface, CI et packaging.
