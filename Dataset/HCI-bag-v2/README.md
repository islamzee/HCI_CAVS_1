# HCI-bag-v2 (hopefully_fixed_0)

Recorded 16 Nov 2026 · 85 s · 88 topics · 22.6 GB. What changed since autonomy_demo_0: `HCI_bag_issue_status.pdf`.

The `.mcap` file is too large for GitHub, so it is shared separately. This folder already has
`metadata.yaml` and `bag_files.txt` from the repo; you only add the `.mcap`.

## Get the bag (once)

1. `git pull` in the repo.
2. Open the shared Google Drive folder:
   https://drive.google.com/drive/folders/1NN1eshRpos7RX6fKIeVO24Sm2WY_8IMH?usp=sharing
   and download the file **hopefully_fixed_0.mcap** itself: right-click the file → Download. Don't use
   "Download" on the whole folder: Drive then makes zip files, and a 22 GB file may be split across several.
   Drive says it can't scan the file for viruses because it is large; choose "Download anyway".
   It is 22.6 GB, so make sure you have about 25 GB free. Ask Zeenat if the link doesn't work.
3. Move it into this folder, so you have:
   ```
   HCI_CAVS_1\Dataset\HCI-bag-v2\hopefully_fixed_0.mcap
   HCI_CAVS_1\Dataset\HCI-bag-v2\metadata.yaml
   HCI_CAVS_1\Dataset\HCI-bag-v2\bag_files.txt
   ```
4. The name must be exactly `hopefully_fixed_0.mcap`. If your browser saved it as
   `hopefully_fixed_0 (1).mcap` or `hopefully_fixed_0-001.mcap`, rename it.
5. Run `Implementation\start-windows.bat` (Windows) or `./pod.sh up` (macOS) as usual. They use this bag
   automatically when the file is here, and the window says "Using ...\HCI-bag-v2".

The start scripts check the name and the exact size (`bag_files.txt`) before starting. If the download stopped
early or the file is renamed, the window says so. Until the file is here, they use the small
`autonomy_demo_slim` bag instead.

## Rules
- Don't commit the `.mcap` (git ignores it already) and don't rename the folder.
- Keep the repo outside OneDrive, e.g. `C:\HCI_CAVS_1`. OneDrive may keep only an online copy of a 22 GB file,
  and the pod can't read that.

## Check the file (optional)
The checksum is the last column of `bag_files.txt`.
- Windows PowerShell: `Get-FileHash .\hopefully_fixed_0.mcap -Algorithm SHA256`
- macOS: `shasum -a 256 hopefully_fixed_0.mcap`

The result must match (Windows prints it in capitals; that's fine). Takes a few minutes.
