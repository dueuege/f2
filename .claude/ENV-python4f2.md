# ENV-python4f2.md — the conda environment behind the systemd timer

> Analysis of how F2 is installed and updated on this machine.
> Written 2026-08-07. Companion to `PLAN.md` and `STATE.md`.

## TL;DR

**`python4f2` is the timer environment, and F2 is installed into it as a pip
*editable* install pointing straight at this repo.** There is no copy of the code in
`site-packages` — only a `.pth` file containing the repo path. Consequently:

- **Editing a file in this repo *is* the deployment.** The next timer fire runs it.
- **There is no update step, and none is needed.** No `pip install` to run.
- **`pip install -U f2` would silently destroy the customization** — see "Hazards".

## The environment

| | |
|---|---|
| Path | `/home/ubuntu-2204-test-1/.conda/envs/python4f2` |
| Python | 3.11.15 |
| conda | 25.11.1 (base at `~/anaconda3`) |
| F2 version | 0.0.1.7 |
| Installer | `pip` |
| Install mode | **editable** |
| `uv` | not installed on this machine |

Key packages: `httpx 0.28.1`, `click 8.1.7`, `rich 13.9.3`, `PyYAML 6.0.2`,
`aiosqlite 0.20.0`, `browser-cookie3 0.20.1`, `pytest 8.3.4`.

## How the editable install works

`site-packages` holds only metadata plus a one-line path file:

```
$CONDA_PREFIX/lib/python3.11/site-packages/
    f2-0.0.1.7.dist-info/
        INSTALLER      -> pip
        direct_url.json -> {"dir_info": {"editable": true},
                            "url": "file:///home/.../Documents/programming/github/f2"}
    _f2.pth            -> /home/ubuntu-2204-test-1/Documents/programming/github/f2
```

At interpreter start, `site` reads `_f2.pth` and appends that directory to `sys.path`.
So `import f2` resolves to the repo:

```bash
$ ~/.conda/envs/python4f2/bin/python -c "import f2; print(f2.__file__)"
/home/ubuntu-2204-test-1/Documents/programming/github/f2/f2/__init__.py
```

This corresponds to `pip install -e .` — the "开发安装 / development install" documented
in `docs/install.md:96`, not the ordinary `pip install f2` at `docs/install.md:43`.

## How the timer reaches it

`~/Documents/programming/script/run_f2.sh`:

```bash
source ~/anaconda3/etc/profile.d/conda.sh
conda activate python4f2          # line 26
F2_BIN="$(which f2)"              # line 43 -> $CONDA_PREFIX/bin/f2
systemd-run --user --unit="$TRANSIENT" --working-directory="$TARGET" \
    -- "$F2_BIN" dy -c dy.yaml    # line 52-53
```

`$TARGET` is `/mnt/tower/VIDEO/Platform/DOUYIN/f2`, so relative paths in `dy.yaml`
(`path: Download`, `logs/`, `douyin_users.db`) resolve on the NAS.

Units: `f2.timer` → `f2.service` → `run_f2.sh` → transient `f2-run.service` (hourly,
force-restarts); `f2-c.timer` → `f2-c.service` → `run_f2_cont.sh` → transient
`f2-cont.service` (24h, skips if already active). They are independent cgroups, so the
hourly restart does **not** kill a long `f2-cont` run.

## Hazards

### 1. `pip install -U f2` would wipe the customization

Upgrading from PyPI replaces the editable install with the published package in
`site-packages`. The timer would silently start running upstream F2 with **no author
sidecar feature**, while this repo sits untouched and apparently fine. Nothing warns you.

If it ever happens, restore with:

```bash
conda run -n python4f2 pip install -e /home/ubuntu-2204-test-1/Documents/programming/github/f2
```

### 2. There are TWO f2 installs, both editable, both pointing here

| Interpreter | Binary | `.pth` location |
|---|---|---|
| conda 3.11.15 | `$CONDA_PREFIX/bin/f2` | `…/python4f2/lib/python3.11/site-packages/_f2.pth` |
| **system 3.10.12** | `/usr/local/bin/f2` | `/usr/local/lib/python3.10/dist-packages/_f2.pth` |

Both resolve `import f2` to this same repo, and the system one works
(`/usr/local/bin/f2 --version` → `Version 0.0.1.7`). **Without conda activated,
`which f2` returns `/usr/local/bin/f2`** — the system-Python one.

Practical effect: if `conda activate python4f2` ever fails inside `run_f2.sh`, line 43
still resolves an `f2` and the job runs — on Python 3.10 instead of 3.11, silently. It
would probably work, since both read the same source, but it is an untested path. To
make the script fail loudly instead, pin the binary:

```bash
F2_BIN="$HOME/.conda/envs/python4f2/bin/f2"
[ -x "$F2_BIN" ] || { echo "$(date): ERROR — f2 not found in python4f2"; exit 1; }
```

### 3. Editing the repo edits production

There is no staging copy. A syntax error saved here takes down the next timer fire. The
sidecar feature itself is safe (it is off unless `authors: true` is in the yaml), but the
*import graph* is shared. Always finish an edit session with:

```bash
~/.conda/envs/python4f2/bin/f2 dy -h     # go/no-go: imports are sound
```

### 4. No `git` CLI on this machine

Only GitKraken (a GUI Electron app) is installed — `/usr/bin/gitkraken`. There is no
`git` binary, so there is no branch, no worktree, and no `git checkout` to revert with.
Back up before large edits, or `sudo apt install git`.

## Current health (2026-08-07 02:45)

`f2-run.service` is in a **failed** state, and it is **not** caused by the sidecar work
and **not** by an expired cookie.

```
FileNotFoundError: [Errno 2] No such file or directory:
    'logs/f2-2026-05-22-23-12-58-1493164-ff13d7d3.log'
  at f2/log/logger.py:131  in clean_logs
  at f2/log/logger.py:187  trace_logger = log_setup(...)
```

`clean_logs` (`f2/log/logger.py:120-135`) globs the log directory, then unlinks the old
files. It catches `PermissionError` but **not `FileNotFoundError`**. The hourly
`f2-run` and the 24h `f2-cont` can run concurrently against the same
`/mnt/tower/.../logs` directory over CIFS, so both compute the same delete list and the
loser hits a file that has already gone. The exception escapes at **module import time**,
so f2 dies before writing anything — which is why the recent logs are 0 bytes.

Two distinct failure eras are visible in the logs, and they have different causes:

| When | Log size | Cause |
|---|---|---|
| ~Aug 5 – Aug 6 22:57 | ~2.4 KB | `403 Forbidden` on the favorite endpoint |
| Aug 6 23:58 onward | **0 bytes** | this `clean_logs` crash, before any output |

Sandbox testing on 2026-08-07 completed a full download with **zero 403s** using the same
cookie, so the cookie is *not* the current blocker. The one-line fix:

```python
log_file.unlink(missing_ok=True)     # f2/log/logger.py:131
```

### FIXED 2026-08-07

`f2/log/logger.py:131` now uses `log_file.unlink(missing_ok=True)` plus a catch-all
`except OSError` that warns instead of raising — log cleanup must never prevent f2 from
starting. Regression test: `tests/test_logger.py::test_clean_logs_survives_vanished_file`
(patches `Path.glob` to return a file that no longer exists).

Not yet confirmed against the NAS: verifying there means letting `clean_logs(99)` run on
the real log directory, which would delete 126 of the 225 files (441 MB). That is f2's
normal designed behavior, but it was left for the next scheduled timer fire rather than
triggered manually.

### Also fixed: `F2_BIN` pinned in both run scripts

`run_f2.sh:46` and `run_f2_cont.sh:45` previously used `F2_BIN="$(which f2)"`, which
would resolve to `/usr/local/bin/f2` (system Python 3.10) if `conda activate` failed.
Both now pin `$HOME/.conda/envs/python4f2/bin/f2` and abort if it is missing.
Timestamped `.bak-*` backups sit beside them.

## Verification commands

```bash
# Which f2 does the timer env import?  (must print this repo)
~/.conda/envs/python4f2/bin/python -c "import f2; print(f2.__file__)"

# Is it still editable?  (must say "editable": true)
cat ~/.conda/envs/python4f2/lib/python3.11/site-packages/f2-0.0.1.7.dist-info/direct_url.json

# Is the sidecar feature present in the timer env?
~/.conda/envs/python4f2/bin/python -c "
from f2.apps.douyin.dl import DouyinDownloader
print('download_authors:', hasattr(DouyinDownloader, 'download_authors'))"

# Import graph sound?  (go/no-go before letting the timer fire)
~/.conda/envs/python4f2/bin/f2 dy -h

# Test suite
~/.conda/envs/python4f2/bin/python -m pytest tests/ -q
```

## Note on `f2 tiktok`

`f2/apps/tiktok/utils.py:1121-1123` calls `TokenManager.gen_real_msToken()` inside a
class body — a **network request at import time**, whose `except` branch retries the same
failing call. With no reachable TikTok endpoint, `f2 tiktok -h` crashes. Pre-existing and
unrelated to the sidecar work, but it means the tiktok code path cannot be exercised in
this environment.
