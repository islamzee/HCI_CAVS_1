# CAVS-1: start (or stop) the bag player + bridge on Windows.
# Normally run by double-clicking start-windows.bat / stop-windows.bat.
#   -Stop          stop the pod
#   -Bag <folder>  bag folder (default: <repo>\Dataset\autonomy_demo_slim)
param([switch]$Stop, [string]$Bag)

$Image  = "ghcr.io/islamzee/hci_cavs_1/cavs-bag-bridge:latest"
$PodYml = Join-Path $PSScriptRoot "cavs-pod.yaml"
$Repo   = Split-Path -Parent $PSScriptRoot
if (-not $Bag) { $Bag = Join-Path $Repo "Dataset\autonomy_demo_slim" }

function Fail($msg) { Write-Host "`n$msg" -ForegroundColor Red; exit 1 }
function Step($msg) { Write-Host "`n== $msg" -ForegroundColor Cyan }

if (-not (Get-Command podman -ErrorAction SilentlyContinue)) {
    Fail "Podman is not installed. Install Podman Desktop from https://podman-desktop.io, open it once, then run this again."
}

# 1. Podman machine (the Linux VM that runs the containers)
Step "Checking the Podman machine"
$machines = podman machine list --format "{{.Name}} {{.Running}}"
if (-not $machines) {
    Write-Host "No Podman machine yet - creating one (first time only, takes a few minutes)"
    podman machine init --cpus 4 --memory 8192
    if ($LASTEXITCODE -ne 0) { Fail "Could not create the Podman machine. Open Podman Desktop and follow its setup, then run this again." }
    $machines = podman machine list --format "{{.Name}} {{.Running}}"
}
if (-not ($machines -match "true")) {
    podman machine start
    if ($LASTEXITCODE -ne 0) { Fail "Could not start the Podman machine. Start it in Podman Desktop, then run this again." }
}

# Stop the old pod (if any) before changing anything
podman kube down $PodYml 2>&1 | Out-Null
if ($Stop) { Write-Host "`nStopped." -ForegroundColor Green; exit 0 }

# 2. Bag folder
Step "Checking the bag folder"
if (-not (Test-Path (Join-Path $Bag "metadata.yaml"))) {
    Fail "No bag found in:`n  $Bag`nRun 'git pull' in the repo folder to get Dataset\autonomy_demo_slim (it must contain metadata.yaml and the .mcap file)."
}
$full = (Resolve-Path $Bag).Path
$vmPath = "/mnt/" + $full.Substring(0, 1).ToLower() + ($full.Substring(2) -replace '\\', '/')   # C:\x\y -> /mnt/c/x/y
Write-Host "Using $full"

# 3. Image
Step "Downloading the latest image (first time ~1 GB)"
podman pull $Image
if ($LASTEXITCODE -ne 0) { Fail "Could not download $Image. Check your internet connection." }

# 4. Bag volume + pod
Step "Starting the pod"
podman volume rm -f cavs-bag 2>&1 | Out-Null
podman volume create --opt type=none --opt o=bind --opt "device=$vmPath" cavs-bag | Out-Null
if ($LASTEXITCODE -ne 0) { Fail "Could not connect the bag folder to Podman." }
podman kube play $PodYml | Out-Null
if ($LASTEXITCODE -ne 0) { Fail "Could not start the pod. See the messages above." }

# 5. Wait for the bridge, then open the probe page
Write-Host "Waiting for data..."
$ok = $false
for ($i = 0; $i -lt 30 -and -not $ok; $i++) {
    Start-Sleep -Seconds 2
    try { $ok = (Invoke-WebRequest -UseBasicParsing "http://localhost:8765/stats" -TimeoutSec 2).Content -match "/mtx/odom" } catch {}
}
if (-not $ok) { Fail "The pod started but no data arrived. Run: podman logs cavs-player" }

Write-Host "`nRunning. Probe page: http://localhost:8765/   Websocket: ws://localhost:8765/" -ForegroundColor Green
Write-Host "To stop: double-click stop-windows.bat"
Start-Process "http://localhost:8765/"
