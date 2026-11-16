#!/usr/bin/env python3
"""Keep one copy of every song in the music library, the best one, and point
playlists at it.

Dry run by default. Pass --apply to move files. Nothing is ever deleted:
everything that leaves the library is renamed into the quarantine tree (same
filesystem), and every run writes a manifest that --undo replays backwards.

Run it on pine as cypress. Only needs Python 3 and ffprobe.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

AUDIO = {'.flac', '.mp3', '.m4a', '.m4p', '.wav', '.ogg', '.opus', '.aac', '.aiff', '.aif', '.wma', '.wv', '.ape'}
LOSSLESS = {'flac', 'alac', 'wavpack', 'ape', 'pcm_s16le', 'pcm_s24le', 'pcm_s32le', 'pcm_s16be', 'pcm_s24be', 'pcm_f32le'}
DRM = {'.m4p'}
SIDECARS = ('.lrc', '.txt')
PLAYLISTS = {'.m3u', '.m3u8'}
PLAYLIST_DIR = 'Playlists'


# scanning

def flac_md5(path):
    # STREAMINFO is always the first metadata block. Its last 16 bytes are the
    # md5 of the decoded audio, so it matches across retagged copies
    try:
        with open(path, 'rb') as fh:
            head = fh.read(42)
    except OSError:
        return None
    if head[:4] != b'fLaC' or (head[4] & 0x7f) != 0:
        return None
    md5 = head[26:42].hex()
    return None if md5 == '0' * 32 else md5


def probe(path):
    try:
        out = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams',
             '-select_streams', 'a:0', path],
            capture_output=True, timeout=120).stdout
        d = json.loads(out or b'{}')
    except (subprocess.SubprocessError, ValueError):
        return {}
    fmt = d.get('format', {})
    st = (d.get('streams') or [{}])[0]
    tags = {k.lower(): v for k, v in (st.get('tags') or {}).items()}
    tags.update({k.lower(): v for k, v in (fmt.get('tags') or {}).items()})
    return {
        'artist': tags.get('artist', ''),
        'albumartist': tags.get('album_artist', tags.get('albumartist', '')),
        'title': tags.get('title', ''),
        'album': tags.get('album', ''),
        'track': tags.get('track', ''),
        'disc': tags.get('disc', ''),
        'duration': float(fmt.get('duration') or 0),
        'codec': st.get('codec_name', ''),
        'bits': int(st.get('bits_per_raw_sample') or st.get('bits_per_sample') or 0),
        'rate': int(st.get('sample_rate') or 0),
        'bitrate': int(fmt.get('bit_rate') or 0),
    }


def file_hash(path):
    h = hashlib.blake2b(digest_size=16)
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def scan(lib, cache_path):
    cache = {}
    if os.path.exists(cache_path):
        with open(cache_path) as fh:
            for line in fh:
                r = json.loads(line)
                cache[r['path']] = r

    paths = []
    for dp, dn, fn in os.walk(lib):
        dn.sort()
        for f in sorted(fn):
            if os.path.splitext(f)[1].lower() in AUDIO:
                paths.append(os.path.relpath(os.path.join(dp, f), lib))

    def one(rel):
        full = os.path.join(lib, rel)
        st = os.stat(full)
        old = cache.get(rel)
        if old and old['size'] == st.st_size and old['mtime'] == st.st_mtime:
            return old
        r = {'path': rel, 'size': st.st_size, 'mtime': st.st_mtime}
        r['flac_md5'] = flac_md5(full) if rel.lower().endswith('.flac') else None
        r.update(probe(full))
        return r

    def stale(rel):
        old = cache.get(rel)
        if not old:
            return True
        st = os.stat(os.path.join(lib, rel))
        return old['size'] != st.st_size or old['mtime'] != st.st_mtime

    fresh = sum(map(stale, paths))
    if fresh:
        print(f'probing {fresh} new or changed files', file=sys.stderr)
    with ThreadPoolExecutor(8) as ex:
        recs = list(ex.map(one, paths))

    # full hashes only where sizes collide
    by_size = defaultdict(list)
    for r in recs:
        by_size[r['size']].append(r)
    for group in by_size.values():
        if len(group) > 1:
            for r in group:
                if not r.get('hash'):
                    r['hash'] = file_hash(os.path.join(lib, r['path']))

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    tmp = cache_path + '.tmp'
    with open(tmp, 'w') as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    os.replace(tmp, cache_path)
    return recs


# matching

def norm(s):
    s = unicodedata.normalize('NFKD', s or '').lower()
    s = re.sub(r'\s*[(\[](feat|ft|with)\.?[^)\]]*[)\]]', '', s)
    s = re.sub(r'\s*[(\[]explicit[)\]]', '', s)
    s = re.sub(r'\s*-\s*(\d{4}\s*)?remaster(ed)?\b.*', '', s)
    return re.sub(r'[^a-z0-9]+', '', s)


def first_artist(r):
    return norm(re.split(r'[,;&/]| x | feat', r.get('artist') or '')[0])


def quality(r):
    if r.get('codec') in LOSSLESS:
        return (1, r.get('bits', 0), r.get('rate', 0), 0)
    return (0, 0, 0, r.get('bitrate', 0))


def qstr(r):
    if r.get('codec') in LOSSLESS:
        return f"{r.get('bits')}/{(r.get('rate') or 0) / 1000:g}"
    return f"{r.get('codec')} {r.get('bitrate', 0) // 1000}k"


def tagscore(r):
    return sum(bool(r.get(k)) for k in ('title', 'artist', 'album', 'track', 'albumartist'))


def is_dump(path):
    # playlist downloads: anything under a "Playlist" folder or a "... Liked Songs" folder
    parts = path.split('/')[:-1]
    return any(p.lower() in ('playlist', 'playlists') or p.lower().endswith('liked songs') for p in parts)


def album_key(r):
    if not r.get('album'):
        return None
    artist = norm(re.split(r'[,;&/]', r.get('albumartist') or r.get('artist') or '')[0])
    disc = (r.get('disc') or '1').split('/')[0].strip() or '1'
    return (artist, norm(r['album']), disc)


def group_songs(recs):
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    for field in ('hash', 'flac_md5'):
        g = defaultdict(list)
        for r in recs:
            if r.get(field):
                g[r[field]].append(r['path'])
        for v in g.values():
            for p in v[1:]:
                union(v[0], p)

    # same artist + title within 3 seconds is the same song in another file
    fz = defaultdict(list)
    for r in recs:
        t = norm(r.get('title'))
        if t:
            fz[(first_artist(r), t)].append(r)
    for v in fz.values():
        v.sort(key=lambda r: r.get('duration', 0))
        for a, b in zip(v, v[1:]):
            if abs(a.get('duration', 0) - b.get('duration', 0)) <= 3:
                union(a['path'], b['path'])

    songs = defaultdict(list)
    for r in recs:
        songs[find(r['path'])].append(r)
    return list(songs.values())


# planning

def plan(lib, recs):
    """Returns (ops, final_of, report). final_of maps every scanned path to the
    path its song ends up at (or None if the song leaves the library)."""
    byp = {r['path']: r for r in recs}
    dir_albums = defaultdict(Counter)
    for r in recs:
        k = album_key(r)
        if k:
            dir_albums[os.path.dirname(r['path'])][k] += 1

    def in_album_folder(r):
        k = album_key(r)
        return bool(k) and not is_dump(r['path']) and dir_albums[os.path.dirname(r['path'])][k] >= 2

    # pick one folder per album: the one holding most of it, then the best sounding
    folders = defaultdict(lambda: defaultdict(list))
    for r in recs:
        if in_album_folder(r):
            folders[album_key(r)][os.path.dirname(r['path'])].append(r)
    primary = {}
    for k, dirs in folders.items():
        primary[k] = max(dirs, key=lambda d: (len(dirs[d]), min(quality(r) for r in dirs[d]),
                                              sum(map(tagscore, dirs[d])), [-ord(c) for c in d]))

    songs = group_songs(recs)
    ops = []
    final_of = {}
    report = Counter()
    kept_both = []
    swaps = []
    album_tracks = defaultdict(list)
    taken = set(r['path'] for r in recs)

    def best_of(cands, prefer_dir=None):
        return max(cands, key=lambda r: (quality(r), os.path.dirname(r['path']) == prefer_dir,
                                         in_album_folder(r), not is_dump(r['path']), tagscore(r),
                                         [-ord(c) for c in r['path']]))

    for copies in songs:
        playable = [r for r in copies if os.path.splitext(r['path'])[1].lower() not in DRM]
        if not playable:
            for r in copies:
                ops.append(('quarantine', r['path']))
                final_of[r['path']] = None
            report['drm-only songs'] += 1
            continue

        best = best_of(playable)
        album_keys = sorted({album_key(r) for r in playable if in_album_folder(r)})
        keep = []  # (file record, destination path)
        for k in album_keys:
            # the album's slot is its track in the primary folder, or failing that any album copy
            occupants = [r for r in playable if in_album_folder(r) and album_key(r) == k]
            in_primary = [r for r in occupants if os.path.dirname(r['path']) == primary[k]]
            slot = best_of(in_primary or occupants)
            # fill it with the best copy whose album tag matches
            fill = best_of([r for r in playable if album_key(r) == k], prefer_dir=primary[k])
            base = os.path.splitext(os.path.basename(slot['path']))[0] + os.path.splitext(fill['path'])[1].lower()
            dest = os.path.join(primary[k], base)
            if dest != fill['path'] and dest in taken and dest not in {r['path'] for r in copies}:
                dest = fill['path']  # name collision with some other song, leave it where it is
                report['slot name collisions'] += 1
            if fill is not slot and quality(fill) > quality(slot):
                swaps.append((fill, slot, dest))
            keep.append((fill, dest))
            album_tracks[k].append({'slot': slot, 'fill': fill, 'best': best})
        if not keep:
            keep.append((best, best['path']))
        elif all(quality(f) < quality(best) for f, _ in keep):
            # the best copy is tagged for some other album: keep it too rather than lose it
            keep.append((best, best['path']))
            kept_both.append(best)

        kept_files = {f['path'] for f, _ in keep}
        for r in copies:
            if r['path'] not in kept_files:
                ops.append(('quarantine', r['path']))
        for f, dest in keep:
            if dest != f['path']:
                ops.append(('move', f['path'], dest))
                taken.add(dest)
        # playlists point at the best kept copy
        target = max(keep, key=lambda fd: (quality(fd[0]), fd[1] == best['path']))[1]
        for r in copies:
            final_of[r['path']] = target
        report['songs'] += 1
        report['files removed'] += len(copies) - len(keep)

    # quarantines first so album slots are free before files move into them
    ops.sort(key=lambda o: o[0] != 'quarantine')
    report['hi-res swapped into albums'] = len(swaps)
    report['hi-res kept beside album copy (album tag differs)'] = len(kept_both)
    return ops, final_of, report, swaps, kept_both, byp, album_tracks


def upgrades(album_tracks):
    """Albums worth re-downloading: some track has a better copy elsewhere, or the
    album ends up mixed quality after better copies were swapped in."""
    def tier(r):
        return quality(r)[:3]

    merged = defaultdict(list)
    for k, tracks in album_tracks.items():
        merged[k[:2]].extend(tracks)
    rows = []
    for k, tracks in merged.items():
        before = [t['slot'] for t in tracks]
        after = [t['fill'] for t in tracks]
        top = max((t['best'] for t in tracks), key=quality)
        worse = [t for t in tracks if tier(t['slot']) < tier(t['best'])]
        mixed = len({tier(r) for r in after}) > 1
        if not worse and not mixed:
            continue
        sample = before[0]
        rows.append({
            'artist': sample.get('albumartist') or sample.get('artist') or '?',
            'album': sample.get('album') or '?',
            'have': Counter(qstr(r) for r in before),
            'best': qstr(top),
            'n': len(worse) or sum(tier(r) < tier(top) for r in after),
        })
    return sorted(rows, key=lambda e: (e['artist'].lower(), e['album'].lower()))


# playlists

def read_playlist(path):
    with open(path, encoding='utf-8-sig', errors='replace') as fh:
        return [l.rstrip('\r\n') for l in fh]


def filename_keys(name):
    """Lookup keys for a track filename like '964 - Artist A, Artist B - Title.flac'."""
    name = re.sub(r'^\d+\s*-\s*', '', os.path.splitext(name)[0])
    keys = [norm(name)]
    if ' - ' in name:
        artist, title = name.split(' - ', 1)
        # try each credited artist: compilations list "Various Artists" first
        keys += [norm(a) + norm(title) for a in re.split(r'[,;&]', artist) if norm(a)]
    return keys


def plan_playlists(lib, recs, final_of):
    byp = {r['path']: r for r in recs}
    idx = defaultdict(list)
    for r in recs:
        for k in filename_keys(os.path.basename(r['path'])):
            idx[k].append(r['path'])
        if r.get('title'):
            idx[norm((r.get('artist') or '') + r['title'])].append(r['path'])
            idx[first_artist(r) + norm(r['title'])].append(r['path'])

    def resolve(pl_rel, entry):
        e = entry.strip()
        if e.startswith('file://'):
            e = e[7:]
        rel = None
        if '\\' not in e and not e.startswith('/'):
            rel = os.path.normpath(os.path.join(os.path.dirname(pl_rel), e))
        elif e.startswith('/media/music/'):
            rel = e[len('/media/music/'):]
        elif e.startswith(lib + '/'):
            rel = e[len(lib) + 1:]
        if rel in byp:
            return rel
        for k in filename_keys(re.split(r'[\\/]', e)[-1]):
            if idx.get(k):
                return idx[k][0]
        return None

    pl_dir = os.path.join(lib, PLAYLIST_DIR)
    out = {}  # name -> (lines, sources)
    retire = []
    unresolved = Counter()
    found = []
    for dp, dn, fn in os.walk(lib):
        for f in fn:
            if os.path.splitext(f)[1].lower() in PLAYLISTS:
                found.append(os.path.relpath(os.path.join(dp, f), lib))

    def build(name, entries, source):
        lines = ['#EXTM3U']
        seen = set()
        for e, rel in entries:
            dest = final_of.get(rel) if rel else None
            if not dest:
                lines.append(f'# unresolved: {e}')
                unresolved[name] += 1
                continue
            if dest in seen:
                continue
            seen.add(dest)
            lines.append(os.path.relpath(os.path.join(lib, dest), pl_dir))
        if name in out:
            # same name from another download of the same playlist: keep whichever resolves more
            resolved = lambda ls: sum(not l.startswith('#') for l in ls)
            if resolved(lines) > resolved(out[name][0]):
                out[name] = (lines, out[name][1] + [source])
            else:
                out[name][1].append(source)
        else:
            out[name] = (lines, [source])

    for rel in sorted(found):
        lines = [l for l in read_playlist(os.path.join(lib, rel)) if l.strip() and not l.startswith('#')]
        entries = [(l, resolve(rel, l)) for l in lines]
        here = os.path.dirname(rel)
        stem = os.path.splitext(os.path.basename(rel))[0]
        inside = rel.startswith(PLAYLIST_DIR + '/')
        # album playlists from downloaders: named "playlist", or every entry is inside the folder
        local = not is_dump(rel) and (stem.lower() == 'playlist' or all(
            not l.startswith(('/', '#', 'file:')) and '\\' not in l and '..' not in l.split('/') for l, _ in entries))
        if local and not inside:
            retire.append(rel)  # album playlist, the album itself already shows in Jellyfin
            continue
        name = stem if stem.lower() != 'playlist' else os.path.basename(here)
        build(name, entries, rel)
        if not inside:
            retire.append(rel)

    # numbered playlist download folders become playlists, once
    for dp, dn, fn in os.walk(lib):
        rel = os.path.relpath(dp, lib)
        if os.path.basename(os.path.dirname(rel)).lower() != 'playlist':
            continue
        tracks = [os.path.join(rel, f) for f in fn if os.path.splitext(f)[1].lower() in AUDIO]
        if not tracks:
            continue
        name = f"{rel.split('/')[0]} - {os.path.basename(rel)}"
        if os.path.exists(os.path.join(pl_dir, name + '.m3u8')) or name in out:
            continue
        unresolved.pop(name, None)
        num = lambda p: int(m.group(1)) if (m := re.match(r'(\d+)', os.path.basename(p))) else 10 ** 9
        build(name, [(t, t) for t in sorted(tracks, key=lambda p: (num(p), p))], rel + '/')

    unresolved = Counter({n: sum(l.startswith('# unresolved') for l in ls) for n, (ls, _) in out.items()})
    # identical playlists collapse into one
    seen = {}
    for name in list(out):
        key = tuple(out[name][0])
        if key in seen:
            out[seen[key]][1].extend(out[name][1])
            del out[name]
        else:
            seen[key] = name
    return out, retire, unresolved


# applying

class Mover:
    def __init__(self, lib, quarantine, dry):
        self.lib, self.q, self.dry = lib, quarantine, dry
        self.qmusic = os.path.join(quarantine, 'music')
        self.manifest = None
        if not dry:
            os.makedirs(quarantine, exist_ok=True)
            name = time.strftime('manifest-%Y%m%d-%H%M%S.tsv')
            self.manifest = open(os.path.join(quarantine, name), 'w')

    def log(self, *fields):
        if self.manifest:
            self.manifest.write('\t'.join(fields) + '\n')
            self.manifest.flush()

    def _rename(self, src, dst):
        if os.path.lexists(dst):
            raise FileExistsError(dst)
        if not self.dry:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            os.rename(src, dst)
        self.log('mv', src, dst)

    def qpath(self, rel):
        dst = os.path.join(self.qmusic, rel)
        n = 1
        base, ext = os.path.splitext(dst)
        while os.path.lexists(dst):
            n += 1
            dst = f'{base} ({n}){ext}'
        return dst

    def with_sidecars(self, rel):
        stem = os.path.splitext(os.path.join(self.lib, rel))[0]
        return [stem + e for e in SIDECARS if os.path.isfile(stem + e)]

    def quarantine(self, rel):
        src = os.path.join(self.lib, rel)
        for side in self.with_sidecars(rel):
            self._rename(side, self.qpath(os.path.relpath(side, self.lib)))
        self._rename(src, self.qpath(rel))

    def move(self, rel, dest_rel):
        src, dst = os.path.join(self.lib, rel), os.path.join(self.lib, dest_rel)
        for side in self.with_sidecars(rel):
            side_dst = os.path.splitext(dst)[0] + os.path.splitext(side)[1]
            if not os.path.lexists(side_dst):
                self._rename(side, side_dst)
        self._rename(src, dst)

    def write(self, rel, lines):
        path = os.path.join(self.lib, rel)
        if os.path.exists(path):
            with open(path) as fh:
                if fh.read() == '\n'.join(lines) + '\n':
                    return False
            self._rename(path, self.qpath(rel))
        if not self.dry:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as fh:
                fh.write('\n'.join(lines) + '\n')
        self.log('write', path, '')
        return True

    def sweep(self, dirs):
        """Quarantine directories left without any audio or playlist."""
        keep_ext = AUDIO | PLAYLISTS
        swept = 0
        for d in sorted(dirs, key=lambda p: -p.count('/')):
            full = os.path.join(self.lib, d)
            if not d or d == '.' or d.split('/')[0] == PLAYLIST_DIR or not os.path.isdir(full):
                continue
            if any(os.path.splitext(f)[1].lower() in keep_ext for _, _, fs in os.walk(full) for f in fs):
                continue
            for dp, dn, fn in os.walk(full, topdown=False):
                for f in fn:
                    s = os.path.join(dp, f)
                    self._rename(s, self.qpath(os.path.relpath(s, self.lib)))
                if not self.dry:
                    os.rmdir(dp)
            swept += 1
            p = os.path.dirname(full)
            while not self.dry and p != self.lib and os.path.isdir(p) and not os.listdir(p):
                os.rmdir(p)
                p = os.path.dirname(p)
        return swept


def undo(quarantine):
    runs = sorted(f for f in os.listdir(quarantine) if f.startswith('manifest-') and f.endswith('.tsv'))
    if not runs:
        sys.exit('nothing to undo')
    path = os.path.join(quarantine, runs[-1])
    with open(path) as fh:
        rows = [l.rstrip('\n').split('\t') for l in fh if l.strip()]
    for op, a, b in reversed(rows):
        if op == 'write' and os.path.exists(a):
            os.remove(a)
        elif op == 'mv' and os.path.lexists(b) and not os.path.lexists(a):
            os.makedirs(os.path.dirname(a), exist_ok=True)
            os.rename(b, a)
    os.rename(path, path + '.undone')
    print(f'undid {len(rows)} operations from {runs[-1]}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--library', default='/mass-storage/bigboi/media/music')
    ap.add_argument('--quarantine', default='/mass-storage/bigboi/dupes-quarantine')
    ap.add_argument('--cache', default=os.path.expanduser('~/.cache/music-dedupe/scan.jsonl'))
    ap.add_argument('--apply', action='store_true', help='actually move files (default is a dry run)')
    ap.add_argument('--undo', action='store_true', help='undo the most recent --apply run')
    ap.add_argument('--upgrades', metavar='FILE', help='write the albums-worth-redownloading table here')
    ap.add_argument('-v', '--verbose', action='store_true', help='print every planned operation')
    args = ap.parse_args()
    lib = os.path.realpath(args.library)

    if args.undo:
        return undo(args.quarantine)

    recs = scan(lib, args.cache)
    ops, final_of, report, swaps, kept_both, byp, album_tracks = plan(lib, recs)
    playlists, retire, unresolved = plan_playlists(lib, recs, final_of)

    print(f'{len(recs)} files, {report["songs"]} songs')
    for k, v in report.items():
        if k != 'songs':
            print(f'  {k}: {v}')
    freed = sum(byp[o[1]]['size'] for o in ops if o[0] == 'quarantine')
    print(f'  quarantine: {sum(o[0] == "quarantine" for o in ops)} files, {freed / 1e9:.1f} GB')
    print(f'  move into album slots: {sum(o[0] == "move" for o in ops)}')
    print(f'playlists: {len(playlists)} in {PLAYLIST_DIR}/, {len(retire)} old playlist files to retire')
    for name, (lines, sources) in sorted(playlists.items()):
        n = sum(1 for l in lines if not l.startswith('#'))
        miss = f', {unresolved[name]} unresolved' if unresolved[name] else ''
        print(f'  {name}: {n} tracks{miss}  <- {", ".join(sources)}')
    if args.verbose:
        for o in ops:
            print('  ', *o)
        for f, slot, dest in swaps:
            print(f'   swap {qstr(slot)} -> {qstr(f)}: {f["path"]} -> {dest}')

    if args.upgrades:
        rows = upgrades(album_tracks)
        with open(args.upgrades, 'w') as fh:
            fh.write('| Artist | Album | you have | best you own | tracks below that |\n|---|---|---|---|---|\n')
            for e in rows:
                fh.write(f"| {e['artist']} | {e['album']} | {', '.join(e['have'])} | "
                         f"{e['best']} | {e['n']} |\n")
        print(f'upgrade list: {len(rows)} albums -> {args.upgrades}')

    if not args.apply:
        print('\ndry run, nothing changed. Re-run with --apply.')
        return

    # make sure nothing moved under us since the scan
    for o in ops:
        r = byp[o[1]]
        st = os.stat(os.path.join(lib, o[1]))
        if st.st_size != r['size'] or st.st_mtime != r['mtime']:
            sys.exit(f'{o[1]} changed since the scan, re-run')

    m = Mover(lib, args.quarantine, dry=False)
    touched = set()
    for o in ops:
        if o[0] == 'quarantine':
            m.quarantine(o[1])
        else:
            m.move(o[1], o[2])
        touched.add(os.path.dirname(o[1]))
    for name, (lines, _) in playlists.items():
        m.write(os.path.join(PLAYLIST_DIR, name + '.m3u8'), lines)
    for rel in retire:
        if os.path.exists(os.path.join(lib, rel)):
            m._rename(os.path.join(lib, rel), m.qpath(rel))
            touched.add(os.path.dirname(rel))
    swept = m.sweep(touched)
    print(f'\napplied. {swept} emptied folders quarantined. Manifest: {m.manifest.name}')


if __name__ == '__main__':
    main()
