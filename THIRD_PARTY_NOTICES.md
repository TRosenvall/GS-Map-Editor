# Third-party software

GS Map Editor's app bundles the software below. Each keeps its own licence;
this file lists them so nothing is left unsaid. **The editor's own licence is
not yet chosen, and neither game art nor a ROM is included in it.**

| Software | Used for | Licence | Source |
|---|---|---|---|
| GNU Binutils 2.43.1 | assembling and linking the game | GPL v3 or later | https://ftp.gnu.org/gnu/binutils/binutils-2.43.1.tar.xz |
| libpng 1.6.44 | build tool for the game's pictures | libpng licence | https://download.sourceforge.net/libpng/libpng-1.6.44.tar.xz |
| utf8proc 2.9.0 | build tool for the game's text | MIT-style | https://github.com/JuliaStrings/utf8proc |
| CPython | runs the editor | PSF licence | https://www.python.org/ |
| Pillow | reading and drawing pictures | MIT-CMU (HPND) | https://python-pillow.org/ |
| pywebview | the app window | BSD 3-Clause | https://pywebview.flowrl.com/ |
| PyInstaller bootloader | packaging | GPL v2 with a bootloader exception | https://pyinstaller.org/ |

The toolchain's licence texts ship inside the app under
`Contents/Frameworks/toolchain/licenses/`. Binutils is GPL software: the source
for the exact version bundled is at the link above (its checksum is in
`packaging/build_toolchain.py`), and a copy is available on request.

The app downloads [alchemy](https://github.com/PascalPixel/alchemy), the
decompilation of Golden Sun it edits, onto the user's own Mac at first run. It
isn't part of this software. **At the pinned commit alchemy has no licence file
at its root: ask its author for terms before relying on this.**

Golden Sun is a trademark of its owners. This project isn't affiliated with them.
