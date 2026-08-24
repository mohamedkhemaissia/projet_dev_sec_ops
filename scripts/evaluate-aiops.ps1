# Mesure reproductible des diagnostics AIOps pour le rapport PFE.
[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:5005",
    [string]$WebhookToken = $env:AIOPS_WEBHOOK_TOKEN,
    [ValidateRange(1, 20)]
    [int]$Repetitions = 1,
    [string]$OutputPath = "docs/evidence/aiops-evaluation.csv"
)

$ErrorActionPreference = "Stop"
$headers = @{ Authorization = "Bearer $WebhookToken" }
$scenarios = @(
    @{
        AlertName = "TrainingHubServiceDown"
        Service = "user-service"
        ExpectedSeverity = "critical"
    },
    @{
        AlertName = "TrainingHubHighErrorRate"
        Service = "course-service"
        ExpectedSeverity = "warning"
    },
    @{
        AlertName = "TrainingHubHighP95Latency"
        Service = "frontend-service"
        ExpectedSeverity = "warning"
    }
)

$results = @()
foreach ($scenario in $scenarios) {
    for ($iteration = 1; $iteration -le $Repetitions; $iteration++) {
        $payload = @{
            version = "4"
            status = "firing"
            receiver = "aiops-evaluation"
            commonLabels = @{
                alertname = $scenario.AlertName
                service = $scenario.Service
                severity = $scenario.ExpectedSeverity
            }
            commonAnnotations = @{
                summary = "Evaluation $($scenario.AlertName) #$iteration"
                description = "Scenario controle pour comparer les modes rules et ollama."
            }
            alerts = @(
                @{
                    status = "firing"
                    labels = @{}
                    annotations = @{}
                    startsAt = [DateTime]::UtcNow.ToString("o")
                }
            )
        }

        $stopwatch = [Diagnostics.Stopwatch]::StartNew()
        $incident = Invoke-RestMethod `
            -Method Post `
            -Uri "$($BaseUrl.TrimEnd('/'))/api/v1/alerts" `
            -Headers $headers `
            -ContentType "application/json" `
            -Body ($payload | ConvertTo-Json -Depth 8)
        $stopwatch.Stop()

        $modelDurationNs = $incident.analysis.model_metrics.total_duration_ns
        $modelDurationMs = if ($null -eq $modelDurationNs) {
            ""
        }
        else {
            [Math]::Round([double]$modelDurationNs / 1000000, 2)
        }

        $results += [PSCustomObject]@{
            timestamp_utc = [DateTime]::UtcNow.ToString("o")
            alertname = $scenario.AlertName
            service = $scenario.Service
            iteration = $iteration
            analysis_mode = $incident.analysis.analysis_mode
            expected_severity = $scenario.ExpectedSeverity
            model_severity = $incident.analysis.model_severity
            predicted_severity = $incident.analysis.severity
            model_severity_match = if ($null -eq $incident.analysis.model_severity) {
                ""
            }
            else {
                $incident.analysis.model_severity -eq $scenario.ExpectedSeverity
            }
            severity_match = $incident.analysis.severity -eq $scenario.ExpectedSeverity
            severity_adjusted = $incident.analysis.severity_adjusted
            confidence = $incident.analysis.confidence
            request_latency_ms = $stopwatch.ElapsedMilliseconds
            model_duration_ms = $modelDurationMs
            prompt_tokens = $incident.analysis.model_metrics.prompt_tokens
            output_tokens = $incident.analysis.model_metrics.output_tokens
            probable_cause = $incident.analysis.probable_cause
            recommendations = $incident.analysis.recommendations -join " | "
            human_score_1_to_5 = ""
            human_comment = ""
        }
    }
}

$resolvedOutputPath = Join-Path (Resolve-Path -LiteralPath ".").Path $OutputPath
$outputDirectory = Split-Path -Parent $resolvedOutputPath
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
$results | Export-Csv -LiteralPath $resolvedOutputPath -NoTypeInformation -Encoding utf8

$results | Format-Table alertname, analysis_mode, severity_match, confidence, request_latency_ms
Write-Output "Evaluation enregistree dans $resolvedOutputPath"
