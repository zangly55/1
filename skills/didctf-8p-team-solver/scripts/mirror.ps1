# Final mirror sync for parallel-solving workspace.
#   knowledge-base : mirror -> work   (/E copy, never delete)
#   answer, wp     : work   -> mirror
# Usage: powershell -File mirror.ps1 -Work <path> -Mirror <path>
param(
    [Parameter(Mandatory=$true)][string]$Work,
    [Parameter(Mandatory=$true)][string]$Mirror
)

$ErrorActionPreference = 'Continue'
Write-Host "Work   = $Work"
Write-Host "Mirror = $Mirror"

# 1) knowledge-base: mirror -> work
$kbSrc = Join-Path $Mirror 'knowledge-base'
$kbDst = Join-Path $Work   'knowledge-base'
if (Test-Path $kbSrc) {
    robocopy $kbSrc $kbDst /E /NFL /NDL /NJH /NJS | Out-Null
    $chunks = Join-Path $kbDst 'rag\chunks.jsonl'
    if (Test-Path $chunks) {
        $n = (Get-Content $chunks -ErrorAction SilentlyContinue | Measure-Object -Line).Lines
    } else {
        $n = 'n/a (no rag)'
    }
    Write-Host "knowledge-base synced. chunks lines: $n"
} else {
    Write-Host "WARN: $kbSrc not found, skip knowledge-base sync"
}

# 2) answer: work -> mirror
$ansSrc = Join-Path $Work   'answer'
$ansDst = Join-Path $Mirror 'answer'
if (Test-Path $ansSrc) {
    New-Item -ItemType Directory -Force -Path $ansDst | Out-Null
    Copy-Item (Join-Path $ansSrc '*.txt') $ansDst -Force
    Write-Host ("answer synced: " + (Get-ChildItem $ansDst -Filter '*.txt').Count + " txt")
}

# 3) wp: work -> mirror
$wpSrc = Join-Path $Work   'wp'
$wpDst = Join-Path $Mirror 'wp'
if (Test-Path $wpSrc) {
    New-Item -ItemType Directory -Force -Path $wpDst | Out-Null
    Copy-Item (Join-Path $wpSrc '*.txt') $wpDst -Force
    Write-Host ("wp synced: " + (Get-ChildItem $wpDst -Filter '*.txt').Count + " txt")
}

Write-Host "mirror done."
exit 0
