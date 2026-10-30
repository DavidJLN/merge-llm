# Crée dans Ollama le modèle ministral-<nom>:q8_0 à partir de
# ~/models/gguf/ministral-<nom>-Q8_0.gguf (produit par convertir.sh).
# Ollama lit le GGUF via \\wsl.localhost et en copie le contenu dans son propre
# stockage, sur C: : supprimer le modèle (ollama rm) dès qu'il est évalué.
#
# Pas de TEMPLATE : l'évaluation envoie des prompts déjà mis en forme (mode raw).
#
# Lancement :
#   .\creer.ps1 test-linear
param([Parameter(Mandatory)][string]$nom)
$gguf = "\\wsl.localhost\Ubuntu\home\david\models\gguf\ministral-$nom-Q8_0.gguf"
if (-not (Test-Path $gguf)) { throw "GGUF introuvable : $gguf" }
$temporaire = New-TemporaryFile
# UTF-8 sans BOM : Set-Content -Encoding utf8 en ajoute un sous PowerShell 5.1.
[IO.File]::WriteAllText($temporaire, "FROM $gguf`n", (New-Object Text.UTF8Encoding $false))
ollama create "ministral-${nom}:q8_0" -f $temporaire
$code = $LASTEXITCODE
Remove-Item $temporaire
# Sans ce throw, le script réussit même si l'import a échoué (disque C: plein,
# par exemple), et un appelant qui supprime le GGUF ensuite le perd.
if ($code -ne 0) { throw "échec de ollama create (code $code)" }
ollama list
