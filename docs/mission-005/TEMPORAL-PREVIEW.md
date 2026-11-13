# Inspection temporelle CPU

Dans l'application, importer un média puis choisir **Inspection temporelle**.
La source est affichée ; si un export de cette session existe, il sert de référence.
Une paire de fichiers existants peut aussi être ouverte explicitement :

```bash
python -m studio_ia.cli temporal-preview source.mp4 --reference export.mp4
# Distribution extraite :
./STUDIO-IA --cli temporal-preview source.mp4 --reference export.mp4
# Windows : STUDIO-IA.exe --cli temporal-preview source.mp4 --reference export.mp4
```

Déplacer le curseur ou indiquer un numéro d'image. Les deux côtés représentent
le même instant demandé en PTS absolu ; chaque PTS effectivement décodé est affiché.
Pour des cadences différentes, l'image présentée à cet instant est sélectionnée,
sans prétendre que ses timestamps sont nécessairement égaux. Des origines sans
recouvrement sont refusées. Le bouton de transition saute aux candidats détectés ;
la loupe ×1–×4 et la séparation permettent d'inspecter les défauts.

Le composant réutilise `Comparison` de la GUI historique. Un seul worker est actif,
une seule demande est en attente (les anciennes positions sont regroupées), un
délai de 60 ms réduit les décodages redondants et le cache garde six paires au plus.
Les PNG sont bornés à 640×360 ; il s'agit d'une loupe d'aperçu, pas d'un décodage
natif HD/4K. Le chargement et les sous-processus restent hors du thread GUI ;
les pixmaps sont créés uniquement dans le thread GUI. La fermeture annule le travail
et attend son arrêt par les événements Qt.

La chronologie initiale est hashée ; les seeks vérifient taille/mtime avant et après
le décodage et le PTS effectivement extrait. Toute modification détectée exige de
recharger. Il n'y a aucune écriture dans les médias. Le rendu sert à l'inspection,
sans calibration colorimétrique d'écran ni mesure perceptuelle automatique.

Le QTest utilise réellement FFmpeg sur une source à 25 fps et son témoin répété à
50 fps : 30 changements rapides, dernier PTS identique 6 s (images 150/300), timer
GUI actif, cache limité à six entrées, saut annulable et hash source inchangé.
Les captures portent sur des sources synthétiques, jamais sur des médias privés.
Aucun aperçu RIFE n'est présenté, aucun moteur neuronal n'est activé.
