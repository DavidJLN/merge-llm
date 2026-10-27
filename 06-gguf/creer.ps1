# Crée dans Ollama un modèle <nom>:<quantification> par fichier GGUF.
# Les GGUF restent dans WSL (~/models/gguf) : Ollama les lit via \\wsl.localhost
# et en copie le contenu dans son propre stockage.
#
# Lancement :
#   .\creer.ps1                       # merge DARE v3 -> prof-json:f16, :q8_0, :q5_k_m, :q4_k_m
#   .\creer.ps1 ab f16,Q8_0           # LoRA AB mélangé -> merge-or-mix:f16, :q8_0
param(
    [string]$modele = "dare",
    [string[]]$quantifs = @("f16", "Q8_0", "Q5_K_M", "Q4_K_M")
)
# Lancé avec powershell -File, « f16,Q8_0 » arrive en une seule chaîne.
$quantifs = $quantifs -split ","
$noms = @{ "dare" = "prof-json"; "ab" = "merge-or-mix" }
$nom = $noms[$modele]
if (-not $nom) { throw "Modèle inconnu : $modele (dare ou ab)" }
$dossierGguf = "\\wsl.localhost\Ubuntu\home\david\models\gguf"
$modelfile = Get-Content "$PSScriptRoot\Modelfile" -Raw

foreach ($q in $quantifs) {
    $temporaire = New-TemporaryFile
    # UTF-8 sans BOM : Set-Content -Encoding utf8 en ajoute un sous PowerShell 5.1.
    $contenu = $modelfile -replace "(?m)^FROM .*$", "FROM $dossierGguf\$modele-$q.gguf"
    [IO.File]::WriteAllText($temporaire, $contenu, (New-Object Text.UTF8Encoding $false))
    Write-Output "=== ${nom}:$($q.ToLower())"
    ollama create "${nom}:$($q.ToLower())" -f $temporaire
    Remove-Item $temporaire
}
ollama list
