# Diagnostics CPU temporels, mouvement et audio

Le scanner décode une seule fois le plan d'analyse. Un observateur calcule les
translations SAD sur deux plans 16×16, avec une même zone centrale 12×12 pour tous
les décalages. Les transitions sont exclues des agrégats. Un résultat ambigu reste
inconnu. Les différences après alignement et le biais de luminance ne sont ni une
évaluation neuronale, ni une preuve de ghosting, ni une correction automatique.

L'audit audio observe tous les paquets jusqu'à EOF dans un budget de 40 000.
Il conserve les timebases rationnelles, `start_pts`, la fin des paquets, langues,
canaux, fréquences et métadonnées de délai du codec. Il distingue le début déclaré
du premier paquet (priming AAC possible). Une valeur absente reste inconnue.
La comparaison de remux exige mêmes PTS vidéo, nombre de pistes, paramètres,
langues et hash de la séquence des données audio ; offsets et fins sont comparés
avec une tolérance explicite de 50 ms. Ce protocole mesure les conteneurs/paquets,
sans prétendre mesurer une synchronisation labiale perceptuelle.

```bash
python -m studio_ia.cli temporal-audit source.mkv --motion --audio --json nouveau-rapport.json
python -m studio_ia.cli interpolation-plan source.mp4 --x2 --cut 100
python scripts/run_temporal_checks.py --output artifacts/temporal
python quality/temporal_flicker.py source.mp4
```

Le script génère et décode réellement un témoin NON_NEURAL_REPEAT_CONTROL :
200 images deviennent 400 répétitions à 50 fps, durée 8 s ; tous les hashes du
plan d'analyse répété doivent correspondre aux images source. Ce témoin ne satisfait
pas AC-005-01 et ne doit jamais être rebaptisé N05-01/RIFE.

Il mesure aussi 750 et 4 500 images (30 s / 3 min) dans des processus distincts.
Les pics RSS de Python et des enfants sont séparés ; sous Windows, le pic des
enfants reste inconnu si non collecté. Ces très petites fixtures ne prédisent pas
les performances HD/4K. Les résultats d'une source sale restent des essais de
développement ; seules les preuves au SHA propre et les collectes CI qualifient
la livraison. Le panorama texturé du corpus produit un faux positif conservateur,
conservé dans cuts.json ; les seuils nécessitent calibration ou correction manuelle.
