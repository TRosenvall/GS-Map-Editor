"""Share a mod as a patch, never as a ROM.

alchemy's stock build is byte-identical to the retail cartridge (rom.sha1),
so a patch from the stock build to the mod build applies to anyone's own
dump. The stock build is made from the commit the mod is based on, in a
separate folder (`git archive`, so the player's checkout is never touched),
checked against rom.sha1, and kept for later exports.

Patches are BPS (byuu's format, what Rom Patcher JS, Floating IPS and most
emulators' soft-patching read): source and target sizes, then actions that
copy from the source in place (SourceRead), from anywhere in the source
(SourceCopy, for data that moved), or carry new bytes (TargetRead), then
CRC32s of source, target and patch.
"""

import hashlib
import os
import shutil
import subprocess
import zlib

from .i18n import N_, tr, translate

SOURCE_READ, TARGET_READ, SOURCE_COPY, TARGET_COPY = range(4)
BLOCK = 16       # source index granularity
MIN_COPY = 32    # shortest SourceCopy worth its header
MIN_RUN = 4      # shortest SourceRead worth breaking a literal for


def _vlq(n):
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(0x80 | x)
            return bytes(out)
        out.append(x)
        n -= 1


def _read_vlq(data, i):
    n, shift = 0, 1
    while True:
        if shift > 1 << 56:
            raise ValueError(tr("This patch file is damaged or isn't a real patch."))
        x = data[i]
        i += 1
        n += (x & 0x7F) * shift
        if x & 0x80:
            return n, i
        shift <<= 7
        n += shift


def _match(a, ai, b, bi, limit):
    """Length of the common run a[ai:] / b[bi:], at most `limit`, by halving
    slice comparisons (fast in CPython) down to single bytes."""
    n, step = 0, 4096
    while n < limit:
        k = min(step, limit - n)
        if a[ai + n:ai + n + k] == b[bi + n:bi + n + k]:
            n += k
            step = min(step * 2, 1 << 20)
        elif k == 1:
            return n
        else:
            step = k // 2
    return n


def bps_encode(source, target, metadata=b""):
    index = {}
    for p in range(0, len(source) - BLOCK + 1, BLOCK):
        index.setdefault(source[p:p + BLOCK], p)
    out = bytearray(b"BPS1")
    out += _vlq(len(source)) + _vlq(len(target)) + _vlq(len(metadata)) + metadata
    literal_from, src_rel, i, n = None, 0, 0, len(target)

    def flush(end):
        nonlocal literal_from
        if literal_from is not None and end > literal_from:
            out.extend(_vlq(((end - literal_from - 1) << 2) | TARGET_READ))
            out.extend(target[literal_from:end])
        literal_from = None

    while i < n:
        run = _match(source, i, target, i, min(len(source), n) - i) if i < len(source) else 0
        if run >= MIN_RUN:
            flush(i)
            out.extend(_vlq(((run - 1) << 2) | SOURCE_READ))
            i += run
            continue
        p = index.get(target[i:i + BLOCK]) if i + BLOCK <= n else None
        if p is not None:
            length = _match(source, p, target, i, min(len(source) - p, n - i))
            if length >= MIN_COPY:
                flush(i)
                out.extend(_vlq(((length - 1) << 2) | SOURCE_COPY))
                d = p - src_rel
                out.extend(_vlq((abs(d) << 1) | (d < 0)))
                src_rel = p + length
                i += length
                continue
        if literal_from is None:
            literal_from = i
        i += 1
    flush(n)
    out += zlib.crc32(source).to_bytes(4, "little") + zlib.crc32(target).to_bytes(4, "little")
    out += zlib.crc32(bytes(out)).to_bytes(4, "little")
    return bytes(out)


# Larger than any GBA game, so a patch asking for more is a bad patch and not a
# reason to fill the Mac's memory.
MAX_GAME = 64 * 1024 * 1024


def _too_big():
    return tr("This patch asks for a game far bigger than a GBA game can be, so it wasn't applied.")


def _broken():
    return tr("This patch file is damaged or isn't a real patch.")


class WrongGame(ValueError):
    """A patch whose checksum says it was made for another game file."""


def bps_apply(source, patch):
    if patch[:4] != b"BPS1" or len(patch) < 19:
        raise ValueError(tr("not a BPS patch"))
    if zlib.crc32(patch[:-4]) != int.from_bytes(patch[-4:], "little"):
        raise ValueError(tr("the patch file is damaged"))
    if zlib.crc32(source) != int.from_bytes(patch[-12:-8], "little"):
        raise WrongGame(tr("this patch is for a different ROM"))
    i = 4
    try:
        src_size, i = _read_vlq(patch, i)
        tgt_size, i = _read_vlq(patch, i)
        meta, i = _read_vlq(patch, i)
    except IndexError:
        raise ValueError(_broken()) from None
    if tgt_size > MAX_GAME:
        raise ValueError(_too_big())
    i += meta
    out = bytearray()
    src_rel = tgt_rel = 0
    end = len(patch) - 12
    try:
        while i < end:
            data, i = _read_vlq(patch, i)
            mode, length = data & 3, (data >> 2) + 1
            if len(out) + length > tgt_size:
                raise ValueError(_broken())
            if mode == SOURCE_READ:
                if len(out) + length > len(source):
                    raise ValueError(_broken())
                out += source[len(out):len(out) + length]
            elif mode == TARGET_READ:
                if i + length > end:
                    raise ValueError(_broken())
                out += patch[i:i + length]
                i += length
            else:
                d, i = _read_vlq(patch, i)
                d = -(d >> 1) if d & 1 else d >> 1
                if mode == SOURCE_COPY:
                    src_rel += d
                    if src_rel < 0 or src_rel + length > len(source):
                        raise ValueError(_broken())
                    out += source[src_rel:src_rel + length]
                    src_rel += length
                else:
                    tgt_rel += d
                    if tgt_rel < 0 or tgt_rel >= len(out):
                        raise ValueError(_broken())
                    for _ in range(length):
                        out.append(out[tgt_rel])
                        tgt_rel += 1
    except IndexError:
        raise ValueError(_broken()) from None
    if len(out) != tgt_size or zlib.crc32(out) != int.from_bytes(patch[-8:-4], "little"):
        raise ValueError(tr("the patch didn't produce the expected game"))
    return bytes(out)


def patch_metadata(patch):
    i = 4
    _, i = _read_vlq(patch, i)
    _, i = _read_vlq(patch, i)
    meta, i = _read_vlq(patch, i)
    return patch[i:i + meta]


# ---- stock builds ---------------------------------------------------------------------

def git(root, *args):
    p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


def base_commit(root, settings=None):
    """The alchemy commit the mod starts from: chosen at setup, else where the
    checkout's branch left the commit this editor is pinned to (the pin itself,
    or HEAD on a checkout still older than the pin), else where it left
    origin/main or main, else HEAD. The pin comes first: a local main can be
    far behind (a clone's main is never moved by updating), and its old files
    would no longer build."""
    if settings and settings.get("base_commit"):
        return settings["base_commit"]
    from .setup import ALCHEMY_PIN
    for ref in (ALCHEMY_PIN, "origin/main", "main"):
        if git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"):
            base = git(root, "merge-base", "HEAD", ref)
            if base:
                return base
    return git(root, "rev-parse", "HEAD")


def expected_sha1(root, commit, edition="tbs-en"):
    text = git(root, "show", f"{commit}:rom.sha1") or ""
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].endswith(f"/{edition}.gba"):
            return parts[0]
    return None


def stock_rom(root, cache_dir, env, log, edition="tbs-en", settings=None):
    """Path of the stock build of the mod's base commit, building it if needed."""
    commit = base_commit(root, settings)
    if not commit:
        raise ValueError(tr("The editor's copy of the game is damaged, so the original can't be rebuilt. Run setup again."))
    want = expected_sha1(root, commit, edition)
    path = os.path.join(cache_dir, f"{commit[:12]}-{edition}.gba")
    if os.path.exists(path) and (not want or hashlib.sha1(open(path, "rb").read()).hexdigest() == want):
        log(tr("Unmodified game: already built for {commit}.", commit=commit[:10]))
        return path, want
    src = os.path.join(cache_dir, f"src-{commit[:12]}")
    shutil.rmtree(src, ignore_errors=True)
    os.makedirs(src)
    log(tr("Building the unmodified game from {commit}, once (a few minutes)…", commit=commit[:10]))
    archive = subprocess.Popen(["git", "-C", root, "archive", commit], stdout=subprocess.PIPE)
    subprocess.run(["tar", "-x", "-C", src], stdin=archive.stdout, check=True)
    if archive.wait() != 0:
        raise ValueError(tr("couldn't export {commit} from the game source", commit=commit[:10]))
    # Reuse the compilers and tools the checkout already built.
    for rel in ("tools/out", "alchemy-gcc"):
        dest = os.path.join(src, rel)
        if os.path.isdir(dest) and not os.listdir(dest):
            os.rmdir(dest)
        if not os.path.exists(dest):
            os.symlink(os.path.join(root, rel), dest)
    p = subprocess.Popen(["make", "-j4", edition], cwd=src, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        log(line.rstrip("\n"))
    if p.wait() != 0:
        raise ValueError(tr("the unmodified game didn't build; see the log"))
    built = os.path.join(src, "out", edition, f"{edition}.gba")
    got = hashlib.sha1(open(built, "rb").read()).hexdigest()
    if want and got != want:
        raise ValueError(tr("the unmodified build doesn't match the retail game (SHA-1 {got}, expected {want})",
                            got=got, want=want))
    shutil.copy(built, path)
    shutil.rmtree(src, ignore_errors=True)
    log(tr("Unmodified game built and checked against the retail SHA-1 {sha1}.", sha1=want))
    return path, want


# ---- export: build, diff, write ----------------------------------------------------------

# Names Windows keeps for devices: a file called con.bps can't be made there.
WINDOWS_RESERVED = {"con", "prn", "aux", "nul"} | {f"{p}{n}" for p in ("com", "lpt") for n in range(1, 10)}
MAX_SLUG = 80  # well inside every system's limit on a file name, with "-2.bps" after it


def slug(name):
    s = "".join(c if c.isalnum() else "-" for c in name.strip().lower()).strip("-")
    while "--" in s:
        s = s.replace("--", "-")
    s = s[:MAX_SLUG].strip("-")
    if s in WINDOWS_RESERVED:
        s += "-mod"
    return s or "my-mod"


def file_base(out_dir, name, keep=False):
    """Where a mod called `name` is saved, without an extension: <slug>, or with
    `keep` and a patch already there, the first free <slug>-2, <slug>-3…"""
    base = os.path.join(out_dir, slug(name))
    if not keep:
        return base
    n, free = 2, base
    while any(os.path.exists(free + ext) for ext in (".bps", ".ips", ".txt")):
        free, n = f"{base}-{n}", n + 1
    return free


def export(root, out_dir, cache_dir, env, log, name, author="", description="", edition="tbs-en", settings=None,
           ips=False, keep=False):
    """Build the mod, make the patch, check it, write <slug>.bps and a readme
    (with `keep`, beside an earlier export of the same name, not over it)."""
    log(tr("Building your mod…"))
    p = subprocess.Popen(["make", "-j4", edition], cwd=root, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        log(line.rstrip("\n"))
    if p.wait() != 0:
        raise ValueError(tr("your mod didn't build; see the log"))
    mod = open(os.path.join(root, "out", edition, f"{edition}.gba"), "rb").read()
    stock_path, want = stock_rom(root, cache_dir, env, log, edition, settings)
    stock = open(stock_path, "rb").read()
    if mod == stock:
        raise ValueError(tr("your build is identical to the unmodified game: nothing to export yet"))
    log(tr("Making the patch…"))
    meta = f"name: {name}\nauthor: {author}\ndescription: {description}\nfor: Golden Sun ({edition}), SHA-1 {want}\n"
    patch = bps_encode(stock, mod, meta.encode("utf-8"))
    if bps_apply(stock, patch) != mod:
        raise ValueError(tr("the patch didn't reproduce your build (a bug in the editor; please report it)"))
    os.makedirs(out_dir, exist_ok=True)
    base = file_base(out_dir, name, keep)
    with open(base + ".bps", "wb") as f:
        f.write(patch)
    with open(base + ".txt", "w", encoding="utf-8") as f:
        f.write(f"{name}\n{'=' * len(name)}\n\n")
        if author:
            f.write(f"By {author}\n\n")
        if description:
            f.write(description.strip() + "\n\n")
        f.write("How to play\n-----------\n"
                "1. Start from your own copy of Golden Sun (the English edition).\n"
                f"   It must be the unmodified game: SHA-1 {want}.\n"
                f"2. Apply {os.path.basename(base)}.bps with a BPS patcher, for example\n"
                "   Rom Patcher JS (https://www.marcrobledo.com/RomPatcher.js/), Floating IPS or GS Map Editor.\n"
                + (f"   ({os.path.basename(base)}.ips is the same mod for older patchers that only take IPS.)\n" if ips else "") +
                "3. Play the patched file in a GBA emulator such as mGBA.\n\n"
                "This patch holds only the mod's changes, not the game.\n"
                "Made with GS Map Editor on alchemy, the Golden Sun decompilation.\n")
    log(tr("Wrote {file} ({size} bytes).", file=base + ".bps", size=f"{len(patch):,}"))
    ips_size = None
    if ips:
        ipatch = ips_encode(stock, mod)
        if ips_apply(stock, ipatch) != mod:
            raise ValueError(tr("the IPS patch didn't reproduce your build (a bug in the editor; please report it)"))
        with open(base + ".ips", "wb") as f:
            f.write(ipatch)
        ips_size = len(ipatch)
        log(tr("Wrote {file} ({size} bytes; IPS can't record moved data, so it's larger).",
               file=base + ".ips", size=f"{ips_size:,}"))
    elif os.path.exists(base + ".ips"):
        # An IPS left by an earlier export under this name is an older mod now:
        # sharing the folder would hand players two different versions.
        os.remove(base + ".ips")
    return {"patch": base + ".bps", "readme": base + ".txt", "size": len(patch), "ips_size": ips_size,
            "for_sha1": want, "mod_sha1": hashlib.sha1(mod).hexdigest()}


def play_patch(root, cache_dir, out_dir, env, log, patch, name="mod", settings=None):
    """Apply someone's patch to this Mac's unmodified build; returns the
    patched game's path. The unmodified build equals the retail game, so
    a patch made for a cartridge dump applies to it too."""
    stock_path, _ = stock_rom(root, cache_dir, env, log, settings=settings)
    game = bps_apply(open(stock_path, "rb").read(), patch)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, slug(name) + ".gba")
    with open(path, "wb") as f:
        f.write(game)
    meta = patch_metadata(patch).decode("utf-8", "replace")
    log(tr("Patched game ready: {path}", path=path))
    return {"game": path, "about": meta}


# ---- IPS and UPS ----------------------------------------------------------------------------
# IPS (1990s): records of (3-byte offset, 2-byte size, bytes), size 0 = a run
# of one byte; "EOF", then optionally a 3-byte size to truncate to. No
# checksums, offsets below 16 MB, no way to say "this moved".
# UPS (2008): XOR blocks between "UPS1", sizes and CRC32s of source, target, patch.

IPS_EOF = 0x454F46  # "EOF": a record may not start here


def ips_encode(source, target):
    if len(target) > 1 << 24:
        raise ValueError(tr("IPS can't describe a game over 16 MB"))
    out = bytearray(b"PATCH")
    i, n = 0, len(target)
    while i < n:
        if i < len(source) and source[i] == target[i]:
            i += 1
            continue
        start = i
        # extend over changed bytes, absorbing equal gaps shorter than a record header
        j = i
        while j < n and j - start < 0xFFFF:
            if j >= len(source) or source[j] != target[j]:
                j += 1
                continue
            gap = j
            while gap < n and gap < len(source) and source[gap] == target[gap] and gap - j < 6:
                gap += 1
            if gap - j >= 6 or gap >= n:
                break
            j = gap
        end = min(j, start + 0xFFFF)
        if start == IPS_EOF:  # back up one byte: re-write it unchanged
            start -= 1
        out += start.to_bytes(3, "big") + (end - start).to_bytes(2, "big") + target[start:end]
        i = end
    out += b"EOF"
    if len(target) < len(source):
        out += len(target).to_bytes(3, "big")
    return bytes(out)


def ips_apply(source, patch):
    if patch[:5] != b"PATCH":
        raise ValueError(tr("not an IPS patch"))
    out = bytearray(source)
    i = 5
    while True:
        if i + 3 > len(patch):
            raise ValueError(tr("the IPS patch is cut short"))
        if patch[i:i + 3] == b"EOF":
            i += 3
            if i + 3 <= len(patch):
                del out[int.from_bytes(patch[i:i + 3], "big"):]
            return bytes(out)
        off = int.from_bytes(patch[i:i + 3], "big")
        size = int.from_bytes(patch[i + 3:i + 5], "big")
        i += 5
        if i + (size or 3) > len(patch):
            raise ValueError(tr("the IPS patch is cut short"))
        if size:
            data = patch[i:i + size]
            i += size
        else:
            count = int.from_bytes(patch[i:i + 2], "big")
            data = patch[i + 2:i + 3] * count
            i += 3
        if off + len(data) > len(out):
            out.extend(b"\0" * (off + len(data) - len(out)))
        out[off:off + len(data)] = data


def ups_apply(source, patch):
    if patch[:4] != b"UPS1":
        raise ValueError(tr("not a UPS patch"))
    if zlib.crc32(patch[:-4]) != int.from_bytes(patch[-4:], "little"):
        raise ValueError(tr("the patch file is damaged"))
    i = 4
    try:
        src_size, i = _read_vlq(patch, i)
        tgt_size, i = _read_vlq(patch, i)
    except IndexError:
        raise ValueError(_broken()) from None
    if tgt_size > MAX_GAME:
        raise ValueError(_too_big())
    if len(source) != src_size or zlib.crc32(source) != int.from_bytes(patch[-12:-8], "little"):
        raise WrongGame(tr("this patch is for a different ROM"))
    out = bytearray(source[:tgt_size]) + bytearray(max(0, tgt_size - len(source)))
    pos, end = 0, len(patch) - 12
    try:
        while i < end:
            skip, i = _read_vlq(patch, i)
            pos += skip
            while True:
                x = patch[i]
                i += 1
                if x == 0:
                    pos += 1
                    break
                if pos < tgt_size:
                    out[pos] ^= x
                pos += 1
    except IndexError:
        raise ValueError(_broken()) from None
    if zlib.crc32(out) != int.from_bytes(patch[-8:-4], "little"):
        raise ValueError(tr("the patch didn't produce the expected game"))
    return bytes(out)


def patch_format(patch):
    return {b"BPS1": "bps", b"UPS1": "ups"}.get(patch[:4]) or ("ips" if patch[:5] == b"PATCH" else None)


def apply_any(source, patch):
    """(patched game, format, notes) for a BPS, UPS or IPS patch."""
    fmt = patch_format(patch)
    if fmt == "bps":
        return bps_apply(source, patch), fmt, patch_metadata(patch).decode("utf-8", "replace")
    if fmt == "ups":
        return ups_apply(source, patch), fmt, ""
    if fmt == "ips":
        return ips_apply(source, patch), fmt, ""
    raise ValueError(tr("this isn't a .bps, .ips or .ups patch"))


EDITIONS = {"tbs": "Golden Sun", "tla": "Golden Sun: The Lost Age"}
# The game titles stay as the games have them; the languages are the editor's words.
LANGS = {"en": N_("English"), "ja": N_("Japanese"), "de": N_("German"), "es": N_("Spanish"), "fr": N_("French"),
         "it": N_("Italian")}


def identify(root, rom):
    """What a ROM is, by alchemy's rom.sha1: 'Golden Sun (English)', or None."""
    sha = hashlib.sha1(rom).hexdigest()
    try:
        text = open(os.path.join(root, "rom.sha1"), encoding="utf-8").read()
    except OSError:
        return None
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == sha:
            game, lang = os.path.basename(parts[1])[:-4].split("-")
            return f"{EDITIONS.get(game, game)} ({translate(LANGS[lang]) if lang in LANGS else lang})"
    return None


def patch_game(root, cache_dir, out_dir, env, log, patch, name, rom=None, settings=None):
    """Apply a patch to `rom` (the player's own file) or, without one, to this
    Mac's unmodified build. Returns the patched game's path and what we know."""
    notes = []
    rom_given = rom is not None
    if rom is None:
        stock_path, _ = stock_rom(root, cache_dir, env, log, settings=settings)
        rom = open(stock_path, "rb").read()
        base = tr("the unmodified game built on this Mac")
    else:
        what = identify(root, rom)
        base = tr("your ROM ({what})", what=what) if what else tr("your ROM")
        if not what:
            notes.append(tr("Your ROM isn't an unmodified game alchemy knows: it may already be patched, "
                            "or be a different version."))
    fmt = patch_format(patch)
    log(tr("Applying a {format} patch to {base}…", format=(fmt or "?").upper(), base=base))
    try:
        game, fmt, about = apply_any(rom, patch)
    except WrongGame:
        raise ValueError(
            tr("This patch was made for a different game file. "
               "Your ROM is a different version, or already patched: start from the unmodified game.")
            if rom_given else
            tr("This patch was made for a different game file. "
               "It wasn't made for the English Golden Sun this editor builds.")) from None
    if fmt == "ips":
        notes.append(tr("IPS patches can't check they're for the right game; if it doesn't start, "
                        "the patch was probably made for a different version."))
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, slug(name) + ".gba")
    with open(path, "wb") as f:
        f.write(game)
    log(tr("Saved {path}", path=path))
    return {"game": path, "format": fmt, "about": about, "base": base, "notes": notes,
            "result_is": identify(root, game)}
