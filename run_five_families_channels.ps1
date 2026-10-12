# Sequential runner for 9 five-family experiments:
#   5 families x 20 000 words x all decoders x 3 channels x 3 sizes.
#
# Each JSON preset defines its own results_dir:
#   research_results/five_families_channels/<channel>/<size>_20k/
# Shared logs/summary live in:
#   research_results/five_families_channels/_runs/
#
# Run all:
#   .\run_five_families_channels.ps1
# Run a subset:
#   .\run_five_families_channels.ps1 -Only "16_8_RAYLEIGH"
#   .\run_five_families_channels.ps1 -Only "SINUSOIDAL"

param(
    [string]$Only = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

$presets = @(
    "FIVE_FAMILIES_20K_FULL_DECODERS_16_8_RAYLEIGH",
    "FIVE_FAMILIES_20K_FULL_DECODERS_16_8_SINUSOIDAL",
    "FIVE_FAMILIES_20K_FULL_DECODERS_16_8_RAYLEIGH_AWGN",
    "FIVE_FAMILIES_20K_FULL_DECODERS_32_16_RAYLEIGH",
    "FIVE_FAMILIES_20K_FULL_DECODERS_32_16_SINUSOIDAL",
    "FIVE_FAMILIES_20K_FULL_DECODERS_32_16_RAYLEIGH_AWGN",
    "FIVE_FAMILIES_20K_FULL_DECODERS_64_32_RAYLEIGH",
    "FIVE_FAMILIES_20K_FULL_DECODERS_64_32_SINUSOIDAL",
    "FIVE_FAMILIES_20K_FULL_DECODERS_64_32_RAYLEIGH_AWGN"
)

if ($Only -ne "") {
    $presets = @($presets | Where-Object { $_ -like "*$Only*" })
    if ($presets.Count -eq 0) {
        Write-Error "No preset matches '$Only'"
        exit 1
    }
}

$runsDir = Join-Path $PSScriptRoot "research_results\five_families_channels\_runs"
New-Item -ItemType Directory -Force $runsDir | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$tempDir = Join-Path $env:TEMP "wavelet_five_families_$stamp"
New-Item -ItemType Directory -Force $tempDir | Out-Null

$masterLog = Join-Path $runsDir "master_log_$stamp.txt"
$summary = @()

function Log([string]$message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message
    Write-Host $line
    Add-Content -Path $masterLog -Value $line
}

Log "start: $($presets.Count) experiment(s)"
Log "master log: $masterLog"

$index = 0
foreach ($preset in $presets) {
    $index++
    $runtimeConfig = Join-Path $tempDir "$preset.json"
    $stdoutLog = Join-Path $runsDir "$preset.stdout.log"
    $stderrLog = Join-Path $runsDir "$preset.stderr.log"

    Log ("=" * 72)
    Log "[$index/$($presets.Count)] $preset"

    # Strip the { preset, experiment } wrapper before running.
    & $python -m research.extract_preset_config --preset $preset --out $runtimeConfig
    if ($LASTEXITCODE -ne 0) {
        Log "ERROR: could not extract runtime config for $preset"
        $summary += [pscustomobject]@{
            Preset = $preset
            Completed = $false
            ExitCode = "config_failed"
            Minutes = 0
        }
        continue
    }

    $started = Get-Date
    $process = Start-Process `
        -FilePath $python `
        -ArgumentList @("-m", "research.run_from_json", $runtimeConfig) `
        -WorkingDirectory $PSScriptRoot `
        -NoNewWindow `
        -Wait `
        -PassThru `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog

    $minutes = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)
    $exitCode = $process.ExitCode
    $completed = $exitCode -eq 0

    if ($completed) {
        Log "DONE: $preset in $minutes min"
    } else {
        Log "ERROR: $preset exited with code $exitCode after $minutes min"
        Log "stderr: $stderrLog"
    }

    $summary += [pscustomobject]@{
        Preset = $preset
        Completed = $completed
        ExitCode = $exitCode
        Minutes = $minutes
    }
}

Log ("=" * 72)
Log "SUMMARY:"
foreach ($row in $summary) {
    Log ("  {0}: completed={1}, exit={2}, {3} min" -f $row.Preset, $row.Completed, $row.ExitCode, $row.Minutes)
}

$summaryPath = Join-Path $runsDir "summary_$stamp.csv"
$summary | Export-Csv -Path $summaryPath -NoTypeInformation -Encoding UTF8
Log "summary: $summaryPath"

Write-Host ""
Write-Host "Done. Per-experiment results:"
Write-Host "  research_results\five_families_channels\<channel>\<size>_20k\"
Write-Host "  files: summary.csv, experiment.log, runtime_config.json"
Write-Host "Master log: $masterLog"
Write-Host "Summary: $summaryPath"
