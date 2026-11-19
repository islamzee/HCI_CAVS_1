# CAVS-1: start (or stop) the bag player + bridge on Windows.
# Normally run by double-clicking start-windows.bat / stop-windows.bat.
#   -Stop          stop the pod
#   -Bag <folder>  bag folder (default: <repo>\Dataset\HCI-bag-v2 if its .mcap is there, else autonomy_demo_slim)
param([switch]$Stop, [string]$Bag)

$Image  = "ghcr.io/islamzee/hci_cavs_1/cavs-bag-bridge:latest"
$PodYml = Join-Path $PSScriptRoot "cavs-pod.yaml"
$Repo   = Split-Path -Parent $PSScriptRoot
$NewBag  = Join-Path $Repo "Dataset\HCI-bag-v2"
$SlimBag = Join-Path $Repo "Dataset\autonomy_demo_slim"

function Fail($msg) { Write-Host "`n$msg" -ForegroundColor Red; exit 1 }
function Step($msg) { Write-Host "`n== $msg" -ForegroundColor Cyan }

# Runs when no data arrives: finds which part is not working, prints what to do,
# and saves everything to cavs-diagnose.txt (send that file to Zeenat if the hint doesn't help).
function Diagnose {
    $report = Join-Path $PSScriptRoot "cavs-diagnose.txt"
    $bagList  = (podman exec cavs-bridge ls -la /bag 2>&1) | Out-String
    $inside   = (podman exec cavs-bridge python3 -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8765/stats',timeout=3).read().decode()[:800])" 2>&1) | Out-String
    $states   = (podman ps -a --pod --format "{{.Names}}  {{.Status}}" 2>&1) | Out-String
    $lines = @(
        "== podman machine", ((podman machine list 2>&1) | Out-String),
        "== containers", $states,
        "== bag folder inside the pod (should list metadata.yaml and a .mcap)", $bagList,
        "== bridge /stats from inside the pod", $inside,
        "== player log (last 30 lines)", ((podman logs --tail 30 cavs-player 2>&1) | Out-String),
        "== bridge log (last 30 lines)", ((podman logs --tail 30 cavs-bridge 2>&1) | Out-String)
    )
    $lines | Out-File -Encoding utf8 $report

    if ($bagList -notmatch "\.mcap") {
        $hint = "The pod cannot see the bag folder.`n" +
                "  - Under '== podman machine' above, VM TYPE must be 'wsl'. If it says 'hyperv', delete that machine in Podman Desktop and create a new one with WSL.`n" +
                "  - If the repo is inside OneDrive (path has 'OneDrive' in it), clone it somewhere else, e.g. C:\HCI_CAVS_1, and run this again.`n" +
                "  - Check that $Bag has the .mcap file. For autonomy_demo_slim run 'git pull'; for HCI-bag-v2 see Dataset\HCI-bag-v2\README.md."
    } elseif ($inside -match "/mtx/odom") {
        $hint = "Data is flowing inside the pod, but Windows cannot reach port 8765.`n" +
                "  - Try http://127.0.0.1:8765/ in the browser.`n" +
                "  - Disconnect any VPN, then run this again.`n" +
                "  - Restart the Podman machine (Podman Desktop > Settings > Resources > restart), then run this again."
    } elseif ($states -notmatch "cavs-player\s+Up") {
        $hint = "The bag player is not running. Its log is below."
    } else {
        $hint = "The player and bridge are running but no messages reach the bridge."
    }
    $lines | ForEach-Object { Write-Host $_ }
    Write-Host "`nNo data arrived. $hint" -ForegroundColor Red
    Write-Host "Everything above is saved in $report - send that file to Zeenat if this doesn't fix it." -ForegroundColor Yellow
    exit 1
}

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
# bag_files.txt lists each .mcap with its exact size: catches wrong names and unfinished downloads.
function CheckBag($dir) {
    $list = Join-Path $dir "bag_files.txt"
    if (-not (Test-Path $list)) { return "ok" }
    foreach ($line in Get-Content $list) {
        if ($line -match '^\s*#' -or -not $line.Trim()) { continue }
        $name, $size = ($line -split '\s+')[0, 1]
        $f = Join-Path $dir $name
        if (Test-Path $f) {
            $have = (Get-Item $f).Length
            if ($have -ne [int64]$size) {
                return "$name is $([math]::Round($have / 1GB, 2)) GB but should be $([math]::Round([int64]$size / 1GB, 2)) GB. The download is incomplete or damaged: download it again."
            }
            continue
        }
        $other = Get-ChildItem $dir -Filter "*.mcap*" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($other) { return "Found '$($other.Name)' but expected '$name'. Rename it to $name (exactly), then run this again." }
        return "missing"
    }
    return "ok"
}
if (-not $Bag) {
    $state = CheckBag $NewBag
    if ($state -eq "ok") { $Bag = $NewBag }
    elseif ($state -eq "missing") {
        Write-Host "The new bag (HCI-bag-v2) is not downloaded yet, so using the small autonomy_demo_slim bag." -ForegroundColor Yellow
        Write-Host "To get it, see Dataset\HCI-bag-v2\README.md"
        $Bag = $SlimBag
    }
    else { Fail "Problem with the new bag in $NewBag`n$state" }
} else {
    $state = CheckBag $Bag
    if ($state -ne "ok") { Fail "Problem with the bag in $Bag`n$(if ($state -eq 'missing') { 'The .mcap file is missing.' } else { $state })" }
}
if (-not (Test-Path (Join-Path $Bag "metadata.yaml"))) {
    Fail "No bag found in:`n  $Bag`nRun 'git pull' in the repo folder (the folder must contain metadata.yaml and the .mcap file)."
}
function VmPath($p) { $f = (Resolve-Path $p).Path; "/mnt/" + $f.Substring(0, 1).ToLower() + ($f.Substring(2) -replace '\\', '/') }   # C:\x\y -> /mnt/c/x/y
$vmPath = VmPath $Bag
$webPath = VmPath $PSScriptRoot        # Implementation folder: dashboard\ and client\ are served from here
Write-Host "Using $((Resolve-Path $Bag).Path)"

# 3. Image
Step "Downloading the latest image (first time ~1 GB)"
podman pull $Image
if ($LASTEXITCODE -ne 0) { Fail "Could not download $Image. Check your internet connection." }

# 4. Bag volume + pod
Step "Starting the pod"
podman volume rm -f cavs-bag cavs-web 2>&1 | Out-Null
podman volume create --opt type=none --opt o=bind --opt "device=$vmPath" cavs-bag | Out-Null
if ($LASTEXITCODE -ne 0) { Fail "Could not connect the bag folder to Podman." }
podman volume create --opt type=none --opt o=bind --opt "device=$webPath" cavs-web | Out-Null
if ($LASTEXITCODE -ne 0) { Fail "Could not connect the dashboard folder to Podman." }
podman kube play $PodYml | Out-Null
if ($LASTEXITCODE -ne 0) { Fail "Could not start the pod. See the messages above." }

# 5. Wait for the bridge, then open the probe page
Write-Host "Waiting for data (up to 90 s)..."
$ok = $false
for ($i = 0; $i -lt 45 -and -not $ok; $i++) {
    Start-Sleep -Seconds 2
    Write-Host "." -NoNewline
    try { $ok = (Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8765/stats" -TimeoutSec 2).Content -match "/mtx/odom" } catch {}
}
Write-Host ""
if (-not $ok) { Diagnose }

Write-Host "`nRunning. Dashboard: http://localhost:8765/dashboard/   Probe page: http://localhost:8765/   Websocket: ws://localhost:8765/" -ForegroundColor Green
Write-Host "To stop: double-click stop-windows.bat"
Start-Process "http://localhost:8765/dashboard/"
