$ErrorActionPreference = 'Stop'
$studioRoot = $PSScriptRoot
& py -3.12 -m venv (Join-Path $studioRoot '.venv')
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 et le lanceur py sont nécessaires.' }
$studioPython = Join-Path $studioRoot '.venv\Scripts\python.exe'
& $studioPython -m pip install pip==26.3
if ($LASTEXITCODE -ne 0) { throw 'Installation de pip impossible.' }
& $studioPython -m pip install ('{0}[gui]' -f $studioRoot)
if ($LASTEXITCODE -ne 0) { throw 'Installation de STUDIO IA impossible.' }
Write-Host 'Installation locale terminée. Lancez Lancer-sources.ps1.'
