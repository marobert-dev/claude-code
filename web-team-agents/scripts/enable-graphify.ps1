#!/usr/bin/env pwsh
# Enable Graphify integration in all development agents
# Usage: .\scripts\enable-graphify.ps1 [-Backup] [-Remove]

param(
    [switch]$Backup = $false,
    [switch]$Remove = $false
)

$AgentsDir = "$env:USERPROFILE\.claude\agents"
$BackupDir = "$AgentsDir-graphify-backup-$(Get-Date -Format 'yyyyMMddHHmmss')"

$GraphifyBlock = @"

Before anything else, check whether ``graphify-out/`` exists in the workspace. If it does, read ``graphify-out/GRAPH_REPORT.md`` for a high-level architecture summary, and run ``graphify query "<question>"`` via Bash whenever you need to know what a file or symbol depends on, or is depended on by, before {{ACTION}}. If Graphify isn't set up for this project, skip this and proceed without it.
"@

# Only the planners and the scout read the full report; every other agent queries on demand,
# since it may be invoked many times per story.
$ReportReaders = @("analyst", "product-owner", "conventions-scout")
$GraphifyQueryBlock = @"

Before anything else, check whether ``graphify-out/`` exists in the workspace. If it does, run ``graphify query "<question>"`` via Bash whenever you need to know what a file or symbol depends on, or is depended on by, before {{ACTION}} — query only what you need; don't read ``graphify-out/GRAPH_REPORT.md`` in full. If Graphify isn't set up for this project, skip this and proceed without it.
"@

# Windows PowerShell 5.1 reads BOM-less UTF-8 as ANSI (mangling — and accents) and writes UTF8 with a BOM,
# which lands before the agent's `---` frontmatter. Read as UTF-8 (a stray BOM is dropped), write without one.
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
function Read-Agent([string]$Path) { [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8) }
function Write-Agent([string]$Path, [string]$Text) { [System.IO.File]::WriteAllText($Path, $Text, $Utf8NoBom) }

$Actions = @{
    "product-manager" = "routing work"
    "analyst" = "deciding on the plan"
    "code-reviewer" = "judging the wider impact of a change"
    "conventions-scout" = "writing conventions"
    "dev-backend" = "changing it"
    "dev-frontend" = "changing it"
    "dev-integrator" = "wiring it"
    "security-reviewer" = "assessing the risks"
    "story-validator" = "validating the story"
    "unit-tester" = "writing tests"
    "doc-writer" = "writing docs"
    "product-owner" = "writing stories"
}

if ($Remove) {
    Write-Host "Removing Graphify blocks from agents..." -ForegroundColor Yellow
    foreach ($agent in $Actions.Keys) {
        $file = "$AgentsDir\$agent.md"
        if (Test-Path $file) {
            $content = Read-Agent $file
            # Same as the bash version: drop the one-line block and the blank line after it.
            $updated = $content -replace '(?m)^Before anything else, check whether `graphify-out/`.*\r?\n(?:[ \t]*\r?\n)?', ''
            Write-Agent $file $updated
            Write-Host "  ✓ Removed from $agent.md"
        }
    }
    Write-Host "Graphify blocks removed. Agents restored to minimal state."
    exit 0
}

if (-not (Test-Path $AgentsDir)) {
    Write-Host "Error: $AgentsDir does not exist. Install agents first: bash install.sh" -ForegroundColor Red
    exit 1
}

if ($Backup) {
    Write-Host "Backing up agents to $BackupDir..." -ForegroundColor Yellow
    Copy-Item -Path $AgentsDir -Destination $BackupDir -Recurse
    Write-Host "  ✓ Backup saved"
}

Write-Host "Enabling Graphify integration in agents..." -ForegroundColor Yellow

foreach ($agent in $Actions.Keys) {
    $file = "$AgentsDir\$agent.md"
    if (-not (Test-Path $file)) {
        Write-Host "  ⚠ Skipping $agent.md (not found)"
        continue
    }

    $content = Read-Agent $file

    # Check if Graphify block already exists
    if ($content -match 'Before anything else, check whether `graphify-out/`') {
        Write-Host "  ✓ $agent.md already has Graphify (skipped)"
        continue
    }

    # Find frontmatter end (second ---)
    $lines = $content -split "`n"
    $frontmatterEnd = 0
    $count = 0
    foreach ($i in 0..($lines.Count - 1)) {
        if ($lines[$i].Trim() -eq "---") {
            $count++
            if ($count -eq 2) {
                $frontmatterEnd = $i
                break
            }
        }
    }

    if ($frontmatterEnd -eq 0) {
        Write-Host "  ✗ Could not find frontmatter end in $agent.md" -ForegroundColor Red
        continue
    }

    # Insert Graphify block after frontmatter
    $action = $Actions[$agent]
    $block = if ($ReportReaders -contains $agent) { $GraphifyBlock } else { $GraphifyQueryBlock }
    $graphifyText = $block -replace '{{ACTION}}', $action

    $before = $lines[0..$frontmatterEnd]
    $after = $lines[($frontmatterEnd + 1)..($lines.Count - 1)]

    $updated = @($before) + @($graphifyText) + @($after)
    Write-Agent $file ($updated -join "`n")

    Write-Host "  ✓ Injected into $agent.md"
}

Write-Host "Done! All agents now support Graphify." -ForegroundColor Green
Write-Host "When graphify-out/ exists in your workspace, agents will use it for architecture queries."
