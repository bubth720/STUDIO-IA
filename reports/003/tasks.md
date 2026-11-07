# Tableau Mission 003

Responsable de toutes les tâches : Codex. Aucun DONE sans preuve.

| ID | Entrée / dépendance | Fichiers | Test / preuve | État | Livraison |
|---|---|---|---|---|---|
| G0 | dépôt initial / PDF | audit, pyproject, README | audit PASS ; branche distante refusée 403 | BLOCKED publication | 95696ba local |
| G1 | G0 | core, CLI, analyzer | doctor/analyze réels, outils absents | DONE local | 35a780f |
| G2 | G1 | pipeline, export, fixtures | F01 E2E, hash, audio, décodage complet PASS | DONE local | 35a780f puis 44051e7 qualifié |
| G3 | G2 | jobs, UI, preview | Qt natif et offscreen, annulation, reprise PASS | DONE local | 7e94421 puis 843efdd gelé |
| G4 | G2–3 | tests, quality | 41 PASS, 1 SKIP IA, audits corrigés | DONE local | 2e7a070 puis 44051e7 |
| G5 | G4 | workflows, package, docs | ZIP Linux lancé/extrait PASS ; CI/Windows non exécutés | BLOCKED CI/Windows | 44051e7, 0f627a1, 843efdd |
| G6 | G2 | engines, models | API intégrité locale testée ; run neural SKIP | PARTIEL | 35a780f, tests 2e7a070 |
| G7 | G0–6 | rapports, docs, PR | bilan et bundle prêts ; PR refusée faute de branche | BLOCKED PR distante | clôture locale, voir manifest |

Les DONE locaux sont soutenus par des preuves ; ils ne franchissent pas les portes
de publication/CI. Niveau formel de mission RED pour absence de code distant.
Voir 04-delivery.md : chaque AC et chaque limite sont explicités. Aucun SHA local
n'est présenté comme un commit publié. Main API finale = 61fe67e, inchangée.
