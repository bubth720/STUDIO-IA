# STUDIO IA — consolidation CPU 0.3.0a2 et préparation M004

Corps préparé ; PR non créée, car l'écriture GitHub reste refusée HTTP 403.
Base : main `61fe67ebb908da856964e88200e1220f83fc2bb8`.
Head : `codex/studio-ia-consolidation-v1`, descendant des huit commits M003.
Ouvrir en **brouillon**, sans auto-merge ni fusion sans autorisation.

Cette consolidation corrige la redirection de destination par symlink, les rapports
de succès prématurés, la gestion des erreurs de nettoyage, l'écrasement possible
des médias par un rapport CLI et l'invalidation des plans de l'historique. Elle
ajoute JSON UTF-8 atomique, découverte simplifiée de FFmpeg/ffprobe, lanceurs et
installation source, finalisation sans remplacement et build Linux glibc 2.36.

Validation réelle : 54 tests PASS, 1 SKIP neuronal ; pipeline FFmpeg complet ;
paquet extrait et 578 hashes contrôlés ; exécutable gelé testé sans réseau sur
Debian 12 et sur X11 virtuel Debian 13 ; installation source dans un chemin
Unicode puis traitement graphique réel. Main inchangée, sauvegardes vérifiées.

Les trois régressions initiales ont été reproduites avant correction. Les logs
d'échecs de construction et les résultats corrigés restent dans les preuves.
La CI versionnée prévoit Linux/Windows natif et le contrôle du ZIP extrait ;
**aucun run distant ou exécutable Windows n'est encore qualifié**.

M004 : cahier technique six pages, sources officielles, corpus/acceptation et
schéma futur de modèles. Pas de moteur neuronal installé, pas de poids téléchargé,
pas de développement lourd lancé. Les variantes Anime4K CNN/classiques sont distinguées.

Risques/limites : CPU classique, formats complexes refusés comme documenté, pas
d'essai sur appareils personnels ; FAT/exFAT/réseau non qualifiés ; FFmpeg externe.
Licences dynamiques et notices incluses, aucune redistribution de modèles.

À compléter après publication : URL/SHA du head distant, runs Linux/Windows,
artefacts et bilan natif Windows. Ne pas remplacer ces champs par des liens fictifs.
