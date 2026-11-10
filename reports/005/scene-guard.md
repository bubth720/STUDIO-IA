# Protection des transitions — lot CPU M005.02/.04

FFmpeg `scdet` mesure la différence moyenne absolue et son score de scène sur un
plan d'analyse 32×32. Le seuil est réglable dans ]0,100] (défaut 10). Les scores
ne sont pas des probabilités de coupe sémantique. Chaque score doit correspondre
exactement à l'index et au PTS de la chronologie décodée.

Une image différente entre deux images d'analyse identiques, avec différences
adjacentes élevées, est marquée `FLASH_OR_SINGLE_FRAME_INSERT` aux deux bords.
Une rampe de luminance monotone devient un candidat de transition graduelle,
sans prétendre prouver un fondu. Les limites imposées et exclusions manuelles
sont explicites et consignées. Le scan ne modifie aucun média.

Le scheduler fournit `HOLD_SOURCE` à chaque paire traversant une limite et
`HOLD_LAST` sur la dernière demi-tranche. Chaque intervalle neutralisé est journalisé
avec les deux index et des bornes rationnelles. Les demandes RIFE à l'intérieur
restent non exécutables. La garde fonctionne sur les limites observées ; une coupe
non détectée reste un risque, à corriger par seuil ou limite manuelle.

Vérifications réelles : vidéo lossless 8 s / 25 fps, coupe image 100 ; flash image
20 et retour 21 ; split-screen stationnaire ; fondu progressif ; cinq cadences
rationnelles ; EOF MKV et préfixe incomplet. Les tests démarrent FFmpeg/ffprobe réels.
Les limites du détecteur sur des panoramiques et changements de split-screen
seront quantifiées dans `cuts.json`, sans extrapolation au cinéma réel.

**Limites** : aucune image RIFE, aucun masque d'occlusion neuronal, aucune validation
sur visages, mains ou rotation rapide. La neutralisation du planning ne prouve pas
la qualité d'un moteur absent. M005.03 et l'acceptation M005 restent BLOCKED.
