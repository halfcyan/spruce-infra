# music tools

Library maintenance for Jellyfin's music on pine. Not a service. There are no Quadlet
units here, so `deploy.sh` ignores this directory and editing it never restarts Jellyfin.

## dedupe.py

Keeps one copy of every song in `/mass-storage/bigboi/media/music`, the highest quality
one, and points every playlist at it. Run it on pine after adding downloads:

```sh
cd ~/spruce-infra/hosts/pine/music-tools
./dedupe.py --upgrades ~/music-upgrades.md   # dry run, prints the plan
./dedupe.py --apply
./dedupe.py --undo                           # roll back the last --apply
```

Then rescan the library in Jellyfin.

What counts as the same song:

1. byte-identical files
2. FLACs with the same audio (STREAMINFO md5), which catches retagged or renamed copies
3. same first artist + title (ignoring feat./explicit/remaster suffixes) within 3 seconds

What it keeps:

- quality first: lossless over lossy, then bit depth, then sample rate. FLAC bitrate is
  ignored, it only measures compression.
- each album lives in one folder: the one holding most of it, then the best sounding. If
  a better copy of an album track exists anywhere (a playlist download, a Roon import)
  and its album tag matches, it moves into the album folder under the album track's name.
  The worse copy is quarantined. Albums stay complete, possibly mixed quality.
- when the better copy is tagged for a different album, both are kept
- DRM'd `.m4p` files are quarantined

Playlists:

- every `.m3u`/`.m3u8` that isn't an album playlist is rewritten into `Playlists/` with
  paths relative to that folder, which Jellyfin resolves. Entries are matched by path,
  then by filename or tags, so old `G:\...` playlists from Windows still resolve. Ones
  that can't be matched stay in the file as `# unresolved:` comments.
- numbered playlist download folders (`*/Playlist/<name>/`) become
  `Playlists/<top> - <name>.m3u8` in track-number order, once. After that the file in
  `Playlists/` is the source of truth and later runs only re-point it.
- downloader album playlists (`playlist.m3u8` inside album folders) are retired.

`--upgrades FILE` writes a table of albums worth re-downloading: some track has a
better copy elsewhere, or the album is mixed quality after swaps. After re-downloading
one, drop it into the library and re-run. The new copy wins and the old one is
quarantined.

Nothing is deleted. Everything that leaves the library is renamed into
`/mass-storage/bigboi/dupes-quarantine/music/` (same btrfs subvolume, so it's instant),
and each run writes a `manifest-<time>.tsv` there for `--undo`. Delete the quarantine
by hand once Jellyfin looks right.

Scan results are cached in `~/.cache/music-dedupe/scan.jsonl`, so re-runs only probe new
or changed files.
