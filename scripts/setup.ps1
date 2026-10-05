param([int]$Pages = 12)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    $venvPython = Join-Path $projectRoot 'venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw 'Önce PyCharm ile bu projeye Python 3.12 venv oluşturun.'
}
& $venvPython -c "import sys; assert sys.version_info[:2] == (3, 12), 'Python 3.12 gerekli'"
if ($LASTEXITCODE -ne 0) { throw 'Python sürümü uygun değil.' }
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Paket kurulumu başarısız.' }
& $venvPython main.py setup --pages $Pages
if ($LASTEXITCODE -ne 0) { throw 'Kurulum tamamlanamadı. Yukarıdaki hatayı inceleyin.' }
