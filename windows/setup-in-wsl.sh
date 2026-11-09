#!/bin/bash
# Installs GS Map Editor inside Ubuntu: the packages alchemy's INSTALL.md
# lists, the editor at one release, and a `gs-map-editor` command that starts
# it. Install-GS-Map-Editor.cmd runs this inside WSL; on any Debian or Ubuntu
# it can be run directly:
#
#   bash setup-in-wsl.sh v0.2.0        (a tag, branch or commit)
#
# Running it again updates the editor to the version given. The game's source
# and your mod are set up later, by the editor's own setup page, in ~/GSMapEditor.
set -euo pipefail

REF="${1:?which version of the editor (for example v0.2.0)}"
REPO="https://github.com/TRosenvall/GS-Map-Editor"
APP="$HOME/.local/share/gs-map-editor"
BIN="$HOME/.local/bin/gs-map-editor"

echo "== The tools for building the game (asks for your Ubuntu password)"
sudo apt-get update -q
sudo apt-get install -y -q build-essential binutils-arm-none-eabi git libpng-dev python3 python3-pil

echo "== GS Map Editor $REF"
mkdir -p "$APP"
if [ ! -d "$APP/.git" ]; then
  git -C "$APP" init -q
  git -C "$APP" remote add origin "$REPO"
fi
git -C "$APP" fetch -q --depth 1 origin "$REF"
git -C "$APP" checkout -q --force FETCH_HEAD

mkdir -p "$(dirname "$BIN")"
cat > "$BIN" <<EOF
#!/bin/sh
exec python3 "$APP/desktop.py" "\$@"
EOF
chmod +x "$BIN"

echo "== Done. Start it with: $BIN"
