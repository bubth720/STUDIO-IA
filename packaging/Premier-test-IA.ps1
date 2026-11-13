# STUDIO IA - premier test IA reel sur ce PC (Windows).
# Aucun telechargement sans votre accord explicite. Empreintes SHA-256 verifiees.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $here 'STUDIO-IA.exe'
$work = Join-Path $env:LOCALAPPDATA 'STUDIO-IA\modeles-ia'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$reports = Join-Path $env:LOCALAPPDATA "STUDIO-IA\tests-ia\$stamp"
$engineUrl = 'https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases/download/v0.2.0/realesrgan-ncnn-vulkan-v0.2.0-windows.zip'
$engineSha = '1bbbdb12d470af80b035c773682e144c6c2f6ece9210832a289af0a48ce3fa9a'
$binarySha = '07e49f7cbb4ede01ae4dd4c399d3a7e5846e3d2085c3128eff881e55cb7b1a0c'
$modelsUrl = 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip'

Write-Host ''
Write-Host 'STUDIO IA - premier test IA reel' -ForegroundColor Yellow
Write-Host 'Ce script va :'
Write-Host '  1. analyser le materiel de ce PC (processeur, memoire, carte graphique) ;'
Write-Host '  2. telecharger 2 archives officielles Real-ESRGAN depuis GitHub (environ 50 Mo) :'
Write-Host "     $engineUrl"
Write-Host "     $modelsUrl"
Write-Host "  3. les placer dans $work, verifier leurs empreintes, puis lancer"
Write-Host '     une courte inference IA sur une petite image de test (32 x 32 pixels).'
Write-Host 'Licences : moteur MIT, poids BSD-3-Clause (projet Real-ESRGAN).'
Write-Host ''

New-Item -ItemType Directory -Force -Path $reports | Out-Null
& $exe --machine --output (Join-Path $reports 'materiel.json')
if ($LASTEXITCODE -ne 0) { Write-Host 'Analyse materielle impossible.' -ForegroundColor Red; exit 1 }

$answer = Read-Host 'Autorisez-vous ce telechargement ? Tapez OUI pour accepter'
if ($answer -ne 'OUI') { Write-Host 'Aucun telechargement. Fin.'; exit 0 }

New-Item -ItemType Directory -Force -Path $work | Out-Null
$engineZip = Join-Path $work 'moteur-v0.2.0-windows.zip'
$modelsZip = Join-Path $work 'modeles-20220424-windows.zip'
if (-not (Test-Path $engineZip)) { Invoke-WebRequest -Uri $engineUrl -OutFile $engineZip -UseBasicParsing }
if (-not (Test-Path $modelsZip)) { Invoke-WebRequest -Uri $modelsUrl -OutFile $modelsZip -UseBasicParsing }
$got = (Get-FileHash -Algorithm SHA256 $engineZip).Hash.ToLower()
if ($got -ne $engineSha) { Write-Host "Empreinte du moteur incorrecte ($got) : arret." -ForegroundColor Red; exit 1 }
Write-Host "Archive des modeles : SHA-256 $((Get-FileHash -Algorithm SHA256 $modelsZip).Hash.ToLower())"
Write-Host '(chaque fichier de modele est verifie individuellement par les manifestes)'

$engineDir = Join-Path $work 'moteur'
$modelsDir = Join-Path $work 'paquet-modeles'
if (-not (Test-Path $engineDir)) { Expand-Archive -Path $engineZip -DestinationPath $engineDir }
if (-not (Test-Path $modelsDir)) { Expand-Archive -Path $modelsZip -DestinationPath $modelsDir }
$binary = Get-ChildItem -Path $engineDir -Recurse -Filter 'realesrgan-ncnn-vulkan.exe' | Select-Object -First 1
if (-not $binary) { Write-Host 'Moteur introuvable dans l archive.' -ForegroundColor Red; exit 1 }
if ((Get-FileHash -Algorithm SHA256 $binary.FullName).Hash.ToLower() -ne $binarySha) {
  Write-Host 'Binaire du moteur non conforme : arret.' -ForegroundColor Red; exit 1
}
$weights = Get-ChildItem -Path $modelsDir -Recurse -Filter 'realesr-animevideov3-x2.bin' | Select-Object -First 1
if (-not $weights) { Write-Host 'Modeles introuvables dans l archive.' -ForegroundColor Red; exit 1 }
$models = $weights.Directory.FullName
Copy-Item -Path (Join-Path $here 'manifests\*.json') -Destination $models -Force

$failed = $false
foreach ($name in @('realesr-animevideov3-x2', 'realesrgan-x4plus')) {
  $manifest = Join-Path $models "$name.json"
  Write-Host ''
  Write-Host "=== Modele $name ===" -ForegroundColor Yellow
  & $exe --cli model-check $manifest $models --json (Join-Path $reports "$name-verification.json")
  if ($LASTEXITCODE -ne 0) { $failed = $true; continue }
  & $exe --cli neural-test --manifest $manifest --model-root $models --binary $binary.FullName --output (Join-Path $reports "$name-essai") --json (Join-Path $reports "$name-essai.json")
  if ($LASTEXITCODE -eq 0) { Write-Host "$name : inference courte REUSSIE sur ce PC" -ForegroundColor Green }
  elseif ($LASTEXITCODE -eq 2) { Write-Host "$name : BLOQUE (voir le rapport : GPU Vulkan absent ou non compatible)" -ForegroundColor Red; $failed = $true }
  else { Write-Host "$name : ERREUR (voir le rapport)" -ForegroundColor Red; $failed = $true }
}
Write-Host ''
Write-Host "Rapports : $reports" -ForegroundColor Yellow
Write-Host 'Envoyez ce dossier (ou son contenu) pour analyse. Aucune donnee n est envoyee automatiquement.'
Start-Process explorer.exe $reports
if ($failed) { exit 2 }
