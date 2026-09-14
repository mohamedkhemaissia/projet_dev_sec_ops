# Lancer les tests localement (Windows).
# Utiliser -SkipInstall pour une execution hors ligne avec l'environnement existant.
[CmdletBinding()]
param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$virtualEnvironmentPython = Join-Path $repositoryRoot ".venv\Scripts\python.exe"

if (Test-Path -LiteralPath $virtualEnvironmentPython) {
    $pythonExecutable = $virtualEnvironmentPython
}
else {
    $pythonExecutable = (Get-Command python -ErrorAction Stop).Source
}

Push-Location $repositoryRoot
try {
    if (-not $SkipInstall) {
        $requirementFiles = @(
            "services/user-service/requirements.txt",
            "services/course-service/requirements.txt",
            "services/certificate-service/requirements.txt",
            "services/frontend-service/requirements.txt",
            "requirements-test.txt"
        )

        foreach ($requirementFile in $requirementFiles) {
            & $pythonExecutable -m pip install -r $requirementFile
            if ($LASTEXITCODE -ne 0) {
                throw "Dependency installation failed for $requirementFile."
            }
        }
    }

    & $pythonExecutable -m pytest tests/ services/frontend-service/tests/ -v
    if ($LASTEXITCODE -ne 0) {
        throw "Pytest failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
