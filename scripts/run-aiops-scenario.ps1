# Demonstration locale du diagnostic AIOps a partir d'une alerte Alertmanager.
[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:5005",
    [string]$WebhookToken = "traininghub-aiops-local-token",
    [ValidateSet(
        "TrainingHubServiceDown",
        "TrainingHubHighErrorRate",
        "TrainingHubHighP95Latency"
    )]
    [string]$AlertName = "TrainingHubHighErrorRate",
    [ValidateSet(
        "user-service",
        "course-service",
        "certificate-service",
        "frontend-service"
    )]
    [string]$Service = "course-service"
)

$ErrorActionPreference = "Stop"

$severity = if ($AlertName -eq "TrainingHubServiceDown") {
    "critical"
}
else {
    "warning"
}

$payload = @{
    version = "4"
    status = "firing"
    receiver = "aiops-webhook"
    groupLabels = @{
        alertname = $AlertName
        service = $Service
    }
    commonLabels = @{
        alertname = $AlertName
        service = $Service
        severity = $severity
    }
    commonAnnotations = @{
        summary = "Scenario AIOps controle pour $Service"
        description = "Alerte generee volontairement pour la demonstration PFE."
    }
    alerts = @(
        @{
            status = "firing"
            labels = @{
                alertname = $AlertName
                service = $Service
                severity = $severity
            }
            annotations = @{}
            startsAt = [DateTime]::UtcNow.ToString("o")
        }
    )
}

$headers = @{
    Authorization = "Bearer $WebhookToken"
}

$incident = Invoke-RestMethod `
    -Method Post `
    -Uri "$($BaseUrl.TrimEnd('/'))/api/v1/alerts" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body ($payload | ConvertTo-Json -Depth 8)

Write-Output "Incident: $($incident.id)"
Write-Output "Service: $($incident.service)"
Write-Output "Alerte: $($incident.alertname)"
Write-Output "Mode d'analyse: $($incident.analysis.analysis_mode)"
Write-Output "Cause probable: $($incident.analysis.probable_cause)"
Write-Output "Confiance: $($incident.analysis.confidence)"
Write-Output "Recommandations:"
foreach ($recommendation in $incident.analysis.recommendations) {
    Write-Output "- $recommendation"
}

if ($incident.analysis.analysis_mode -eq "rules_fallback") {
    Write-Warning "Le modele etait indisponible ou sa sortie etait invalide."
}
