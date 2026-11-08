# STUDIO IA — Protocole permanent d’exécution par missions (M004–M017)

**Version** : 1.0 (8 novembre 2026)  
**Dépôt officiel** : `bubth720/STUDIO-IA`  
**Branche de référence à la rédaction** : `codex/studio-ia-consolidation-v1` au commit `24f5c211cc96d7d6956d9e7452c4dc025693caa4`  
**PR de référence** : `#1` en brouillon. Aucune fusion autorisée.  
**Application vérifiée** : `0.3.0a2` ALPHA CPU; M004 neuronal non exécutée.

## 1. Une seule commande pour lancer une mission

> **« Codex, dans le dépôt `bubth720/STUDIO-IA`, consulte `docs/roadmap-v2/CODEX-START-HERE.md`, le protocole `docs/roadmap-v2/EXECUTION_PROTOCOL.md` et exécute intégralement la mission MXXX décrite dans `docs/roadmap-v2/missions/MXXX.md`. Réutilise les acquis, respecte toutes les portes de validation, publie une branche et une PR en brouillon. Ne fusionne rien. Fournis preuves, liens et bilan PASS/FAIL/SKIP/BLOCKED. »**

Tu remplaces uniquement `MXXX` par `M004`, `M005`, ... `M017`. Si le document demandé n’existe pas, si son périmètre est ambigu ou si une dépendance est manquante, Codex ne doit pas improviser une autre mission : il produit un rapport de blocage et propose le correctif minimum. La présence d’un cahier ne vaut pas autorisation d’une dépense, d’une installation personnelle ou d’une fusion.

## 2. Interdictions permanentes

- Ne jamais fusionner dans `main` sans consentement explicite; ne pas activer auto-merge.
- Ne jamais supprimer ou réécrire des branches historiques, rapports, sources, originaux vidéos ou sauvegardes.
- Ne jamais intervenir sur les dépôts JARVIS, PERSONA IA, ATELIER ou autres sans ordre spécifique.
- Pas de cloud payant, de token, de compte ni de téléversement de médias privés. Le fonctionnement final doit être local/hors ligne après installation.
- Pas d’installation sur téléphone, tablette ou PC personnels du propriétaire sans autorisation explicite.
- Ne pas fournir de fausses preuves, de résultats de métriques fabriqués, d’avis humains inventés, ni prétendre qu’un modèle est qualifié parce qu’il est détecté.
- Ne pas diffuser des médias tiers non autorisés ni supposer les droits sur les **poids** d’un modèle à partir de la licence de son code.
- Les moteurs de génération créative sont interdits avant le GO M014 et une nouvelle autorisation.

## 3. Algorithme obligatoire au démarrage (preflight)

1. Lire le README, la PR #1, `reports/consolidation/CLOTURE-PUBLICATION.md`, `docs/mission-004/CAHIER-TECHNIQUE.md` et la branche de référence **telle qu’elle existe réellement au moment de l’intervention**.
2. Inventorier branches, tags, commits, PR, workflows, artefacts, paquets, tests et modèles disponibles; consigner `base_sha`, `head_sha`, version et plateforme. Ne pas supposer que la branche initiale est encore l’état courant.
3. Trouver le dernier jalon vérifié et comparer aux prérequis de MXXX; si prérequis absent, produire `BLOCKED` et rétablir uniquement les préconditions strictement nécessaires dans une sous-phase avec preuves.
4. Définir une branche nouvelle `codex/studio-ia-mXXX-<slug>` depuis la branche de développement approuvée la plus récente; ne jamais écraser une branche homonyme contenant des commits.
5. Rejouer le socle CPU et les tests essentiels de sécurité d’export avant toute modification; sauvegarder le rapport baseline.
6. Décomposer la mission en lots cohérents et signer les contrats d’interface en documentation (versions de schéma, compatibilité, chemins).
7. Publier un commit par lot; vérifier la présence distante et les liens des tests, sans publier de média privé.
8. Exécuter les tests positifs, négatifs, stress, annulation, offline et packaging pertinents à la mission. Chaque échec doit être corrigé ou rester visible avec justification.
9. Ouvrir une PR **Draft** vers la branche de développement approuvée (pas automatiquement `main`) et conserver les anciennes PR intactes. Ne pas demander au propriétaire de cliquer Merge.
10. Produire `reports/MXXX/FINAL.md`, le manifeste de preuves, la matrice PASS/FAIL/SKIP/BLOCKED et la prochaine mission admissible.

## 4. États techniques obligatoires

**NOT_STARTED** = code absent. **IMPLEMENTED_UNVERIFIED** = code présent sans exécution réelle. **DETECTED** = outil trouvé sur disque. **COMPATIBLE** = prérequis validés. **PASS** = test réel réussi au commit exact, environnement décrit. **FAIL** = assertion échouée. **SKIP** = test non exécuté pour motif justifié. **BLOCKED** = précondition indispensable non remplie. **REGRESSION** = ancien test vert devenu rouge. Un skip ne devient jamais un pass, et un mode démo/mock ne valide pas le moteur de production.

## 5. Contrats de preuve et validation

Chaque tâche a un `task_id`, un commit, un jeu de tests et une pièce de preuve. Un rapport machine lisible contient au minimum :

```json
{
  "mission": "MXXX", "task_id": "MXXX.01", "status": "PASS",
  "tested_commit_sha": "<sha Git réel>",
  "os_arch": "<système et architecture>",
  "hardware": {"cpu": "<observé>", "gpu": "<observé ou non disponible>"},
  "engine": {"name": "<nom réel>", "version": "<version réelle>", "model_sha256": null},
  "source_sha256": "<hash si fichier fourni>",
  "output_sha256": "<hash si export réussi>",
  "tests": {"passed": 0, "failed": 0, "skipped": 0},
  "evidence_paths": ["reports/MXXX/evidence/..."],
  "limitations": [], "measured_at_utc": "<horodatage>",
  "ci_run_url": null
}
```

Les valeurs encadrées par `< >` sont des **placeholders**, jamais des données réelles. Si le champ n’est pas mesurable, mettre `null` et expliquer. GitHub Actions sans GPU ne peut pas confirmer l’exécution NN. Un screenshot Qt offscreen n’est pas un essai sur écran physique. Un paquet construit n’est pas automatiquement testé sur tous les PC.

Pour tout export vidéo : `ffprobe` métadonnées + décodage complet + dimensions + durée/PTS et cadence lorsque pertinents + audio/offset + hash source inchangé + publication de destination **sans écrasement**. Une annulation, OOM, erreur ou crash ne doit jamais produire un fichier final marqué réussi.

## 6. Gouvernance des médias et des modèles

- Source originale référencée et immuable; travail dans dossier temporaire possédé par STUDIO IA; finalisation atomique/no-clobber si possible.
- Modes RESTORE : préserver sémantique, identité visuelle et datation; les détails reconstruits par réseaux sont des **inférences plausibles**, non preuve du contenu historique réel.
- `source`, `model`, `engine`, `settings`, `timebase`, `license`, `sha256`, `hardware`, `versions` doivent figurer dans le plan figé et la provenance.
- Aucun modèle ne doit être importé en chargeant du code arbitraire depuis une archive non fiable. Hash et licence ne suffisent pas à prouver qu’un poids est sûr.
- Entrées et sorties en UTF-8 et chemins Unicode, espaces et liens symboliques traités. Politique de sous-titres, flux et couleur explicite : support testé, conversion opt-in ou refus.
- Le corpus public doit être synthétique ou sous licence autorisant l’usage exact; jamais publier de vidéos personnelles sans consentement.

## 7. Suivi et acceptation sans recontacter l’utilisateur

Codex peut arbitrer les décisions techniques **à l’intérieur** du cahier, réparer les bugs et choisir l’implémentation libre la plus simple. Il peut poursuivre les lots indépendants lorsqu’un lot facultatif est bloqué. Il doit s’arrêter à tout moment nécessitant : dépense, service en ligne, autorisation d’installation personnelle, changement de périmètre vers création, exfiltration de données, destruction ou fusion. Il peut cependant publier en branche dédiée, lancer la CI gratuite disponible et ouvrir une PR Draft.

Chaque mission se termine par : (1) ce qui fonctionne vraiment; (2) ce qui ne fonctionne pas; (3) statut de chaque test et moteur; (4) lien branche/PR/runs/artefacts; (5) instructions de reproduction; (6) déclaration de compatibilité matériel; (7) garde-fous et licences; (8) recommandation de mission suivante **seulement si ses portes sont satisfaites**.

## 8. Politique de progression

M004 à M014 = restauration haute qualité et livraison. M015 à M017 = création audiovisuelle **future**, interdite tant que M014 n’est pas acceptée et qu’une autorisation séparée n’est pas donnée. Une mission peut être techniquement plus rapide ou impossible sur le matériel disponible; sa numérotation n’est pas une mesure du nombre de jours ni une promesse de performance. Ne jamais annoncer 100 % des résultats sur toutes vidéos : préférer garanties sur scénarios et formats réellement qualifiés.

## 9. Gestion des artefacts expirants

Les artefacts GitHub Actions sont temporaires; avant expiration, les sauvegarder dans un emplacement durable vérifié (Drive privé ou release avec accord), avec hashes et provenance, sans remplacer une ancienne sauvegarde. Les fichiers PDF présents dans la conversation/Drive sont des copies de consultation ; **les Markdown publiés dans `docs/roadmap-v2/missions` sont la référence pour Codex**, sauf révision approuvée et commitée.