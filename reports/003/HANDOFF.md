# Reprendre et publier sans perdre les commits

Destiné à un prochain agent ou poste de développement autorisé. L'utilisateur
Android peut télécharger les ZIP ; aucune installation Android n'est nécessaire
pour consulter les preuves. Un ZIP Linux ne s'exécute pas sur Android/Windows.

Le ZIP sources contient un `STUDIO-IA-M003.bundle` autonome avec l'historique complet
et la branche de mission. Ne pas le remplacer par une recréation manuelle des fichiers.

```sh
git bundle verify STUDIO-IA-M003.bundle
git clone -b codex/studio-ia-m003-first-verifiable-build STUDIO-IA-M003.bundle STUDIO-IA-reprise
cd STUDIO-IA-reprise
git remote set-url origin https://github.com/bubth720/STUDIO-IA.git
git fetch origin
git status --short
git log --oneline --all --max-count=15
```

Comparer le nouveau main distant avec la base du dossier. Si d'autres travaux
sont arrivés, les préserver et les auditer avant d'adapter la branche. Si une
branche homonyme existe, ne pas la forcer ; créer un nom avec suffixe ou intégrer
prudemment ses changements. Les commits du bundle descendent du main initial.

Une fois les droits Contents/Workflows écriture disponibles et la branche sûre :

```sh
git push -u origin codex/studio-ia-m003-first-verifiable-build
git ls-remote origin refs/heads/codex/studio-ia-m003-first-verifiable-build refs/heads/main
gh pr create --draft --base main --head codex/studio-ia-m003-first-verifiable-build \
  --title "M003 - STUDIO IA first verifiable build (CPU + GUI + CI)" \
  --body-file reports/003/PULL_REQUEST.md
```

Ne pas exécuter de merge ni d'auto-merge. Les workflows push doivent alors lancer
Ubuntu/Windows. Corriger les échecs réels, télécharger et vérifier les artefacts,
ajouter les URLs/numéros/SHAs des runs et mettre à jour le rapport avant de demander
une validation finale. Conserver les limites/anciens résultats comme historiques.

Si l'on importe dans un checkout existant, utiliser `git fetch CHEMIN_DU_BUNDLE`
vers une **nouvelle branche non conflictuelle** ; ne pas écraser les fichiers ou
modifications non commitées. Aucun token ne doit être copié dans le dépôt ou le chat.
