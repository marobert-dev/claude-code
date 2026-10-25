#Requires -Version 5.1
<#
  Installs the web-team-agents pipeline.
    Global (always):    copies agents\*.md into ~\.claude\agents\
    Workspace (opt-in): pass -Workspace to also install the per-project helpers
                         (hook scripts, runners, templates) there.

  Usage:
    .\install.ps1                                   # global agents only
    .\install.ps1 -Workspace C:\path\to\app          # global agents + workspace helpers

  Env:
    CLAUDE_AGENTS_DIR   override the global agents install dir (default: ~\.claude\agents)
#>
[CmdletBinding()]
param(
    [string]$Workspace
)
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AgentsDir = if ($env:CLAUDE_AGENTS_DIR) { $env:CLAUDE_AGENTS_DIR } else { Join-Path $HOME ".claude\agents" }

Write-Host "==> Installing agents into $AgentsDir"
New-Item -ItemType Directory -Force -Path $AgentsDir | Out-Null
$agentFiles = Get-ChildItem (Join-Path $ScriptDir "agents") -Filter *.md
Copy-Item $agentFiles.FullName -Destination $AgentsDir -Force
Write-Host "    $($agentFiles.Count) agent files copied."
Write-Host "    Restart Claude Code if $AgentsDir didn't already exist before this copy -"
Write-Host "    a running session only picks up a brand-new agents directory after a restart."

if ($Workspace) {
    Write-Host "==> Installing workspace helpers into $Workspace"
    New-Item -ItemType Directory -Force -Path (Join-Path $Workspace ".claude\hooks") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $Workspace "scripts") | Out-Null
    $HookScripts = @("gate.sh", "pm-state.sh", "detect-conventions.sh", "role-guard.sh", "secret-scan.sh")
    foreach ($f in $HookScripts) {
        Copy-Item (Join-Path $ScriptDir "hooks\$f") (Join-Path $Workspace ".claude\hooks\$f") -Force
    }
    Copy-Item (Join-Path $ScriptDir "scripts\run-queue.sh") (Join-Path $Workspace "scripts\") -Force
    Copy-Item (Join-Path $ScriptDir "scripts\run-parallel.sh") (Join-Path $Workspace "scripts\") -Force
    Write-Host "    Copied $($HookScripts -join ', ') to .claude\hooks\ (the agents' frontmatter hooks call gate.sh and role-guard.sh)."
    Write-Host "    Copied run-queue.sh, run-parallel.sh to scripts\."
    $Templates = Join-Path $Workspace ".claude\templates"
    New-Item -ItemType Directory -Force -Path $Templates | Out-Null
    foreach ($t in @("user-manual", "e2e")) {
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $Templates $t)
        Copy-Item (Join-Path $ScriptDir "templates\$t") $Templates -Recurse -Force
    }
    Write-Host "    Copied the user-manual template (doc-writer) and the e2e screenshot hook (story-validator) to .claude\templates\."
    Write-Host "    NOTE: these are bash scripts - run them from Git Bash or WSL, not PowerShell."
    Write-Host "    NOT auto-merged: $ScriptDir\hooks\settings.snippet.json into $Workspace\.claude\settings.json"
    Write-Host "    Back up settings.json first, then merge that snippet by hand (team-memory and pipeline-script permissions)."
    Write-Host "    If an older snippet added a SubagentStop gate hook there, remove it: the dev agents now run the gate themselves."
} else {
    Write-Host "==> No -Workspace given - skipping per-project helpers (hooks/, scripts/)."
    Write-Host "    Re-run as: .\install.ps1 -Workspace C:\path\to\your\app-repo"
}

Write-Host "==> Done. See README.md to queue stories (product-owner) and run the pipeline (product-manager)."
