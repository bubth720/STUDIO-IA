# LOT 01 — Consolidation du socle CPU sans régression

12 novembre 2026. Mission directrice V1 IA, LOT 01, autorisé par le propriétaire.
**Statut : PASS** (CPU). Consolidation faite, requalifiée localement et par la CI native
Windows/Linux de la PR brouillon #11 (run 43294655171 annulé par concurrence, run 43295027960 retenu).
Aucune fusion dans `main`, aucune PR existante modifiée, aucune dépense.

## Ce qui a été consolidé

Branche `ccr-d9ef863a-4ykxu5`, issue de `main` (`61fe67e`) par la pile complète :

| Étape | SHA | Contenu |
|---|---|---|
| Base | `7ee80b2` | Tête PR #10 = PR #1 + #3 (code `000a980`) + #4 → #10 |
| Fusion | `6388156` | `fcce196` (tête PR #3) : bilan M004, preuves, `docs/plan-v2.md`. Absent de la pile car PR #4 était basée sur `000a980` |
| Fusion | `339a415` | `8db4916` (PR #2) : `docs/roadmap-v2/`, 20 fichiers additifs |
| Correction | `dc1a056` | `MISSION_STATUS.json` : M004 BLOCKED, M005 PREPARATION_BLOCKED, approbation requise pour chaque lot |

Les deux fusions sont sans conflit. Les seuls fichiers touchés de part et d'autre
(`README.md`, `docs/engines.md`) ne reçoivent que des ajouts M004. **Aucun fichier de
`src/`, `tests/`, `scripts/`, `ui/` ou des workflows n'est modifié** par rapport à
`7ee80b2` : API, CLI, schémas de plans, base de données, interface et protection des
originaux sont donc strictement ceux qualifiés en CI sur `7841ccd`/`7ee80b2`.

## Requalification locale (cet environnement)

Conteneur Linux 6.18, 4 vCPU, Python 3.13.18, FFmpeg 6.1.1, PySide6 6.8.3, Qt offscreen,
**exécution en root**, sans GPU ni `/dev/dri`. SHA testé : `dc1a056` (code identique à `7ee80b2`).

| Contrôle | Résultat |
|---|---|
| `ruff check`, `ruff format --check` | PASS (61 fichiers) |
| `mypy` (13 modules du workflow) | PASS |
| `pytest -q -ra` (165 cas) | **163 PASS / 1 SKIP / 1 FAIL**, 93 s |
| `test_failures.py` rejoué en utilisateur non privilégié (uid 65534) | **3/3 PASS** |
| `scripts/run_e2e.py` (import, CPU, vérification, export) | PASS |
| `scripts/run_temporal_checks.py` | `PASS_CPU_ONLY`, `m005_accepted=false` |

L'unique FAIL, `test_unwritable_destination`, vient de l'environnement : root ignore
`chmod 0o500`. Rejoué sous un utilisateur normal, il passe. Ce n'est pas une
régression et le test n'a pas été modifié. Le SKIP est attendu (Video2X/modèles absents).
Python 3.13 au lieu de 3.12 de la CI : écart toléré par `requires-python`, mais la
référence de qualification reste la CI 3.12.

Preuves : [evidence/](evidence/) (JUnit XML, résumé pytest, journaux E2E et temporel).

## Qualification CI native (référence G1)

[Run 43295027960](https://github.com/bubth720/STUDIO-IA/actions/runs/43295027960) — **success**,
tête `6f38d6d` (code identique à `7ee80b2`), `BUILD_INFO source_dirty=false`.

| Étape | Ubuntu 24.04 / Py 3.12.16 / Qt X11 | Windows Server 2022 / Py 3.12.10 / Qt natif |
|---|---|---|
| Lint + types | PASS | PASS |
| pytest complet | PASS | PASS |
| Contrôles temporels CPU | PASS (`neural_executed=false`) | PASS (`neural_executed=false`) |
| E2E CPU synthétique (13 assertions, original intact) | PASS | PASS |
| Build PyInstaller + lancement figé (vérifier/démarrer/annuler) | PASS | PASS |
| ZIP extrait : intégrité + hashes | PASS, 610 fichiers | PASS, 382 fichiers |
| Installateur source en chemin Unicode | — | PASS |

ZIP applicatifs internes : Linux `aa3461f88f1fc42908152019b30c72b30e03fb1e220fa9cce1d275119de6d75c`,
Windows `2205baa50fa8487f1701e1451d198522217dac2927f8499498ff9aa71ebf2a24`.
Artefacts Actions (expirent le **26/11/2026**) : ALPHA-Linux `sha256:685e1f69…d55ed`,
ALPHA-Windows `sha256:37276ff4…52faf8`, evidence-Linux `sha256:be703bc5…8ec8ea`,
evidence-Windows `sha256:35349c50…4ffa`.

## Non couvert par ce lot (honnêteté des preuves)

- Builds PyInstaller, lancement figé et ZIP extrait : non rejoués ici ; couverts par la CI de la PR.
- Fermeture Qt sur écran physique, chemins réseau/ACL Windows, disque réellement plein : non testés ici.
- Aucune inférence neuronale : G2 reste **BLOCKED** (GPU, licence des poids, modèle généraliste).
- Les artefacts CI des runs 42907280119 et 42644689519 expirent les 23 et 24/11/2026 ; la
  CI de cette PR produira des artefacts équivalents pour la tête consolidée.

## Décision

G1 (CPU) : **PASS** sur les runners Windows/Linux et en local (hors poste utilisateur physique).
LOT 02 : **NO-GO tant que** le propriétaire n'a pas choisi la machine GPU (option A
recommandée : son PC avec un pilote Vulkan) et tranché la licence des poids Real-ESRGAN.
Les PR #1 à #10 restent ouvertes et intactes ; leur fermeture relève du propriétaire.
