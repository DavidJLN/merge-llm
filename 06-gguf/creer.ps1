# Crée dans Ollama un modèle prof-json:<quantification> par fichier GGUF.
# Les GGUF restent dans WSL (~/models/gguf) : Ollama les lit via \\wsl.localhost
# et en copie le contenu dans son propre stockage.
$dossierGguf = "\\wsl.localhost\Ubuntu\home\david\models\gguf"
$modelfile = Get-Content "$PSScriptRoot\Modelfile" -Raw

foreach ($q in "f16", "Q8_0", "Q5_K_M", "Q4_K_M") {
    $temporaire = New-TemporaryFile
    # UTF-8 sans BOM : Set-Content -Encoding utf8 en ajoute un sous PowerShell 5.1.
    $contenu = $modelfile -replace "(?m)^FROM .*$", "FROM $dossierGguf\dare-$q.gguf"
    [IO.File]::WriteAllText($temporaire, $contenu, (New-Object Text.UTF8Encoding $false))
    Write-Output "=== prof-json:$($q.ToLower())"
    ollama create "prof-json:$($q.ToLower())" -f $temporaire
    Remove-Item $temporaire
}
ollama list
