# Preuves de qualification native GitHub

Le [bilan de clôture](../CLOTURE-PUBLICATION.md) identifie le commit et le run
correspondant. Chaque sous-dossier contient le JUnit complet, le résultat E2E,
le manifeste du build et la vérification du ZIP extrait. Les captures proviennent
de l'exécutable gelé après un export réellement effectué, avec clics QTest.

Linux utilise X11 virtuel (`xcb`), Windows le plugin Qt `windows` sur le runner
Windows Server 2022 x64. Ce sont des essais natifs gérés, sans appareil personnel
ou écran physique. Le test Windows d'installation source utilise un nouveau venv
dans un chemin avec espaces et caractères japonais ; son module installé est tracé.

Les journaux `*-failure.log` conservent les défauts constatés avant correction :
Qt X11 incomplet, annotation de diversion dpkg et encodage pip Windows. Ils ne
sont pas présentés comme des succès. L'historique Git conserve les corrections.
Les SKIP et leurs motifs restent dans les fichiers JUnit, sans conversion en PASS.

Le formulaire comprimé visible dans `windows-before-small-screen.png` a ensuite
été corrigé par défilement. Le test de géométrie à 1024×720 passe sur les deux
runners ; comparer avec `Windows/gui-success.png`. Le dossier Bookworm contient
la qualification du même commit sous glibc 2.36 sans réseau, puis son exécution
sur Debian 13 avec X11 virtuel.

L'archive complète de preuves contient aussi commandes, logs, fichiers synthétiques
et vérifications FFmpeg/ffprobe. Aucun média utilisateur ou poids neuronal inclus.
Les archives antérieures et leurs empreintes sont conservées séparément.
