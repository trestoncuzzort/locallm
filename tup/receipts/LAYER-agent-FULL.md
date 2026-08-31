# tup layer: agent — the whole cost, measured

Installing an AI coding agent onto an operating system, file by file.
Nobody publishes this number, because on an ordinary distribution nobody
can compute it. tup can, because the base system's inventory is complete.

- before: `INVENTORY-20260831T111051Z.txt` (65,284 files)
- after:  `INVENTORY-20260831T111648Z.txt` (70,128 files)
- **added: 4,844**   removed: 0   **modified: 1**

## Where the files went

| path | files |
|---|---|
| `/opt/node-v24.20.0` | 4,812 |
| `/root/.npm` | 25 |
| `/usr/bin` | 4 |
| `/etc/ssl` | 3 |

## What that means

- **4,812 files are Node itself** — the prebuilt binary, and the
  one thing in tup this machine did not compile. That is the honesty cost of
  the layer, stated in its own page header and visible here as a number.
- **Claude Code itself is 36 files.** It ships as a thin npm package wrapping a
  prebuilt native binary, so the agent is a rounding error beside its runtime.
- **`/etc/profile` is the single MODIFIED file** — the CA-certificates page
  appends SSL_CERT_FILE and NODE_EXTRA_CA_CERTS to it. An earlier version of
  this diff keyed on filename alone and reported 0 modified files; that bug was
  found by an adversarial audit before this layer was ever installed, which is
  why the number above is 1 and not 0.
- **Nothing was removed.** A layer that deletes part of the base would be a
  finding, not a feature.

## The modified file

- `/etc/profile`  `6e9c1e97157a4ab2…` → `fba61961329ccb90…`

## Verify this yourself

```sh
bash tup/inventory.sh /mnt/lfs      # regenerates an inventory
diff <(grep -v '^#' INVENTORY-20260831T111051Z.txt) <(grep -v '^#' INVENTORY-20260831T111648Z.txt)
```
