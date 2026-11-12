# M004 — lots, contrats et critères

Base 24f5c211cc96d7d6956d9e7452c4dc025693caa4 ; référence du cahier 8db491635b572314744ee7afd1e3339ebd6ad85b.

| Lot | Développement / contrat | Preuve et limite |
| --- | --- | --- |
| M4.01 | Socle CPU requalifié, backend prioritaire NCNN0.2.0, alternative Video2X documentée, lock binaire/modèle | PASS préflight CPU local et deux OS, aide locale exécutée ; aucune inférence déduite de la détection |
| M4.02 | Model-manifest-v2, paire param/bin, licences séparées, hashes/snapshot, refus chemins/archives/chargeur | PASS contrôles logiciels ; droits des vrais poids inspectés BLOCKED, aucun modèle productif enregistré |
| M4.03 | Diagnostic CPU/AVX2/Vulkan physique et inférence courte conditionnelle | Diagnostic réel PASS ; compatibilité et inférence BLOCKED, vkCreateInstance=-9 |
| M4.04 | Plan v2 immuable, migration/replay CPU1, provenance et table PTS/durées rationnelles | PASS tests de lecture après fermeture, mutations et schémas futurs ; SQLite1 inchangé |
| M4.05 | Pipeline NCNN : extraction, vrai appel natif prévu par frame, audio et assemblage, vérification/publication | IMPLEMENTED_UNVERIFIED sur GPU ; transport FFmpeg/double non neuronal PASS ; E2E NN BLOCKED |
| M4.06 | Segment courant ≤3s, modèle/tuile du plan, trois images, instant source réel, comparateur Qt source/CPU/NN | Contrats/transport PASS ; aperçu NN et qualité réelle BLOCKED, aucun avis humain inventé |
| M4.07 | Une tâche intensive, arrêt de groupe, hash modèle/binaire, source protégée, disque/annulation/publication | PASS contrats et vrai sous-processus de panne ; OOM GPU réel SKIP et annulation native GPU BLOCKED |
| M4.08 | CLI et interface branchées, moteurs non qualifiés désactivés, CPU conservé, readiness séparée de la CI CPU | Tests UI/CLI et packaging CPU à leur SHA ; aucune distribution annoncée ALPHA NN qualifiée |

| Scénario | Résultat admissible actuel |
| --- | --- |
| NN01 : 8s / deux pistes / ×2 | BLOCKED pour Real-ESRGAN ; PASS du transport avec double explicitement non neuronal, jamais substitué à la preuve GPU |
| NN02 : référence HR dégradée / CPU / NN | BLOCKED pour la comparaison NN ; aucun PSNR/SSIM/VMAF neuronal publié |
| NN03 : modèle modifié après enregistrement | PASS du contrôle de stockage/hash, octets synthétiques ; pas de qualification du parseur NCNN |
| NN04 : arrêt pendant inférence et reprise originale | BLOCKED sur GPU ; PASS annulation d'un vrai processus enfant de test et absence d'export partiel, pas un checkpoint NN |

Commits par lot : `1956ba16c390443281b098146c2d5991c0230bf1` (registre/plans/hardware/audit), `3a62bb17fe544c0e0aa637a703148235f428899b` (pipeline, CLI/Qt/jobs, aperçus, pannes/harness), `000a9801f16da9a855442eab7d864384570cf5c2` (readiness sans qualification). Le commit final documentaire s'ajoute sans attribuer au nouveau SHA la compilation d'un autre commit.

Contrats signés par ce lot logiciel : manifeste2 avec loader restreint, plan2 avec enveloppe CPU1 exacte, état VERIFIED_NOT_COMMITTED puis publication sans écrasement, rapport moteur avec identité/modèle/hardware/limitations. Cela n'accorde aucune approbation juridique des poids, aucun matériel ou droit d'installation, aucune validation artistique ou porte inter-missions.

Rollback : garder la branche de consolidation CPU ou sélectionner CPU. Les bases historiques, réglages, originaux et sorties existantes n'ont pas besoin de restauration ou migration. Les nouveaux travaux restent isolés dans leur branche et leurs répertoires de job.
