# Running CAVS-1 on a Linux server

Author: Zeenat Islam · 19 Nov 2026

The same pod the team runs on laptops: a bag player and the websocket bridge. The bridge also serves the dashboard.
Everyone opens one address; they all see the same playback, and each viewer picks their own camera.

> **Not for the CAVS server.** It runs only on the MTX's local network with no outside connections
> (Dr Hudson, 19 Nov 2026), so the team could not reach it. Use this guide for another Linux machine on the
> campus network, such as a lab PC or a department VM. Until then, everyone runs the pod on their own laptop.

## What the server needs
- Linux on x86-64 or ARM64, with **Podman 4+** or **Docker with Compose v2**, and git
- About 30 GB free disk (the bag is 22.6 GB) and 4 CPU cores
- One TCP port for viewers: 8765, or 443 if a web server is put in front (below)

## 1. Code and bag
```
git clone https://github.com/islamzee/HCI_CAVS_1.git
cd HCI_CAVS_1
```
Put `hopefully_fixed_0.mcap` in `Dataset/HCI-bag-v2/` (steps and checksum in `Dataset/HCI-bag-v2/README.md`).
From a terminal without a browser (gdown, not yet tried with this 22.6 GB file; if it fails, download on a
laptop and copy it over with `scp`):
```
pip install gdown
gdown --folder https://drive.google.com/drive/folders/1NN1eshRpos7RX6fKIeVO24Sm2WY_8IMH -O Dataset/HCI-bag-v2
sha256sum Dataset/HCI-bag-v2/hopefully_fixed_0.mcap     # must match bag_files.txt
```

## 2a. Start with Podman
```
cd Implementation
IMAGE=ghcr.io/islamzee/hci_cavs_1/cavs-bag-bridge:latest ./pod.sh up
```
`pod.sh` checks the bag, labels the folders for SELinux when it is on (RHEL, Rocky, Fedora), and starts the
containers with `--restart=always`. To start them again after a reboot (once, as the same user):
```
systemctl --user enable --now podman-restart.service
sudo loginctl enable-linger $USER          # lets that user's containers run without a login session
```
Stop: `./pod.sh down`. Logs: `./pod.sh logs player` or `./pod.sh logs bridge`.

## 2b. Or start with Docker
```
cd Implementation
docker compose up -d                       # uses ../Dataset/HCI-bag-v2; another bag: BAG_DIR=/path docker compose up -d
```
`restart: unless-stopped` brings it back after a reboot (Docker's service must be enabled:
`sudo systemctl enable docker`). Stop: `docker compose down`. Logs: `docker compose logs -f player`.
Use `docker-compose.yml` with Docker only; on Podman use `pod.sh`.

## 3. Open it
`http://<server>:8765/dashboard/` (probe page: `http://<server>:8765/`, receive counts: `/stats`).
If it doesn't load from another machine, open the port:
```
sudo firewall-cmd --add-port=8765/tcp --permanent && sudo firewall-cmd --reload   # RHEL / Rocky / Fedora
sudo ufw allow 8765/tcp                                                           # Ubuntu
```

## 4. Optional: behind the department web server (HTTPS)
Point a path on the existing web server at the bridge. nginx (tested with the path `/cavs/`):
```
location /cavs/ {
    proxy_pass http://127.0.0.1:8765/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;      # the live data is a websocket
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 1h;
}
```
The dashboard is then `https://<server>/cavs/dashboard/`. It finds the data through the same address on its
own (wss:// under https), so nothing else changes. Then port 8765 can stay closed to the outside.

## Updating
- Dashboard (HTML/JS/CSS): `git pull`. The server serves the repo folder, so a page reload shows the change.
- Bridge or player (anything else in `Implementation/`): `git pull`, then
  `podman pull ghcr.io/islamzee/hci_cavs_1/cavs-bag-bridge:latest && ./pod.sh restart` with the same `IMAGE=...`,
  or `docker compose pull && docker compose up -d`. GitHub builds the image about 10 minutes after a push.

## Good to know
- **No login.** Anyone who can reach the port sees the dashboard. Viewers can only choose their own camera and
  frame rate; nothing is sent to a vehicle. Keep it on the campus network or VPN, or add a login on the web
  server (e.g. nginx `auth_basic`).
- **ROS on the same server is not affected.** The pod's ROS traffic stays inside the pod (domain 42, localhost
  discovery, its own network), so it does not see or disturb other ROS systems on the machine or network.
- **Load.** One browser gets about 100 kB/s. Playing the full bag reads about 270 MB/s from disk on average, so
  keep the bag on a local disk (not a network share).
- **Several bags at once:** with Docker, run another copy with its own port and bag:
  `PORT=8766 BAG_DIR=../Dataset/autonomy_demo_slim docker compose -p cavs2 up -d`. `pod.sh` runs one pod per user.
