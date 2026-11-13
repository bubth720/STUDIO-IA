STUDIO IA peut maintenant importer une vidéo locale, appliquer un débruitage et un agrandissement classiques sur CPU, exporter en MP4/MKV puis vérifier intégralement le résultat. L'interface Qt française relie analyse, plan, progression, annulation, historique et comparaison réelle.

Les huit commits M003 sont préservés. La consolidation protège les médias et rapports contre l'écrasement, corrige les chemins/publications concurrents, le cycle SQLite/UI, la découverte FFmpeg et les installateurs. Les défauts constatés sur les runners (Qt X11, notices dpkg Ubuntu, encodage pip Windows) ont été corrigés et requalifiés.

Validation native du commit `4d42029f3bdbf260b72a6f2f0f81ed01be1265a9` : [run réussi](https://github.com/bubth720/STUDIO-IA/actions/runs/42420338324). Linux : 61 PASS / 1 SKIP ; Windows : 59 PASS / 3 SKIP ; zéro échec. E2E FFmpeg, UI gelée, extraction et relance des ZIP PASS sur les deux OS. Installateur source Windows testé dans un chemin japonais avec nouveau venv. Les SKIP concernent les moteurs neuronaux absents et, sous Windows, deux contrôles POSIX/Linux. Le paquet Bookworm glibc 2.36 reste vérifié sous Debian 12/13.

Voir [bilan et preuves](https://github.com/bubth720/STUDIO-IA/blob/codex/studio-ia-consolidation-v1/reports/consolidation/CLOTURE-PUBLICATION.md) pour les empreintes, tests et distributions. Le commit documentaire de clôture ne change pas les sources exécutées ; BUILD_INFO donne le vrai commit des binaires. Les sauvegardes initiales et le bundle complet sont vérifiés.

Limites : ALPHA CPU, FFmpeg externe ; pas de moteur neuronal qualifié, gain perceptuel universel, essai Windows 10/11 physique ou FAT/exFAT/réseau. HDR/BT.2020, >8 bits, rotation, entrelacement, SAR non carré et flux secondaires refusés explicitement. M004 fournit uniquement le cahier Real-ESRGAN / Anime4K / RIFE ; aucun développement lourd lancé.

PR conservée en brouillon. Aucune fusion dans main et aucune installation sur appareil personnel.
