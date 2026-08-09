# STATE.md — working memory (keep < 200 lines, prune aggressively)

## Current Active Task

**Implementation COMPLETE and verified in the sandbox (2026-08-07).**
Nothing is live yet — the feature is off until the user adds `authors: true` to
`/mnt/tower/VIDEO/Platform/DOUYIN/f2/dy.yaml`.

## Current Execution Plan

1. [x] `f2/utils/utils.py` — shared core: `SIDECAR_CANONICAL_FIELDS`,
       `SIDECAR_DEFAULT_FIELDS`, `SIDECAR_DEFAULT_NAMING`, `SIDECAR_NAME_LIMIT`,
       `inline_text`, `check_invalid_sidecar_naming`, `resolve_sidecar_fields`,
       `format_sidecar_name`, `format_sidecar_content`
2. [x] `f2/apps/{douyin,tiktok,twitter,weibo}/utils.py` — `AUTHOR_FIELD_MAP`,
       `AUTHOR_URL_TEMPLATES`, `format_author_file_name`, `format_author_file_content`
3. [x] `f2/apps/{douyin,tiktok,twitter,weibo}/dl.py` — `download_authors`
4. [x] `f2/apps/{douyin,tiktok,twitter,weibo}/{cli,help}.py` — `--authors/-a`,
       `--authors-naming`
5. [x] `f2/conf/defaults.yaml` — 3 keys × 4 app blocks
6. [x] `tests/test_author_sidecar.py` — 39 tests, all pass; full suite 139 pass
7. [x] `~/Documents/programming/script/check_authors_coverage.py` (read-only)
8. [x] Sandbox verification in `.claude/test/`

## Verification results (sandbox, local disk only)

- **Feature OFF → 0 sidecars written.** The live pipeline is unaffected until opted in.
- **Feature ON → 20 sidecars**, each inside the existing work folder next to the
  `_video.mp4`. Folder structure unchanged.
- **Re-run → 0 rewritten, 0 added, 0 removed, 0 videos re-downloaded.** `seen_at` is
  non-deterministic, so an unchanged file proves the exact-filename skip fired. This is
  the idempotency proof that makes drip-mode backfill safe across interrupted runs.
- Cookie in `.claude/test/dy.yaml` **works** — no 403 during testing. The NAS 403s are
  therefore more likely rate-limiting than a dead cookie, but the live pipeline should
  still be re-checked.

## Also fixed this session (outside the sidecar scope)

- **`clean_logs` crash** (`f2/log/logger.py:131`) — `unlink(missing_ok=True)` + catch-all
  `OSError` warning. This bug crashed f2 at **import time**, killing every hourly run
  since Aug 6 23:58 (0-byte logs). Cause: hourly and 24h jobs clean the same CIFS log
  directory concurrently; the loser hits an already-deleted file. Regression test added.
  **Not yet confirmed against the NAS** — see `ENV-python4f2.md`.
- **`F2_BIN` pinned** in `run_f2.sh` / `run_f2_cont.sh` to
  `$HOME/.conda/envs/python4f2/bin/f2`. `which f2` could fall through to
  `/usr/local/bin/f2` (system Python 3.10) if `conda activate` failed. `.bak-*` backups made.

## Next immediate step (user action)

1. `authors: true` → `/mnt/tower/VIDEO/Platform/DOUYIN/f2/dy.yaml`
2. Baseline: `check_authors_coverage.py` (expect `0 / 26058`)
3. Re-check coverage after a few days of drip to confirm progress

## Caught during implementation (do not regress)

`format_sidecar_name` must raise `KeyError` on a placeholder outside the canonical
vocabulary. `authors_naming` set in the **yaml bypasses the click callback entirely**
(`merge_config` just merges the value), so without that check a typo would have
silently produced 26k files all named `Authors-unknown.txt`. Covered by
`test_name_unknown_placeholder_raises`.

## Hard-won facts (do not re-derive)

- **`check_invalid_naming` cannot validate `'Authors-{nickname}'`.** It strips known
  `{patterns}` then requires every remaining char to be a separator
  (`f2/utils/utils.py:441-452`), so the literal `Authors` fails char by char. A separate
  validator is required.
- **Skip logic is purely `full_path.exists()`** on the exact filename
  (`f2/dl/base_downloader.py:527, 575, 622`). That is what makes "write both on rename"
  free — no glob pre-check needed — and what makes the backfill idempotent.
- **`_to_list()` already carries the author.** `nickname`, `nickname_raw`, `uid`,
  `sec_user_id`, `aweme_id`, `create_time` are all in `aweme_data_dict` at `dl.py:112`.
- **`nickname` is already `replaceT`'d** in the filter — regex
  `[^一-龥a-zA-Z0-9#]` → `_` (`f2/utils/utils.py:328-347`). Filesystem-safe, but
  unlike `desc` it is *not* length-capped, so cap it explicitly.
- **`_()` falls back to the raw msgid** when a catalog entry is missing
  (`f2/i18n/translator.py:74-78`), so new strings need no `.po`/`.mo` work.
  `make_pot.sh` is broken anyway — it expects `.po` files not in the tree.
- **`merge_config` has no schema** (`f2/utils/utils.py:467-507`): app.yaml < user yaml <
  CLI, and only non-`None`/non-`""` values override. An absent key is simply absent.
- **`base_path` differs per app.** Douyin uses `self.base_path` (`dl.py:112`);
  tiktok (`dl.py:170`), twitter (`dl.py:100`), weibo (`dl.py:88`) use a *local*
  variable, so the writer must be called inline where it is in scope.
- **No `git` CLI on this machine** — only GitKraken (GUI). No branch/worktree isolation
  and no `git checkout` to revert with.
- **Install is pip-editable into conda `python4f2`**, `_f2.pth` → this repo. Editing a
  file here changes what the systemd timer runs. There is no reinstall step.

## Blockers / cautions

- **Do NOT run f2 against `/mnt/tower`.** Explicit user constraint — it would write into
  the 26k-folder NAS corpus. All testing goes to `.claude/test/` on local disk.
- **`.claude/test/dy.yaml` has `max_counts: 0`** (unlimited) and a cookie byte-identical
  to the NAS one. Use a separate test config with a small cap; do not edit theirs.
- Feature must stay OFF for the live pipeline until the user adds `authors: true`
  themselves. The only live risk from editing this repo is a syntax/import error, so
  keep the tree importable and finish with `f2 dy -h` as the go/no-go check.

## Dead ends (do not retry)

- Changing `naming` to `{create}_{nickname}_{desc}` — re-downloads all 26k works.
- `douyin_videos.db` as an author source — never populated in like mode.
- Historical logs as an author source — the line carrying author is `logger.debug` and
  the root logger is pinned to INFO (`f2/log/logger.py:64`); zero hits for 作者 in 2024 logs.
