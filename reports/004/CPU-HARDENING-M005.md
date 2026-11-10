# Compléments M004 indépendants du GPU — 10 novembre 2026

Deux défauts vérifiables sont corrigés sans modifier le moteur neuronal :

1. L'ajout au registre faisait une lecture puis un remplacement atomique, sans
   protéger l'ensemble de la transaction. Deux processus pouvaient perdre un ajout.
   Un verrou OS borné couvre désormais lecture, validation et publication. Le crash
   libère le verrou ; le fichier marqueur n'est jamais supprimé. L'historique, les
   identifiants et les hashes existants restent conservés. Un registre corrompu,
   lié ou mal typé est refusé sans réécriture. Aucun schéma de base n'est migré.
2. `load_plan([])` et les requêtes héritées mal typées pouvaient lever AttributeError.
   Ils produisent maintenant StudioError, comme les versions flottantes et les
   données JSON non finies. Les enveloppes CPU historiques valides gardent les
   mêmes filtres et réglages.

Les tests démarrent des processus réels concurrents, arrêtent uniquement leur
propre enfant pour vérifier la libération du verrou, et contrôlent les octets du
registre après les erreurs. Les poids synthétiques des fixtures vérifient uniquement
le stockage ; ils ne sont jamais présentés comme un modèle Real-ESRGAN.

**M004 demeure BLOCKED** : ni inférence réelle, ni droit des poids établi, ni GPU
qualifié. Les étapes image/vidéo, la qualité humaine, OOM et VRAM neuronale restent
à exécuter sur matériel compatible autorisé. La PR #3 et ses preuves sont intactes.
