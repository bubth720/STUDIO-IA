# Plan de traitement v2 — M004

Le socle Request/Plan CPU version 1 reste lisible et exécuté avec ses filtres figés.
SQLite reste à user_version=1 ; aucune base existante n'est migrée. Les nouveaux
champs de job sont additionnels. Une tâche interrompue repart de l'original, pas
d'un checkpoint d'inférence présumé.

`PlanV2` est une enveloppe immuable de JSON canonique, avec SHA-256 d'identité.
Ses propriétés retournent de nouvelles valeurs, sans partager un dictionnaire
mutable avec l'appelant. Le chargeur accepte `cpu-v1` ou `neural-ncnn` ; schémas
futurs et moteurs inconnus sont refusés. Le replay CPU v1 n'invente pas de nouveaux
filtres et ne réanalyse pas les réglages pour modifier silencieusement leur sens.

Une enveloppe neuronale contient : source canonique et SHA initial ; projection
du plan média CPU pour compatibilité de l'historique ; identité exacte du binaire
et aide observée ; manifeste modèle entier/root/identité ; table frame_id/PTS/durée
en entiers et timebase rationnelle ; budgets ; politiques d'audio/couleur/export.
Le manifeste est figé dans le plan ; changer le JSON original n'actualise pas un job.

Avant exécution, l'application revalide les modèles et reconstruit le plan depuis
les mêmes paramètres : toute différence de média, source, moteur, réglages ou
table temporelle empêche la poursuite. Le binaire doit appartenir aux deux hashes
officiels épinglés Linux/Windows, **avant même son appel d'aide**. Un plan importé
ne peut donc pas choisir un programme arbitraire en fournissant son propre hash.

Le profil initial est volontairement restreint : modèle natif animevideov3 ×2,
prétraitement neutre, CFR à PTS initiaux zéro, MP4, SDR 8 bits BT.709 limitée avec
métadonnées explicites. VFR, origine vidéo décalée, HDR, rotations, SAR non carré,
flux secondaires, MKV neuronal et autres modèles ne sont pas convertis en secret.
Le chemin CPU conserve les formats et politiques auparavant qualifiés.

Les durées sont lues du décodeur ou déduites des PTS entiers successifs ; pour la
dernière frame sans durée explicite, seul duration_ts du flux est accepté.
`duration_evidence` trace cette origine. Aucune cadence moyenne arrondie ne sert
à fabriquer une durée. Comparaison finale : même nombre de frames, égalité exacte
des PTS et durées rationnelles, en plus du décodage intégral et des contrôles AV.

Le modèle est copié dans un répertoire de job neuf puis ses octets sont hashés.
Les images extraites et traitées ont une table de provenance. L'agrandissement
NCNN remplace Lanczos ; les deux filtres scale restants ne changent pas la taille,
ils rendent explicites les conversions BT.709 limitée ↔ RGB24. Le pipeline remappe
toutes les pistes audio prises en charge depuis la source, avec leurs offsets.

Budget : estimation conservative des images/stockage, plafond de frames et tuile
bornée ; pic RAM/VRAM **non garanti** et non annoncé comme mesuré. Une seule tâche
neuronale par défaut, verrou interprocessus et groupe de processus annulable.
Un verrou laissé par un arrêt brutal bloque le redémarrage jusqu'au diagnostic,
sans suppression automatique d'un verrou potentiellement actif.

La sortie transitoire reste dans un répertoire possédé par le job, sur le système
de fichiers de destination. L'état VERIFIED_NOT_COMMITTED précède publication
atomique sans remplacement ; PASS/SUCCEEDED n'est produit qu'après publication.
L'original et une destination concurrente restent protégés.

L'aperçu utilise un segment réel court, le même modèle/tuile et les paramètres
complets. Il indique instant demandé et premier PTS source échantillonné, puis
produit source/CPU/NN au même instant local. Les images d'affichage utilisent le
comparateur existant ; aucun avis humain ou gain de qualité n'est déduit de leur
simple création. Une vraie qualification GPU et la revue temporelle restent requises.
