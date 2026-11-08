# STUDIO IA — Programme directeur M004 à M017

**Programme conçu le 8 novembre 2026.** Cette feuille de route est **préparée, pas exécutée**. Les statuts de développement doivent être récupérés des commits, PR, tests et matériels réellement qualifiés au moment de chaque mission.

## État exact de référence

- Branche existante : `codex/studio-ia-consolidation-v1` ; PR `#1` en brouillon, **aucune fusion dans main**.
- Source stabilisée : `0.3.0a2` ALPHA CPU ; FFmpeg import/débruitage/Lanczos/couleurs/audio/GUI/annulation/historique réellement testés en CI sur Windows Server 2022 et Ubuntu 24.04.
- Moteurs neuronaux non exécutés : Video2X/Real-ESRGAN/Anime4K/RIFE restent non qualifiés.
- Artefacts CI précédents sauvegardés indépendamment, liens GitHub Actions temporaires.
- Une vraie restauration professionnelle exige des tests de fidélité, stabilité temporelle et colorimétrie, pas seulement un upscale en pixels.

## Mode d’emploi : une instruction suffit

Ouvrir `CODEX-START-HERE.md` ou dire : **« Codex, exécute la Mission MXXX du dépôt bubth720/STUDIO-IA selon docs/roadmap-v2. Suis le protocole; code, teste, publie branche + PR Draft, ne fusionne pas. »**

L’ordre des missions peut adapter les phases indépendantes, **sans court-circuiter les portes bloquantes**. M015–M017 sont un futur studio créatif uniquement après une véritable version RESTORE stable (M014) et ton feu vert explicite. Les tests peuvent échouer : mieux vaut conserver un statut BLOCKED qu’inventer une réussite.

## Ordre et résultats ciblés

| Mission | Titre | Gate de départ | Cible de sortie |
|---|---|---|---|
| [M004](missions/M004.md) | Moteurs de restauration neuronale | M003 0.3.0a2 publié + CI CPU Windows/Linux verte + archive conservée | Un moteur Real-ESRGAN ou équivalent NCNN/Vulkan opérationnel et qualifié; Anime4K précisément identifié si disponible. |
| [M005](missions/M005.md) | Cohérence temporelle et interpolation | M004 NN E2E sur matériel compatible + Plan v2 | RIFE x2 validé sur matériel adéquat avec cadence, PTS et audio corrects. |
| [M006](missions/M006.md) | Restauration des dégradations réelles | M005 validée ou compatibilité temporelle de chaque filtre documentée | Boîte à outils réversible : denoise, deblock, deblur conservative, deband, scratch/dust optionnels. |
| [M007](missions/M007.md) | Profils photoréalistes et animation | M004–M006 selon capacités réellement disponibles | Profil prises de vues réelles préserve géométrie du visage/peau/objets. |
| [M008](missions/M008.md) | Couleurs professionnelles et formats complexes | Socle M003 conservé, au moins regressions couleur et audio vertes | Chaîne colorimétrique traçable : primaries/transfer/matrix/range, bit depth et métadonnées HDR. |
| [M009](missions/M009.md) | Diagnostic automatique et planificateur explicable | M006/M007 profils et métriques consolidés; M008 selon formats | Analyse par scènes avec indices noise/blur/blocking/flicker/codec/color/motion. |
| [M010](missions/M010.md) | Performances, ressources et traitements longs | M004 vrai moteur NN au moins sur un environnement | Gestion des tâches prioritaires, limites RAM/VRAM/disque et concurrence explicite. |
| [M011](missions/M011.md) | Expérience studio et production par lots | M009 planificateur stable; M010 ressources connues | A/B temporel synchronisé, zoom et comparaison zones sensibles. |
| [M012](missions/M012.md) | Sécurité, confidentialité et distribution fiable | M003 consolidée + modules M004–M011 effectivement livrés | Contrôle des entrées fichiers/modèles/archives et absence de réseau durant traitement. |
| [M013](missions/M013.md) | Laboratoire de qualité et validation terrain | M004–M012 fonctionnalités candidates stabilisées | Corpus de vidéos autorisées et non seulement synthétiques. |
| [M014](missions/M014.md) | Version 1.0 et validation finale | M013 audit GO et M012 sécurité/licences validés | RC versionnée, builds figés, tests E2E et QA ré-exécutables. |
| [M015](missions/M015.md) | Studio créatif : montage non destructif | M014 restauration stable GO + feu vert explicite pour création | Timeline multi-clips, cuts, trims, transitions classiques, titres et audio contrôlé. |
| [M016](missions/M016.md) | Studio créatif : transformations contrôlées | M015 montage non destructif validé et M014 noyau stable | Masquage/blur/effets de couleur sélectifs et tracking sur zones contrôlées. |
| [M017](missions/M017.md) | Studio créatif : génération de séquences locale | M016 et M014 GO + accord explicite distinct pour modèles génératifs | Pipeline expérimental text/image-to-video local, modèles possédant droits d’usage documentés. |

## Chemin critique et jalons

1. **M004–M005** : preuve d’inférence NN et stabilité temporelle, vidéo complète, audio/PTS.
2. **M006–M009** : défauts réels, matières photoréalistes et anime, formats couleur, AUTO explicable.
3. **M010–M012** : RAM/VRAM et jobs longs, workflow batch, sécurité et packaging offline.
4. **M013–M014** : corpus autorisés, comparaison visuelle, campagne bêta, go/no-go et éventuelle 1.0.
5. **M015–M017** : seulement après M014 et accord : montage, retouches contrôlées, génération locale expérimentale.

## Liens utiles du dépôt

- [Protocole commun](EXECUTION_PROTOCOL.md)
- [Instructions courtes Codex](CODEX-START-HERE.md)
- [Ancien cahier M004, préservé](../mission-004/CAHIER-TECHNIQUE.md)
- [Bilan consolidation](../../reports/consolidation/CLOTURE-PUBLICATION.md)

## Choix du support documentaire

Les **Markdown** de cette branche sont le texte source pour Codex, consultables directement depuis GitHub. Les PDF individuels et le volume intégral sont produits à partir des **mêmes Markdown**, afin de faciliter lecture et partage. Ne pas recopier à la main un document long dans Codex : indique le fichier à lire dans le dépôt.

## Glossaire des statuts

- **Documenté** : cahier rédigé; zéro preuve de développement impliquée.
- **Implémenté** : code existe mais peut être non qualifié.
- **Validé CPU** : test réel CPU réussi sur la plateforme décrite.
- **Validé NN** : véritable vidéo traitée par modèle qualifié sur matériel réellement compatible.
- **Stable** : release uniquement après toutes les portes et décision de publication explicite.