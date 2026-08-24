param(
    [string]$UserBaseUrl = "http://localhost:5001",
    [string]$CourseBaseUrl = "http://localhost:5002",
    [string]$CertificateBaseUrl = "http://localhost:5004",
    [string]$FrontendBaseUrl = "http://localhost:3000",
    [string]$AdminEmail = "admin@training.com",
    [string]$AdminPassword = $env:DEFAULT_ADMIN_PASSWORD
)

$ErrorActionPreference = "Stop"

function Assert-Scenario {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw "Scenario invalide: $Message"
    }
}

function Invoke-JsonRequest {
    param(
        [string]$Method,
        [string]$Uri,
        [hashtable]$Headers = @{},
        [object]$Body
    )

    $parameters = @{
        Method = $Method
        Uri = $Uri
        Headers = $Headers
        UseBasicParsing = $true
        TimeoutSec = 20
    }

    if ($null -ne $Body) {
        $parameters.ContentType = "application/json"
        $parameters.Body = $Body | ConvertTo-Json -Depth 8 -Compress
    }

    Invoke-RestMethod @parameters
}

function New-BearerHeader {
    param([string]$Token)
    @{ Authorization = "Bearer $Token" }
}

$runId = "{0}-{1}" -f (Get-Date -Format "yyyyMMddHHmmss"), ([guid]::NewGuid().ToString("N").Substring(0, 8))
$learnerEmail = "learner.$runId@example.com"
$learnerPassword = "LearnerDemo123!"
$courseTitle = "DevSecOps PFE $runId"

Write-Host "[1/11] Verification des services"
$userHealth = Invoke-JsonRequest -Method GET -Uri "$UserBaseUrl/api/v1/users/health"
$courseHealth = Invoke-JsonRequest -Method GET -Uri "$CourseBaseUrl/api/v1/courses/health"
$certificateHealth = Invoke-JsonRequest -Method GET -Uri "$CertificateBaseUrl/api/v1/certificates/health"
$frontendHealth = Invoke-JsonRequest -Method GET -Uri "$FrontendBaseUrl/health"
Assert-Scenario ($userHealth.status -eq "ok") "user-service indisponible"
Assert-Scenario ($courseHealth.status -eq "ok") "course-service indisponible"
Assert-Scenario ($certificateHealth.status -eq "ok") "certificate-service indisponible"
Assert-Scenario ($frontendHealth.status -eq "ok") "frontend-service indisponible"

Write-Host "[2/11] Creation d'un learner unique"
$learner = Invoke-JsonRequest -Method POST -Uri "$UserBaseUrl/api/v1/users/register" -Body @{
    name = "Learner Demo"
    email = $learnerEmail
    password = $learnerPassword
}
Assert-Scenario ($learner.role -eq "learner") "le role learner n'a pas ete applique"

Write-Host "[3/11] Authentification learner et administrateur"
$learnerLogin = Invoke-JsonRequest -Method POST -Uri "$UserBaseUrl/api/v1/users/login" -Body @{
    email = $learnerEmail
    password = $learnerPassword
}
$adminLogin = Invoke-JsonRequest -Method POST -Uri "$UserBaseUrl/api/v1/users/login" -Body @{
    email = $AdminEmail
    password = $AdminPassword
}
Assert-Scenario (-not [string]::IsNullOrWhiteSpace($learnerLogin.token)) "token learner absent"
Assert-Scenario ($adminLogin.user.role -eq "admin") "le compte admin n'a pas le role admin"

$learnerHeaders = New-BearerHeader -Token $learnerLogin.token
$adminHeaders = New-BearerHeader -Token $adminLogin.token

Write-Host "[4/11] Verification RBAC: creation interdite au learner"
$forbiddenStatus = 0
try {
    Invoke-JsonRequest -Method POST -Uri "$CourseBaseUrl/api/v1/courses" -Headers $learnerHeaders -Body @{
        title = "Cours interdit $runId"
        description = "Cette creation doit etre refusee."
        duration = 1
        category = "Security"
    } | Out-Null
} catch {
    if ($null -ne $_.Exception.Response) {
        $forbiddenStatus = [int]$_.Exception.Response.StatusCode
    }
}
Assert-Scenario ($forbiddenStatus -eq 403) "le RBAC n'a pas bloque le learner"

Write-Host "[5/11] Creation d'une formation par l'administrateur"
$courseResponse = Invoke-JsonRequest -Method POST -Uri "$CourseBaseUrl/api/v1/courses" -Headers $adminHeaders -Body @{
    title = $courseTitle
    description = "Formation de demonstration sur la livraison logicielle securisee."
    duration = 24
    level = "beginner"
    category = "DevSecOps"
}
$course = $courseResponse.course
Assert-Scenario ($course.title -eq $courseTitle) "la formation n'a pas ete creee"

Write-Host "[6/11] Inscription du learner"
$enrollment = Invoke-JsonRequest -Method POST -Uri "$CourseBaseUrl/api/v1/courses/$($course.id)/enroll" -Headers $learnerHeaders
Assert-Scenario ($enrollment.status -eq "enrolled") "l'inscription n'est pas au statut enrolled"

Write-Host "[7/11] Completion de la formation par l'administrateur"
$completedEnrollment = Invoke-JsonRequest -Method PUT -Uri "$CourseBaseUrl/api/v1/courses/enrollments/$($enrollment.id)/status" -Headers $adminHeaders -Body @{
    status = "completed"
}
Assert-Scenario ($completedEnrollment.status -eq "completed") "l'inscription n'est pas completee"

Write-Host "[8/11] Emission du certificat"
$certificate = Invoke-JsonRequest -Method POST -Uri "$CertificateBaseUrl/api/v1/certificates/courses/$($course.id)/issue" -Headers $learnerHeaders
Assert-Scenario ($certificate.status -eq "active") "le certificat n'est pas actif"

Write-Host "[9/11] Consultation des certificats du learner"
$certificates = @(Invoke-JsonRequest -Method GET -Uri "$CertificateBaseUrl/api/v1/certificates/me" -Headers $learnerHeaders)
$certificateFound = $null -ne ($certificates | Where-Object { "$($_.id)" -eq "$($certificate.id)" } | Select-Object -First 1)
Assert-Scenario $certificateFound "le certificat emis n'apparait pas dans la liste"

Write-Host "[10/11] Verification publique du certificat"
$verification = Invoke-JsonRequest -Method GET -Uri "$CertificateBaseUrl/api/v1/certificates/verify/$($certificate.certificate_code)"
Assert-Scenario ($verification.valid -eq $true) "la verification publique a echoue"

Write-Host "[11/11] Telechargement du PDF"
$pdfPath = Join-Path ([System.IO.Path]::GetTempPath()) "traininghub-$runId.pdf"
try {
    Invoke-WebRequest `
        -Uri "$CertificateBaseUrl/api/v1/certificates/$($certificate.id)/download" `
        -Headers $learnerHeaders `
        -UseBasicParsing `
        -TimeoutSec 30 `
        -OutFile $pdfPath
    $pdfInfo = Get-Item -LiteralPath $pdfPath
    Assert-Scenario ($pdfInfo.Length -gt 500) "le PDF est vide ou incomplet"
} finally {
    if (Test-Path -LiteralPath $pdfPath) {
        Remove-Item -LiteralPath $pdfPath -Force
    }
}

Write-Host ""
Write-Host "SCENARIO METIER VALIDE" -ForegroundColor Green
[pscustomobject]@{
    LearnerEmail = $learnerEmail
    CourseId = $course.id
    EnrollmentId = $enrollment.id
    CertificateId = $certificate.id
    CertificateCode = $certificate.certificate_code
}
