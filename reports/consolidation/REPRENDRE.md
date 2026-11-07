# Reprise sûre par un agent disposant de l'écriture GitHub

Le bundle consolidé inclut les huit commits M003 intacts et tous les nouveaux
commits. Aucun besoin de recopier manuellement le code ou de réécrire l'historique.

```sh
git bundle verify STUDIO-IA-consolidation.bundle
git clone -b codex/studio-ia-consolidation-v1 STUDIO-IA-consolidation.bundle STUDIO-IA-reprise
cd STUDIO-IA-reprise
git remote set-url origin https://github.com/bubth720/STUDIO-IA.git
git fetch origin
git status --short
git log --oneline --all --max-count=20
```

Vérifier la connexion Codex/GitHub en écriture effective sur STUDIO-IA, avec
Contents et Workflows écriture. Le compte propriétaire ne suffit pas si le jeton
d'intégration est limité. Utiliser les paramètres de connexion/environnement ;
aucun jeton dans le chat, les fichiers ou les commits. La reconnexion déclarée
durant cette session n'a pas supprimé les 403 observés.

Préserver tout travail distant nouveau et toute branche homonyme. Pas de force push.
Après audit et avec une branche sûre :

```sh
git push -u origin codex/studio-ia-consolidation-v1
git ls-remote origin refs/heads/main refs/heads/codex/studio-ia-consolidation-v1
gh pr create --draft --base main --head codex/studio-ia-consolidation-v1 \
  --title "STUDIO IA — consolidation CPU 0.3.0a2 et préparation M004" \
  --body-file reports/consolidation/PULL_REQUEST.md
```

Laisser la CI Windows/Linux effectuer de vrais exports et tests de paquet.
Corriger les échecs constatés, publier les preuves et les liens réels. Ne pas
fusionner. L'accord sur les travaux de consolidation n'autorise ni installation
personnelle ni développement lourd de M004.

Le build Linux qualifié provient de f36fa05481c488558db258b2723cd3d51653e919 ;
BUILD_INFO et les rapports indiquent ses propriétés. Les mises à jour de rapports
de clôture ne changent pas le code applicatif testé. Voir BILAN-FINAL.md.
