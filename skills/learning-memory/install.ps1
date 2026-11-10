#!/usr/bin/env pwsh
# Installs the learning-memory system (skill, /learn-review command, database, hooks).
# Usage: .\install.ps1 [-NoHooks] [-DryRun] [-Uninstall]
#   -NoHooks    copy files and create the database, leave settings.json alone
#   -DryRun     print the hooks that would be registered, change nothing
#   -Uninstall  remove hooks, command and skill (the database is kept)

param(
    [switch]$NoHooks,
    [switch]$DryRun,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $PSCommandPath
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$SkillDst = Join-Path $env:USERPROFILE ".claude\skills\learning-memory"
$CmdDst = Join-Path $env:USERPROFILE ".claude\commands"
$CmdSrc = Join-Path $RepoRoot "commands\learn-review.md"
$env:PYTHONUTF8 = "1"

function Find-Python {
    foreach ($c in @(@("python3"), @("python"), @("py", "-3"))) {
        $exe = Get-Command $c[0] -ErrorAction SilentlyContinue
        if (-not $exe) { continue }
        $extra = @($c | Select-Object -Skip 1)
        & $exe.Source @extra -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { return ,@($exe.Source) + $extra }
    }
    return $null
}

function Invoke-Learn {
    param([string]$Script, [string[]]$LearnArgs)
    $py = Find-Python
    if (-not $py) { throw "No Python >= 3.9 found (python, python3 or py -3)." }
    $exe = $py[0]
    $pre = @($py | Select-Object -Skip 1)
    & $exe @pre $Script @LearnArgs
    if ($LASTEXITCODE -ne 0) { throw "learn.py $($LearnArgs -join ' ') failed (exit $LASTEXITCODE)" }
}

if ($Uninstall) {
    Write-Host "==> Removing hooks" -ForegroundColor Cyan
    $installed = Join-Path $SkillDst "scripts\learn.py"
    if (Test-Path $installed) { Invoke-Learn $installed @("uninstall-hooks") }
    Remove-Item (Join-Path $CmdDst "learn-review.md") -Force -ErrorAction SilentlyContinue
    Remove-Item $SkillDst -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "==> Removed skill and command. The database (~\.claude\learnings\) and its backups are kept."
    exit 0
}

if ($DryRun) {
    Write-Host "==> Dry run: hooks that would be registered" -ForegroundColor Cyan
    Invoke-Learn (Join-Path $ScriptDir "scripts\learn.py") @("install-hooks", "--dry-run")
    exit 0
}

Write-Host "==> Installing skill into $SkillDst" -ForegroundColor Cyan
if ($ScriptDir -ne $SkillDst) {
    New-Item -ItemType Directory -Path $SkillDst -Force | Out-Null
    Copy-Item (Join-Path $ScriptDir "*") $SkillDst -Recurse -Force
    Remove-Item (Join-Path $SkillDst "scripts\__pycache__") -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "==> Installing /learn-review into $CmdDst" -ForegroundColor Cyan
if (Test-Path $CmdSrc) {
    New-Item -ItemType Directory -Path $CmdDst -Force | Out-Null
    Copy-Item $CmdSrc (Join-Path $CmdDst "learn-review.md") -Force
} else {
    Write-Host "    $CmdSrc not found (installer run outside the repo); command not installed." -ForegroundColor Yellow
}

$Learn = Join-Path $SkillDst "scripts\learn.py"
Write-Host "==> Creating the database" -ForegroundColor Cyan
Invoke-Learn $Learn @("init")

if ($NoHooks) {
    Write-Host "==> Hooks NOT registered (-NoHooks). Register later: python `"$Learn`" install-hooks" -ForegroundColor Yellow
} else {
    Write-Host "==> Registering hooks in ~\.claude\settings.json" -ForegroundColor Cyan
    Invoke-Learn $Learn @("install-hooks")
}

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Host "WARNING: 'claude' is not on PATH; the background analysis needs it (or set LEARN_CLAUDE_BIN)." -ForegroundColor Yellow
}
Write-Host "==> Done. Restart Claude Code so the hooks and the command are picked up." -ForegroundColor Green
Write-Host "    After a session ends, its learnings appear as 'pending'; review them with /learn-review."
Write-Host "    Hooks run through Git Bash (required by Claude Code on Windows)."
