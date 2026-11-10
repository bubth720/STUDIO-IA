# Contrat temporel M005 (préparation CPU)

`temporal.FrameStamp` et `FrameTimeline` de la PR #5 restent les contrats de base.
`FrameRecord` en donne une vue immuable sérialisable : index, PTS entier, timebase
numérateur/dénominateur, durée entière ou inconnue, keyframe, scène et hash optionnel.
Les hashes des scènes portent sur le plan GRAY8 32×32 avec padding, jamais sur le
fichier original ni sur sa résolution entière. Le SHA source est distinct.

Le temps présenté vaut exactement `pts * Fraction(time_base_num, time_base_den)`.
Le DTS commande le décodage (notamment avec B-frames) ; le PTS commande l'affichage.
Les diagnostics lisent le `best_effort_timestamp` décodé, sans reconstruire une
chronologie à partir de `fps` flottants, du DTS ou du seul numéro d'image.
Une origine positive ou négative est conservée. Un delta différent ne prouve pas
à lui seul une VFR : l'arrondi de timebase d'un conteneur peut aussi varier.

Les durées internes proviennent du PTS suivant. La dernière durée doit être
rapportée par le décodeur ; son absence reste inconnue. Une couverture complète
nécessite un total déclaré concordant ou un EOF borné vérifié par les compteurs
de paquets et de frames. Atteindre le budget ne démontre jamais un EOF.
Le diagnostic préfixe historique reste utilisable et distinct du scan complet.

Le plan ×2 exige une demande explicite et une source CFR complètement observée.
Il garde chaque image source à son PTS, ajoute une demande de milieu d'intervalle
seulement à l'intérieur d'un plan, répète la source aux transitions et maintient
la dernière image pendant la dernière demi-tranche. Convention N → 2N ; durée
inchangée. Une source VFR ou une durée finale inconnue entraîne un refus explicite.
Ce plan ne charge aucun modèle et ne produit aucune image neuronale : M004 et RIFE
restent BLOCKED. Aucun changement automatique vers 60 fps.

Commandes depuis les sources installées :

```bash
python -m studio_ia.temporal source.mp4 --max-frames 3000
python -m studio_ia.scene_detect source.mp4 --threshold 10 --cut 100
python -m studio_ia.interpolate source.mp4 --explicit-x2-plan
```

Les sorties JSON vont sur stdout. `--ignore-cut INDEX` corrige explicitement un
faux positif du détecteur ; chaque exclusion reste dans le rapport. Une exclusion
constitue un choix opérateur, sans garantie sémantique du détecteur.
