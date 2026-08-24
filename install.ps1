$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/WorkofAditya/Leaf.git"
$InstallDir = Join-Path $env:LOCALAPPDATA "Leaf"
$BinDir = Join-Path $InstallDir "bin"
$SourceDir = Join-Path $InstallDir "source"
$Launcher = Join-Path $BinDir "leaf.cmd"

Write-Host "🍃 Installing Leaf for Windows..."

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is required. Install Git for Windows first."
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python is required. Install Python 3.10+ first."
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

if (Test-Path (Join-Path $SourceDir ".git")) {
    Write-Host "Updating existing Leaf installation..."
    git -C $SourceDir fetch origin
    git -C $SourceDir checkout GUI
    git -C $SourceDir pull --ff-only origin GUI
} else {
    if (Test-Path $SourceDir) {
        Remove-Item -Recurse -Force $SourceDir
    }
    Write-Host "Downloading Leaf..."
    git clone --branch GUI --depth 1 $RepoUrl $SourceDir
}

Write-Host "Installing Python dependencies..."
python -m pip install --user --upgrade PySide6

@"
@echo off
python "$SourceDir\leaf" %*
"@ | Set-Content -Encoding ASCII $Launcher

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathEntries = @()
if ($userPath) {
    $pathEntries = $userPath -split ';' | Where-Object { $_ -ne '' }
}

if ($pathEntries -notcontains $BinDir) {
    [Environment]::SetEnvironmentVariable("Path", (($pathEntries + $BinDir) -join ';'), "User")
    $env:Path = "$BinDir;$env:Path"
}

Write-Host ""
Write-Host "🌳 Leaf installed successfully."
Write-Host "Run 'leaf' from any PowerShell or Command Prompt window."
Write-Host "Run 'leaf status' for the CLI."
Write-Host "Run 'leaf' with no arguments for the GUI."
Write-Host ""
Write-Host "If an already-open terminal cannot find 'leaf', close it and open a new terminal."
