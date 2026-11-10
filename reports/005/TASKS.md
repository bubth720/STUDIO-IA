# Lots publiés et portes M005

Les branches sont empilées ; chaque PR reste en brouillon. Les PR #1–#5 sont
préservées. Aucun raccordement RIFE productif, aucune fusion dans main.

| Lot | Code | PR | Qualification actuelle |
|---|---|---|---|
| M5.01/.02/.04 : PTS, EOF, scènes, scheduler protégé | 02a8754 + e879b6e | [#6](https://github.com/bubth720/STUDIO-IA/pull/6) | 34 tests CPU ciblés ; correction Windows ensuite qualifiée en CI |
| M5.05/.07/.08 : mouvement, audio, contrôles et mesures bornés | 1b50d48 | [#7](https://github.com/bubth720/STUDIO-IA/pull/7) | 42 tests temporels ciblés ; protocole FFmpeg réel |
| M5.06 : inspection Qt par PTS | 7d2f028 | [#8](https://github.com/bubth720/STUDIO-IA/pull/8) | QTest réel et régression GUI ; six paires en cache |
| Compléments M004 indépendants | 24e6c56 | [#9](https://github.com/bubth720/STUDIO-IA/pull/9) | 40 tests registre/plans ; vrais processus concurrents |
| Qualification consolidée / distribution | Branche codex/studio-ia-m005-qualification | PR dédiée après publication | Smoke temporel source exécuté ; CI native/build/extraction à consigner dans FINAL.md |
| M004 image/vidéo NN réelle | Aucun résultat produit | PR #3 préservée | BLOCKED : GPU, poids/droits et qualification réelle absents |
| M5.03 et comparaison CPU/NN/stabilité NN | Plan ×2 seulement, jamais exécuté | Toutes les branches gardent la gate fermée | BLOCKED |
| Occlusions, mains, visages, rotations rapides | Aucune validation réelle | — | BLOCKED ; aucun masque d'occlusion prétendu |

Les réussites locales portent sur les révisions des lots testées. Les rapports
CI et preuves de livraison finales précisent les SHA exacts, OS et éventuels
SKIP. Un test de transport/répétition n'est jamais compté comme RIFE.

Le protocole GPU futur est celui de l'ordre combiné et de M004 : manifeste exact
avec licences du moteur/poids/shaders, Vulkan et GPU réellement compatibles,
NN01 image puis NN02 vidéo complète avec audio/PTS/qualité. RIFE ne s'ouvre
qu'après M004 PASS, puis nécessite sa propre qualification réelle opt-in.
**M006 reste NO_GO** tant que les critères bloquants M005 ne sont pas tous PASS.
