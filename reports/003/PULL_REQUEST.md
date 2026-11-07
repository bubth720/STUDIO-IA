# M003 - STUDIO IA first verifiable build (CPU + GUI + CI)

**Corps de PR préparé ; PR non créée : accès GitHub écriture refusé HTTP 403.**
Base proposée : `main`, `61fe67ebb908da856964e88200e1220f83fc2bb8`.
Head local : `codex/studio-ia-m003-first-verifiable-build`. Ne pas fusionner sans
autorisation du propriétaire ; pas d'auto-merge.

Le dépôt initial ne contenait qu'un README. Cette branche ajoute une application
Qt française locale et une CLI partageant le même pipeline FFmpeg CPU : importer,
analyser, planifier, débruiter/redimensionner/corriger légèrement, exporter après
ffprobe et décodage complet, comparer les images et conserver un historique.
Les sources et destinations ne sont jamais écrasées. Annulation réelle et
relancement sûr depuis l'original. Aucune fonction de création vidéo ni modèle IA.

| Validation | Résultat |
|---|---|
| Linux source | 41 PASS, 1 SKIP neuronal explicite |
| E2E F01 réel | 320×180 → 640×360, 8 s, audio, hash source et décodage PASS |
| Qt natif X11 et hors écran | parcours + annulation PASS |
| ZIP Linux extrait sans réseau | binaire gelé PASS, 538 empreintes vérifiées |
| Lint / format / types cœur / pip check | PASS |
| Audit PyPI runtime et environnement corrigé | 0 avis connu, limites natives documentées |
| CI / Windows | non exécutés, à qualifier après publication |

- [ ] AC-01 branche distante publiée (actuellement bloquée)
- [x] AC-02 main préservée
- [x] AC-03 à AC-10 diagnostic, média, traitement, audio, source, GUI, annulation
- [ ] AC-11 run CI E2E distant vert
- [x] AC-12 archive Linux testée ; Windows reste à qualifier
- [x] AC-13 résultats et limites explicites

Preuves : [rapport](04-delivery.md), [capture réelle](evidence/gui-success.png),
[E2E](evidence/release-e2e.json), [archive vérifiée](evidence/archive-verification.json).
Run GitHub : aucun ; liens à ajouter seulement après exécution effective.
Le workflow Ubuntu/Windows teste réellement FFmpeg/Qt puis le paquet, et publie
JSON/logs/médias synthétiques/ZIP/SHA pendant 14 jours. Pas de release stable.

Licences MIT pour le projet ; Qt/PySide LGPL dynamique, notices tierces et sources
correspondantes documentées ; FFmpeg et poids de modèles non redistribués.
HDR/rotation/entrelacement/>8 bits/SAR et sous-titres/données sont refusés pour
éviter une conversion/perte implicite. Liens durs nécessaires à la finalisation.
Tests synthétiques, pas de gain perceptuel universel ni d'essai personnel promis.

Validation ultérieure demandée : examen et qualification Windows après CI.
**Cette PR doit rester en brouillon et non fusionnée tant que les portes bloquées
ne sont pas satisfaites et que la fusion n'est pas explicitement autorisée.**
