# Consolidation de la Mission 003 et préparation de la Mission 004

Base sauvegardée : `61dc911ac105be2fb8b7259114a6516e125466c6`, huit commits M003.
Main distante : `61fe67ebb908da856964e88200e1220f83fc2bb8`, à préserver.
Branche de consolidation : `codex/studio-ia-consolidation-v1`.

Sauvegarde intégrale locale : 439 235 362 octets, 12 021 fichiers ordinaires relus.
SHA-256 : `6d9db1f47b31af99116184fd63da6f8a693a01d636ddbf9e3ee71b8a1405d94a`.
Les dix livrables initiaux ont tous passé leur contrôle d'empreinte ; tous les ZIP
ont passé leur CRC et le bundle est autonome/intègre. Voir backup-verification.json.
L'archive contient aussi le venv et le PDF d'origine : sauvegarde locale, pas un
fichier à pousser intégralement sur GitHub. Les sources et preuves synthétiques
ont leurs archives séparées.

Diagnostic GitHub : compte propriétaire accessible en lecture, installation
`167943396`, dépôt sélectionné ; création de ref et push refusés HTTP 403.
L'en-tête serveur demande `contents=write` et, pour les workflows, `workflows=write`.
L'utilisateur a confirmé la mise à jour/reconnexion ; les premières nouvelles
requêtes sont encore refusées. Aucun changement de main ni contournement.
Les résultats finaux de publication seront consignés seulement après preuve.

Les trois régressions initiales ont été reproduites (3 FAIL avant correction) :
destination ajoutée comme symlink après prévalidation, rapport PASS écrit avant
publication effective, et nettoyage refusé transformant un export validé en erreur.
Les correctifs et tests ciblés sont ajoutés ; qualification complète en cours.

Autres consolidations : JSON atomique UTF-8, rapports CLI qui refusent d'écraser
les médias/fichiers existants, chemins canoniques figés, fermetures SQLite,
invalidation du plan lors du chargement d'historique, chemins FFmpeg simplifiés,
scripts d'installation source, lanceurs portables et contrôle du ZIP livré.

La version `0.3.0a2` reste CPU. Aucun poids de modèle n'est téléchargé/exécuté.
Le cahier technique M004 sera documentaire ; pas de développement neuronal lourd.
Qualification Bookworm/Windows et bilan final : voir les rapports complémentaires
qui seront ajoutés après leurs exécutions réelles, sans inventer de résultat.
