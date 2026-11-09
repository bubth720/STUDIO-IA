# STUDIO IA — Anti-banding CPU optionnel (11/2026)

## Fonction ajoutée

La chaîne FFmpeg sait désormais appliquer un filtre **deband** conservateur aux vidéos SDR 8 bits déjà acceptées par STUDIO IA. C'est une fonctionnalité **classique CPU** : elle n'emploie ni modèle d'IA, ni GPU, et ne recrée pas de détails perdus.

Elle peut atténuer les bandes de quantification sur les ciels, aplats et dégradés animés. Elle peut aussi lisser du grain, du texte ou des traits fins ; comparer l'original reste indispensable. Aucun gain perceptuel universel n'est revendiqué.

## Commande

```sh
studio-ia process "source.mp4" "sortie.mp4" --deband light
studio-ia process "source.mp4" "sortie-moderee.mp4" --deband moderate
```

Modes acceptés : `off` (valeur par défaut), `light`, `moderate`.

Le filtre doit être réellement disponible dans le FFmpeg local. Sinon, la validation du plan échoue explicitement avant tout export. Le mode AUTO / Préservation ainsi que le réencodage témoin ne l'activent **jamais** silencieusement.

## Interface

Dans **AVANCÉ · Personnalisé**, sélectionner **Anti-banding CPU** → Désactivé / Léger / Modéré. Le changement invalide le plan précédent ; l'utilisateur doit revérifier le plan avant de démarrer. La sélection revient sur Désactivé en quittant le profil personnalisé. La voie neuronale NCNN initiale refuse tout anti-banding CPU incorporé dans son plan afin de conserver un pipeline clairement auditable.

## Paramètres techniques

- Léger : `deband=1thr=0.012:2thr=0.012:3thr=0.012:4thr=0.012:range=8:blur=1`
- Modéré : `deband=1thr=0.020:2thr=0.020:3thr=0.020:4thr=0.020:range=12:blur=1`

Le filtre est ajouté **après** le débruitage éventuel et **avant** les corrections colorimétriques et la mise à l'échelle, afin de travailler sur les dimensions de la source. Ne pas présumer que ce placement est optimal pour tous les médias ; il reste à comparer sur un corpus réel autorisé.

## Validation

```sh
python -m pytest -q -ra tests/test_pipeline.py tests/test_gui.py
python scripts/run_e2e.py --output artifacts/e2e
```

Les tests ajoutés couvrent l'exécution FFmpeg réelle dans deux modes, la conservation du fichier original, le décodage et l'audio via le vérificateur existant, l'absence d'activation par défaut, les paramètres invalides, l'absence du filtre et les états des profils Qt.

Les tests sur des références synthétiques prouvent la **correction technique** de l'export, pas l'amélioration esthétique d'une séquence réelle. Pour cette dernière, effectuer une revue humaine sur des dégradés compressés, du texte fin et des surfaces détaillées.

## Compatibilité et sécurité

La nouvelle option est ajoutée en fin de `Request` avec `deband="off"` : les anciens plans CPU v1 sans ce champ restent chargeables. La politique de sortie sans écrasement, le contrôle intégral, les refus HDR et flux secondaires et les validations audio restent inchangés.

Pas d'ajout de dépendance ; FFmpeg/ffprobe restent externes ; aucune installation ni dépense. La branche doit être validée en CI Windows/Linux avant toute annonce de qualification multiplateforme.

Cette contribution est indépendante de la **gate GPU BLOCKED** de M004. Elle ne transforme pas un traitement CPU en restauration neuronale et n'autorise pas M005.
