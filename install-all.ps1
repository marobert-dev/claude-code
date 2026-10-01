#!/usr/bin/env pwsh
# Complete installer: web-team-agents, skills and rules into ~\.claude\
# Usage: .\install-all.ps1 [-Workspace C:\path\to\workspace]

param(
    [string]$Workspace = "."
)

$RepoRoot = Split-Path -Parent $PSCommandPath
$AgentsSrc = Join-Path $RepoRoot "web-team-agents\agents"
$SkillsSrc = Join-Path $RepoRoot "skills"
$RulesSrc = Join-Path $RepoRoot "rules"
$AgentsDst = Join-Path $env:USERPROFILE ".claude\agents"
$SkillsDst = Join-Path $env:USERPROFILE ".claude\skills"
$RulesDst = Join-Path $env:USERPROFILE ".claude\rules"

# Colors for output
function Write-Info {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[X] $Message" -ForegroundColor Red
}

Write-Host "=== Claude Code Agents & Skills Installer ===" -ForegroundColor Cyan
Write-Host ""

# Check sources exist
if (-not (Test-Path $AgentsSrc)) {
    Write-Error-Custom "Source not found: $AgentsSrc"
    exit 1
}

if (-not (Test-Path $SkillsSrc)) {
    Write-Error-Custom "Source not found: $SkillsSrc"
    exit 1
}

# Create directories
if (-not (Test-Path $AgentsDst)) {
    New-Item -ItemType Directory -Path $AgentsDst -Force | Out-Null
}

if (-not (Test-Path $SkillsDst)) {
    New-Item -ItemType Directory -Path $SkillsDst -Force | Out-Null
}

if (-not (Test-Path $RulesDst)) {
    New-Item -ItemType Directory -Path $RulesDst -Force | Out-Null
}

# Install agents
Write-Info "Installing agents..."
Copy-Item "$AgentsSrc\*.md" $AgentsDst -Force
$AgentCount = (Get-ChildItem "$AgentsDst\*.md" | Measure-Object).Count
Write-Success "Installed $AgentCount agents"
Write-Host ""

# Install skills (every folder under skills\ that contains a SKILL.md)
Write-Info "Installing skills..."
$SkillCount = 0
Get-ChildItem $SkillsSrc -Directory | Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } | ForEach-Object {
    $SkillDestDir = Join-Path $SkillsDst $_.Name
    if (-not (Test-Path $SkillDestDir)) {
        New-Item -ItemType Directory -Path $SkillDestDir -Force | Out-Null
    }
    Copy-Item (Join-Path $_.FullName "*") $SkillDestDir -Recurse -Force
    Write-Host "  - $($_.Name)"
    $SkillCount++
}
Write-Success "Installed $SkillCount skills"
Write-Host ""

# Install rules (loaded automatically by Claude Code in every session)
Write-Info "Installing rules..."
$RuleFiles = @()
if (Test-Path $RulesSrc) {
    $RuleFiles = @(Get-ChildItem $RulesSrc -Filter *.md -File -Recurse)
}
if ($RuleFiles.Count -gt 0) {
    Copy-Item (Join-Path $RulesSrc "*") $RulesDst -Recurse -Force
    Write-Success "Installed $($RuleFiles.Count) rules"
} else {
    Write-Host "No rules found in $RulesSrc - skipped" -ForegroundColor Yellow
}
Write-Host ""

# Optional: install workspace helpers
if ($Workspace -ne ".") {
    Write-Info "Installing workspace helpers into $Workspace..."

    $HooksDir = Join-Path $Workspace ".claude\hooks"
    $ScriptsDir = Join-Path $Workspace "scripts"

    if (-not (Test-Path $HooksDir)) {
        New-Item -ItemType Directory -Path $HooksDir -Force | Out-Null
    }

    if (-not (Test-Path $ScriptsDir)) {
        New-Item -ItemType Directory -Path $ScriptsDir -Force | Out-Null
    }

    $GateFile = Join-Path $RepoRoot "web-team-agents\hooks\gate.sh"
    if (Test-Path $GateFile) {
        Copy-Item $GateFile "$HooksDir\gate.sh" -Force
        Write-Success "Copied gate.sh"
    }

    $RunQueueFile = Join-Path $RepoRoot "web-team-agents\scripts\run-queue.sh"
    if (Test-Path $RunQueueFile) {
        Copy-Item $RunQueueFile "$ScriptsDir\run-queue.sh" -Force
        Write-Success "Copied run-queue.sh"
    }

    $RunParallelFile = Join-Path $RepoRoot "web-team-agents\scripts\run-parallel.sh"
    if (Test-Path $RunParallelFile) {
        Copy-Item $RunParallelFile "$ScriptsDir\run-parallel.sh" -Force
        Write-Success "Copied run-parallel.sh"
    }

    $EnableGraphifyFile = Join-Path $RepoRoot "web-team-agents\scripts\enable-graphify.ps1"
    if (Test-Path $EnableGraphifyFile) {
        Copy-Item $EnableGraphifyFile "$ScriptsDir\enable-graphify.ps1" -Force
        Write-Success "Copied enable-graphify.ps1"
    }

    Write-Host ""
}

Write-Host "=== Installation Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Location of installed components:"
Write-Host "  Agents:     $AgentsDst" -ForegroundColor Green
Write-Host "  Skills:     $SkillsDst" -ForegroundColor Green
Write-Host "  Rules:      $RulesDst" -ForegroundColor Green

if ($Workspace -ne ".") {
    Write-Host "  Workspace:  $Workspace" -ForegroundColor Green
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart Claude Code if ~/.claude/agents/, skills/ or rules/ was newly created"
Write-Host "  2. Queue stories:     claude --agent product-owner"
Write-Host "  3. Process queue:     claude --agent product-manager"
Write-Host "  4. (Optional) Enable Graphify:  .\scripts\enable-graphify.ps1 -Backup"
Write-Host ""
Write-Host "For SSH setup, see: https://claude.ai/artifact/Y2ncJTckHk8Bdpt2FuoPgv" -ForegroundColor Cyan
Write-Host ""
