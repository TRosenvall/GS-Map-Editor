# Issues for alchemy (PascalPixel/alchemy)

Four issues found while building a map editor on top of alchemy, each ready to paste into GitHub: the title line, then the body.

Checked against alchemy `main` at `e123af37b4` (alchemy-gcc `19919a0`), on macOS 14.2 (Intel, x86_64) with Apple clang 15.0.0 (clang-1500.1.0.2.5) and GNU Make 3.81.

**Status at alchemy `0c937e7df0` (2026-11-11):** none needs filing now. Issue 1 is fixed: the Makefile masks the rotate count, and GAS 2.10 is vendored in alchemy-gcc. Issue 2 is fixed: the Makefile stops early on a path with a space. Issue 3 no longer applies, since a map's three grid planes became one `map.txt`. Issue 4 is fixed: INSTALL.md asks only for binutils and libpng. The text below is kept as a record.

---

## Issue 1

**Title:** GAS 2.10 is miscompiled at -O2 by Apple clang: every ARM-mode immediate fails with "Constant expression expected"

**Body:**

### What happens

On macOS (Intel) with Apple clang 15, `make bootstrap` succeeds, but `make tbs-en` then stops in the ARM-mode files (`ARM_C`: `field/vertices.c`, `field/update.c`, `window/glyph_arm.c`):

```
out/tbs-en/obj/games/tbs/src/field/vertices.s:174: Error: Constant expression expected
out/tbs-en/obj/games/tbs/src/field/vertices.s:178: Error: Constant expression expected
make[1]: *** [out/tbs-en/obj/games/tbs/src/field/vertices.o] Error 1
```

Every ARM data-processing instruction with an immediate operand fails. Thumb code, load/store offsets and register operands assemble fine:

| Instruction (ARM mode) | GAS built with `-O2` | GAS built with `-O0` |
|---|---|---|
| `mov r0, #1` | error | ok |
| `mov r0, #0` | error | ok |
| `add r6, r6, #32` | error | ok |
| `cmp r3, #0` | error | ok |
| `ldr r0, [r1, #4]` | ok | ok |
| `ldmia r6, {r0-r3}` | ok | ok |
| `mov r0, r1` | ok | ok |
| Thumb `mov r0, #1` | ok | ok |

### Cause

`binutils-2.10/gas/config/tc-arm.c`, `validate_immediate` (and `validate_immediate_twopart`, which uses the same macro):

```c
#define rotate_left(v, n) (v << n | v >> (32 - n))

  for (i = 0; i < 32; i += 2)
    if ((a = rotate_left (val, i)) <= 0xff)
```

On the first iteration `i == 0`, so the macro computes `val >> 32`. Shifting a 32-bit value by 32 is undefined behaviour in C, and `-fwrapv` doesn't cover it (it only defines signed overflow). At `-O0` the x86 shift instruction happens to give the intended result. At `-O2` clang is entitled to assume the shift never happens, and the check stops accepting any immediate.

### Reproduce (no alchemy checkout needed, about 1 minute)

```sh
curl -LO https://ftp.gnu.org/gnu/binutils/binutils-2.10.tar.gz
tar -xzf binutils-2.10.tar.gz && mkdir gas && cd gas
LEX='touch lex.yy.c' \
CC='cc -fsigned-char -fwrapv -fno-strict-aliasing -fno-delete-null-pointer-checks -ffp-contract=off' \
CFLAGS='-O2 -std=gnu89 -D_POSIX_C_SOURCE=200809L -DNSIG=32 -Wno-implicit-int -Wno-implicit-function-declaration -Wno-int-conversion -Wno-incompatible-pointer-types -fcommon' \
../binutils-2.10/configure --target=arm-elf --build=i686-unknown-linux-gnu --host=i686-unknown-linux-gnu --disable-nls --disable-shared
make MAKEINFO=true all-gas
printf '\t.text\n\t.arm\n\tmov r0, #1\n' > t.s && gas/as-new -marm7tdmi -o t.o t.s
```

Expected: no output. Actual: `t.s:3: Error: Constant expression expected`. These are the `HOST_MODEL` and `GAS_CFLAGS` flags from alchemy's Makefile and `alchemy-gcc/config/host.mk`. With `-O0` in place of `-O2` it assembles.

### Suggested fix

Define the rotate for `n == 0`. This is a host fix that changes nothing GAS outputs:

```c
#define rotate_left(v, n) ((n) ? ((v) << (n) | (v) >> (32 - (n))) : (v))
```

For example, in the `$(CCAS)` recipe right after `tar -xzf`. `sed -i.orig` works with both GNU and BSD sed:

```make
sed -i.orig 's/^#define rotate_left(v, n) (v << n | v >> (32 - n))$$/#define rotate_left(v, n) ((n) ? ((v) << (n) | (v) >> (32 - (n))) : (v))/' \
    $(TOOLCHAIN)/binutils-2.10/gas/config/tc-arm.c
```

Building GAS with `-O0` in `GAS_CFLAGS` also works around it, more bluntly.

### Verified

- With the patched GAS at `-O2`, `vertices.o`, `update.o` and `glyph_arm.o` are byte-identical to those from a `-O0` GAS.
- A full `make tbs-en` of `main` using the patched `-O2` GAS (145 assembler runs) produced `5c4695205413df7db52b9a184815a07783999971`, matching `rom.sha1`.
- I haven't run `make compare-editions` with it, so the other eleven editions aren't confirmed yet.
- I haven't tested Apple Silicon yet. GCC on Linux may not exploit the undefined shift the same way, which would explain why CI doesn't see it.

---

## Issue 2

**Title:** `make bootstrap` fails when the checkout path contains a space

**Body:**

### What happens

With alchemy cloned to a path containing a space (here `~/Documents/GS Map Editor/alchemy`), `make bootstrap` stops at once:

```
Makefile:4: Map: No such file or directory
Makefile:4: Editor/alchemy/alchemy-gcc/config/host.mk: No such file or directory
make[1]: *** No rule to make target `Editor/alchemy/alchemy-gcc/config/host.mk'.  Stop.
make: *** [tools/out/compilers/xgcc] Error 2
```

### Cause

`alchemy-gcc/Makefile` lines 3-4:

```make
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
include $(ROOT)/config/host.mk
```

GNU make splits `include` arguments (and most lists) at spaces, so an absolute path containing a space becomes several words. The top-level Makefile's `$(CURDIR)` uses (`LIBGCC_CC`, `LIBGCC_INCLUDES`) would hit the same problem. GNU make can't realistically support spaces in paths, so a clear early error is probably the practical fix.

### Reproduce

```sh
mkdir -p "/tmp/with space" && cd "/tmp/with space"
git clone https://github.com/PascalPixel/alchemy && cd alchemy
git submodule update --init --recursive alchemy-gcc
make bootstrap
```

### Suggested fix

Stop early with an explanation, near the top of the Makefile:

```make
ifneq ($(words $(CURDIR)),1)
$(error The checkout path "$(CURDIR)" contains a space, which make can't build from. Move or rename it so the path has no spaces)
endif
```

Then add one line to INSTALL.md: "Clone alchemy to a path without spaces."

The same checkout built with no spaces in its path went on to match `rom.sha1`. With compilers that were already built, `make tbs-en` itself did work from a path with spaces; only the bootstrap step failed.

---

## Issue 3

**Title:** Editing a map's grid plane (grid_collision.tsv etc.) doesn't rebuild grid.parts.lz

**Body:**

### What happens

A map's `grid.tsv` is an index of its plane files:

```
GRID_COLLISION	plane
GRID_SHAPE	plane
GRID_METATILE	plane
```

`grid.parts.lz` is built by the generic table rule, `%.parts.lz: %.tsv $(AGSGFX)` (from `TABLE_FORMS` × `CODECS`). The plane files that ags-graphics reads through the index aren't prerequisites. So editing `grid_collision.tsv`, `grid_shape.tsv` or `grid_metatile.tsv` leaves `grid.parts.lz`, and therefore the ROM, stale until `grid.tsv` itself changes.

### Reproduce

```sh
make tbs-en
touch games/tbs/src/map/map_002/grid_collision.tsv
make -n tbs-en | grep map_002/grid     # nothing: no rebuild
touch games/tbs/src/map/map_002/grid.tsv
make -n tbs-en | grep map_002/grid     # tools/out/ags-graphics …/grid.tsv …/grid.parts.lz
```

The same likely applies to any other table built as `.parts` from an index.

### Suggested fix

Have ags-graphics write a dependency file next to its output, listing every file it read (the way `cc -MD` does), and `-include` those depfiles from the Makefile. Alternatively, ags-deps could emit the plane files as prerequisites of each `grid.parts.lz`.

The workaround I use for now is to touch `grid.tsv` after editing a plane.

---

## Issue 4 (minor, documentation)

**Title:** INSTALL.md asks for xz, but no build step uses it

**Body:**

INSTALL.md lists `xz` (Homebrew) and `xz-utils` (apt), but I couldn't find any rule that runs `xz`:
- `grep` finds no use in `Makefile`, `tools/Makefile` or alchemy-gcc's Makefiles;
- binutils 2.10 is fetched as `.tar.gz` and extracted with `tar -xzf`.

As a check, a fresh clone on macOS, with a `PATH` that had no `xz` on it, completed `make bootstrap` and `make tbs-en` and matched `rom.sha1`.

If nothing else needs it, it could come out of the install lines. (Small related note: Homebrew now installs pkg-config as the `pkgconf` formula. `brew install pkg-config` still works as an alias, so INSTALL.md is fine as written.)
