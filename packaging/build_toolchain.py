"""Build the tools alchemy's build needs beyond Apple's developer tools, into
one folder the app carries, so players never need Homebrew:

  bin/arm-none-eabi-{as,ld,objcopy,readelf,...}   GNU binutils for the GBA
  bin/libpng-config                               a shim answering as tools/Makefile asks
  lib/libpng16.a + headers                        static, so tools link no dylibs

    python3 packaging/build_toolchain.py [--out packaging/toolchain] [--jobs 8]

Sources are downloaded once into packaging/.cache and checked against the
SHA-256 sums below (pinned when first fetched). Builds for this Mac's
architecture: run it, and the app build, on an Apple Silicon Mac for a native
arm64 app, and on an Intel Mac for an x86_64 one.
"""

import argparse
import contextlib
import hashlib
import os
import platform
import shutil
import subprocess
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = {
    "binutils": ("https://ftp.gnu.org/gnu/binutils/binutils-2.43.1.tar.xz",
                 "13f74202a3c4c51118b797a39ea4200d3f6cfbe224da6d1d95bb938480132dfd"),
    "libpng": ("https://download.sourceforge.net/libpng/libpng-1.6.44.tar.xz",
               "60c4da1d5b7f0aa8d158da48e8f8afa9773c1c8baa5d21974df61f1886b8ce8e"),
}
MIN_MACOS = "11.0"

LIBPNG_CONFIG_SHIM = r"""#!/bin/sh
# libpng-config for the static libpng in ../lib. alchemy's tools/Makefile asks
# for --cflags and --ldflags; libpng's own script names the machine it was
# built on, so the app carries this one instead.
here=$(cd "$(dirname "$0")/.." && pwd)
out=
for a in "$@"; do
  case "$a" in
    --cflags|--I_opts) out="$out -I$here/include/libpng16" ;;
    --ldflags|--libs|--static) out="$out $here/lib/libpng16.a -lz" ;;
    --version) out="$out 1.6.44" ;;
    --prefix) out="$out $here" ;;
    *) ;;
  esac
done
echo $out
"""


def fetch(name, cache):
    url, sha = SOURCES[name]
    path = os.path.join(cache, os.path.basename(url))
    if not os.path.exists(path):
        os.makedirs(cache, exist_ok=True)
        print("download", url, flush=True)
        # curl, not urllib: it uses the system's certificates, follows
        # SourceForge's mirror redirects, and retries a dropped connection.
        subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error", "--retry", "3",
                        "-o", path + ".part", url], check=True)
        os.replace(path + ".part", path)
    got = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if got != sha:
        raise SystemExit(f"{path}: SHA-256 {got}, expected {sha}")
    return path


def unpack(archive, work):
    with tarfile.open(archive) as t:
        top = t.getnames()[0].split("/")[0]
        dest = os.path.join(work, top)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        t.extractall(work, filter="data") if hasattr(tarfile, "data_filter") else t.extractall(work)
    return dest


def run(cmd, cwd, env):
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "toolchain"))
    ap.add_argument("--cache", default=os.path.join(HERE, ".cache"))
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    work = os.path.join(args.cache, "build")
    os.makedirs(work, exist_ok=True)
    env = dict(os.environ, MACOSX_DEPLOYMENT_TARGET=MIN_MACOS,
               PATH="/usr/bin:/bin:/usr/sbin:/sbin", CC="clang", CFLAGS="-O2")
    j = f"-j{args.jobs}"

    src = unpack(fetch("binutils", args.cache), work)
    run(["./configure", f"--prefix={out}", "--target=arm-none-eabi", "--disable-nls", "--disable-werror",
         "--disable-gdb", "--disable-gdbserver", "--disable-sim", "--disable-gprofng", "--disable-libctf",
         "--without-zstd", "--disable-plugins", "--enable-deterministic-archives",
         # macOS's own zlib: the copy inside binutils doesn't compile against
         # the macOS 15 SDK (Xcode 16), where stdio.h already defines fdopen.
         "--with-system-zlib"], src, env)
    run(["make", j], src, env)
    run(["make", "install-strip"], src, env)

    src = unpack(fetch("libpng", args.cache), work)
    run(["./configure", f"--prefix={out}", "--disable-shared", "--enable-static"], src, env)
    run(["make", j], src, env)
    run(["make", "install"], src, env)

    # Only what the build uses; documentation and dylibs stay out of the app.
    # The licences stay: binutils is GPL, so its terms and a source pointer ship with it.
    licences = os.path.join(out, "licenses")
    os.makedirs(licences, exist_ok=True)
    for name, files in (("binutils", ["COPYING3", "COPYING3.LIB"]), ("libpng", ["LICENSE"])):
        folder = next(os.path.join(work, d) for d in os.listdir(work) if d.startswith(name))
        for f in files:
            shutil.copy(os.path.join(folder, f), os.path.join(licences, f"{name}-{f}"))
    # libpng's own scripts name the machine they were built on: the shim
    # above takes their place.
    for f in ("libpng-config", "libpng16-config"):
        with contextlib.suppress(FileNotFoundError):
            os.remove(os.path.join(out, "bin", f))
    shim = os.path.join(out, "bin", "libpng-config")
    with open(shim, "w") as f:
        f.write(LIBPNG_CONFIG_SHIM)
    os.chmod(shim, 0o755)
    for d in ("share", "lib/pkgconfig", "arm-none-eabi/lib"):
        shutil.rmtree(os.path.join(out, d), ignore_errors=True)
    for f in os.listdir(os.path.join(out, "lib")):
        if not f.endswith(".a") or f in ("libpng.a",):
            p = os.path.join(out, "lib", f)
            os.remove(p) if os.path.isfile(p) or os.path.islink(p) else shutil.rmtree(p)
    with open(os.path.join(out, "TOOLCHAIN.txt"), "w") as f:
        f.write(f"arch {platform.machine()}, macOS >= {MIN_MACOS}\n")
        for name, (url, sha) in SOURCES.items():
            f.write(f"{name} {url} sha256 {sha}\n")
    print("toolchain in", out)


if __name__ == "__main__":
    main()
