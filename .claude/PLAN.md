# PLAN.md — Author sidecar files for F2

> Macro truth for this customization. Read-heavy, write-rarely.
> Working memory lives in `STATE.md`.

## Problem

Douyin `like` mode loses the per-video **author**. Downloads land in:

```
/mnt/tower/VIDEO/Platform/DOUYIN/f2/Download/douyin/like/震动哥/<{create}_{desc}>/
    <name>_video.mp4
    <name>_music.mp3
    <name>_desc.txt
```

**26,058 leaf folders**, all under the single top folder `震动哥` — which is the *liker*
(the account whose likes are downloaded), not the creator. Each liked video has a
different author, recorded nowhere. A folder's only identity today is
`create_time` + a truncated, `replaceT`-sanitized description.

The data is already in memory and discarded: `UserPostFilter`
(`f2/apps/douyin/filter.py:176-190`) exposes `nickname`, `nickname_raw`, `uid`,
`sec_user_id` from `$.aweme_list[*].author.*`, and `_to_list()` (`filter.py:343-367`)
passes all of them into `aweme_data_dict` at `f2/apps/douyin/dl.py:112`. The default
`naming` template simply never references them.

## Goal

A configurable sidecar file — default `Authors-{nickname}.txt` — written into each
work's folder, across all four apps, driven entirely from the yaml config.

## Hard constraints

- **Never change `naming`.** It drives both the folder (`dl.py:112-117`) *and* every
  file basename (`dl.py:153, 168, 189, 201, 222, 240`). The skip check is purely
  `full_path.exists()` (`f2/dl/base_downloader.py:527, 575, 622`) with no manifest DB
  (`douyin_videos.db` is never populated in like mode — call sites commented out at
  `handler.py:363, 488-494`). Touching `naming` would orphan all 26,058 folders and
  re-download every video.
- **Opt-in.** An absent `authors` key must be falsy in every config layer, so existing
  setups are byte-for-byte unaffected. Do not add the key to `f2/conf/app.yaml`.
- **The repo IS the timer env.** pip editable install; `_f2.pth` in
  `/home/ubuntu-2204-test-1/.conda/envs/python4f2` points here. Saving a file changes
  what the systemd timer runs. No reinstall step exists.
- **Testing never touches the NAS.** Only `.claude/test/` (local disk, gitignored)
  with a small `max_counts`.

## Design decisions (locked with the user)

| Decision | Choice |
|---|---|
| Scope | All 4 apps: douyin, tiktok, twitter, weibo |
| Configurable | Filename template **and** content field list |
| Field vocabulary | Canonical names, mapped per app |
| Unavailable field | Omit the line, log at DEBUG |
| Author renamed | Write both files |
| Currency marker | File mtime **and** a `seen_at` line |
| Backfill | Drip via the existing timers |
| Rollout | Code + read-only coverage script; user refreshes cookie and edits live `dy.yaml` |

## Config surface (per app, `f2/conf/defaults.yaml`)

```yaml
douyin:
  authors:                              # bool, absent/false = OFF
  authors_naming: 'Authors-{nickname}'  # filename stem, .txt appended
  authors_fields:                       # canonical names, order preserved
    - nickname
    - nickname_raw
    - author_id
    - author_handle
    - work_id
    - create_time
    - author_url
    - work_url
    - seen_at
```

## Canonical field registry

| Canonical | douyin | tiktok | twitter | weibo |
|---|---|---|---|---|
| `nickname` | `nickname` | `nickname` | `nickname` | `nickname` |
| `nickname_raw` | `nickname_raw` | `nickname_raw` | `nickname_raw` | `nickname_raw` |
| `author_id` | `uid` | `uid` | `user_id` | `uid` |
| `author_handle` | `sec_user_id` | `uniqueId` | `user_unique_id` | *(none)* |
| `work_id` | `aweme_id` | `aweme_id` | `tweet_id` | `weibo_id` |
| `work_type` | `aweme_type` | `aweme_type` | *(none)* | *(none)* |
| `create_time` | `create_time` | `createTime` | `tweet_created_at` | `weibo_created_at` |
| `desc` | `desc` | `desc` | `tweet_desc` | `weibo_desc` |

Computed, not looked up on the data dict:

- `author_url` — douyin `https://www.douyin.com/user/{author_handle}` ·
  tiktok `https://www.tiktok.com/@{author_handle}` ·
  twitter `https://x.com/{author_handle}` · weibo `https://weibo.com/u/{author_id}`
- `work_url` — douyin `https://www.douyin.com/video/{work_id}` ·
  tiktok `https://www.tiktok.com/@{author_handle}/video/{work_id}` ·
  twitter `https://x.com/{author_handle}/status/{work_id}` ·
  weibo `https://weibo.com/{author_id}/{work_id}`
- `seen_at` — `timestamp_2_str(get_timestamp("sec"))`

Weibo has no `author_handle`; that line and any URL depending on it are omitted.

## Why a new validator was needed

`check_invalid_naming` (`f2/utils/utils.py:425`) strips known `{patterns}` then requires
**every remaining character** to be a separator (`:441-452`). The literal `Authors` in
`'Authors-{nickname}'` is therefore rejected character by character. Hence
`check_invalid_sidecar_naming`, which validates `{placeholders}` against the canonical
vocabulary and allows filesystem-safe literal text.

## File content

Written once, never rewritten (exact-filename skip). `key: value`, one per line, in the
order given by `authors_fields`:

```
nickname: 震动哥
nickname_raw: 震动哥🌟
author_id: 60312345678
author_handle: MS4wLjABAAAApQB2zNdf...
work_id: 7123456789012345678
create_time: 2024-04-02 06-23-54
author_url: https://www.douyin.com/user/MS4wLjABAAAApQB2zNdf...
work_url: https://www.douyin.com/video/7123456789012345678
seen_at: 2026-08-07 01-32-00
```

This puts `work_id` on disk for the first time, permanently fixing folder identity.

## Backfill mechanism

No separate script. `handle_user_like` (`handler.py:471`) always walks from
`max_cursor=0` — there is no `--max-cursor` option anywhere, and `last_aweme_id` is
written (`dl.py:149`) but never read, and in like mode the write is a silent no-op
because it targets the *author's* `sec_user_id`, which is never a row in
`douyin_users.db` (`db.py:90-97` selects first). So enabling the option and re-running
recomputes the same `base_path`, skips all media, and writes only the sidecar.

## Known environment blockers (not code)

1. **Cookie.** Every trace log since ~Aug 5 ends in `403 Forbidden` on the favorite
   endpoint; the last two runs produced 0-byte logs. `sid_guard` declares an expiry of
   12 Jul 2026. Note some 403s are rate-limiting — a healthy Aug-3 run logged 13 of them.
2. **`timeout` is dual-purpose.** `handler.py:568` sleeps `timeout` seconds between
   pages; `f2/crawlers/base_crawler.py:106` uses the same value as the HTTP timeout. At
   `timeout: 30` / `page_counts: 10`, a full 26k walk is ~2,600 pages ≈ 22h of sleeping
   alone — which is why the hourly `f2.service` can never finish one and only the 24h
   `f2-c.service` makes progress.

## Roadmap

- [ ] Shared sidecar core in `f2/utils/utils.py`
- [ ] Per-app field maps + wrappers in `f2/apps/*/utils.py`
- [ ] `download_authors` writer in `f2/apps/*/dl.py`
- [ ] CLI options, help rows, `defaults.yaml` keys
- [ ] Unit tests
- [ ] Read-only coverage script
- [ ] Sandbox verification (`.claude/test/` only)
