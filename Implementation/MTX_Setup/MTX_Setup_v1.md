# Running CAVS-1 on the MTX

Author: Zeenat Islam · 20 Nov 2026

The MTX computer has no internet, so everything is brought over on a USB drive. The dashboard then replays a
bag that is already on the MTX. Nothing in the code changes; `pod.env` tells it which bag to use.

## 1. Before you go: check the MTX (ask whoever has access)
- Podman is installed: `podman --version` shows 4 or newer.
- Processor type: `uname -m` prints `x86_64` (Intel/AMD) or `aarch64` (ARM). Needed in step 2.

## 2. Prepare the USB drive (on your laptop, with internet)
```
podman pull --platform linux/amd64 ghcr.io/islamzee/hci_cavs_1/cavs-bag-bridge:latest
podman save -o cavs-image-amd64.tar ghcr.io/islamzee/hci_cavs_1/cavs-bag-bridge:latest
```
Use `linux/arm64` instead if the MTX printed `aarch64`. Don't skip `--platform`: a Mac is ARM and would
otherwise save the wrong one.

Copy to the drive:
- `cavs-image-amd64.tar` (Intel/AMD) or `cavs-image-arm64.tar` (ARM), about 1 GB each. Ready-made copies of both are in `MTX_transfer/` at the top of the repo on Zeenat's laptop (made 20 Nov 2026, not in git)
- the repo's `Implementation` folder (`git pull` first). `Dataset` is not needed; the bag is already on the MTX.

## 3. On the MTX: load and set up (once)
```
cp -r /media/<usb>/Implementation ~/cavs
podman load -i /media/<usb>/cavs-image-amd64.tar     # or cavs-image-arm64.tar on an ARM MTX
cd ~/cavs
cp pod.env.example pod.env
nano pod.env
```
In `pod.env`, set `BAG_DIR` to the bag folder, then save (Ctrl+O, Enter) and exit (Ctrl+X):
```
BAG_DIR=/full/path/to/their/bag
IMAGE=ghcr.io/islamzee/hci_cavs_1/cavs-bag-bridge:latest
```
`BAG_DIR` is the folder that contains `metadata.yaml` and the `.mcap` file. Use the full path, no spaces around
`=`, no quotes. To find bag folders: `find / -name metadata.yaml 2>/dev/null`

## 4. Run it
```
./pod.sh up
```
- It prints `Bag: /full/path/to/their/bag`. If it says `autonomy_demo_slim` instead, `pod.env` was not read:
  check the file name (`pod.env`, in the same folder as `pod.sh`) and the format above.
- After about 10 seconds, `./pod.sh topics` should list `/mtx/odom` and other topics, and show a rate.

## 5. Open the dashboard
- On the MTX itself: http://localhost:8765/dashboard/
- From a laptop or tablet on the MTX network: run `hostname -I` on the MTX for its address, then open
  `http://<address>:8765/dashboard/`. If localhost works but this doesn't, the MTX firewall blocks port 8765;
  ask whoever manages the MTX.

## 6. When you're done
```
./pod.sh down
```
Always stop it: it keeps reading the bag, and the MTX is the vehicle's computer.

## If something goes wrong
| What you see | What to do |
|---|---|
| Dashboard says it's waiting for data | `./pod.sh logs player` and `./pod.sh logs bridge` show why |
| Some panels empty, others fine | That bag doesn't have those topics; nothing to fix in the setup |
| `./pod.sh logs bridge` says "exec format error" | Wrong processor type: redo step 2 with the other `--platform` |
| `./pod.sh up` says the pod already exists | `./pod.sh down`, then `./pod.sh up` |

## Other commands
- Another bag for one run: `BAG_DIR=/other/bag ./pod.sh up`
- Slower playback: `RATE=0.5 ./pod.sh up`
- Restart: `./pod.sh restart` · status: `./pod.sh status`
