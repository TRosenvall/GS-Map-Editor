"""Read and write alchemy's table TSVs (a map's cell pictures and shapes).

Before 2026-11-25 the header named each column and its type, e.g.

    top_left:u16	top_right:u16	bottom_left:u16	bottom_right:u16
    0xf200	0xf200	0xf200	0xf200

Since then headers are plain names and values decimal (shapes.tsv), and a
map's cell pictures are cell_tiles.tsv: three columns a corner, its tile, its
flip (h, v, hv or nothing) and its palette, read here into the same 16-bit
entries as before (tile 10 bits, hflip 0x400, vflip 0x800, palette 12-15) so
the rest of the editor sees one table either way.

Each value's original spelling is kept so an unchanged table saves
byte-identical; edited values are written in the column's usual style.
"""


from .fsio import atomic_write


class Table:
    def __init__(self, columns, rows, spellings):
        self.columns = columns  # [(name, type)]
        self.rows = rows  # [[int]]
        self._spellings = spellings  # [[str]] original text per cell

    def set(self, row, col, value):
        self.rows[row][col] = value
        # Write the new value in the cell's own style (hex or decimal).
        old = self._spellings[row][col]
        hexed = old.startswith("0x") if old is not None else self._hex_style(col)
        self._spellings[row][col] = f"{value:#x}" if hexed else str(value)

    def append(self, values):
        self.rows.append(list(values))
        self._spellings.append([None] * len(values))

    def insert(self, index, values):
        """Insert a row, written in decimal."""
        self.rows.insert(index, list(values))
        self._spellings.insert(index, [str(v) for v in values])

    def delete(self, index):
        del self.rows[index]
        del self._spellings[index]

    def _hex_style(self, col):
        for r in self._spellings:
            if r[col] is not None:
                return r[col].startswith("0x")
        return self.columns[col][1] == "u16"  # a plain column ("") is decimal

    def to_text(self):
        out = ["\t".join(f"{n}:{t}" if t else n for n, t in self.columns)]
        for vals, spell in zip(self.rows, self._spellings):
            cells = []
            for c, (v, s) in enumerate(zip(vals, spell)):
                if s is not None:
                    cells.append(s)
                elif self._hex_style(c):
                    cells.append(f"{v:#x}")
                else:
                    cells.append(str(v))
            out.append("\t".join(cells))
        return "\n".join(out) + "\n"


CORNERS = ("top_left", "top_right", "bottom_left", "bottom_right")
CELL_TILES_HEADER = "\t".join(f"{c}{part}" for c in CORNERS for part in ("", "_flip", "_palette"))
FLIPS = {"": 0, "h": 0x400, "v": 0x800, "hv": 0xC00}


class CellTiles(Table):
    """cell_tiles.tsv: rows of four 16-bit entries, written three columns a corner."""

    def __init__(self, rows, lines):
        super().__init__([(c, "u16") for c in CORNERS], rows, None)  # the lines keep the spellings
        self._lines = lines  # each row's text as read; None once it changes

    def set(self, row, col, value):
        self.rows[row][col] = value
        self._lines[row] = None

    def append(self, values):
        self.rows.append(list(values))
        self._lines.append(None)

    def insert(self, index, values):
        self.rows.insert(index, list(values))
        self._lines.insert(index, None)

    def delete(self, index):
        del self.rows[index]
        del self._lines[index]

    @staticmethod
    def _entry_text(e):
        flip = {0: "", 0x400: "h", 0x800: "v", 0xC00: "hv"}[e & 0xC00]
        return f"{e & 0x3FF}\t{flip}\t{e >> 12}"

    def to_text(self):
        out = [CELL_TILES_HEADER]
        for vals, line in zip(self.rows, self._lines):
            out.append(line if line is not None else "\t".join(self._entry_text(e) for e in vals))
        return "\n".join(out) + "\n"


def _parse_cell_tiles(lines):
    rows = []
    entries = {}  # entry -> itself: the same few entries recur, kept as one object each
    for line in lines[1:]:
        c = line.split("\t")
        row = [int(c[k]) | FLIPS[c[k + 1]] | (int(c[k + 2]) << 12) for k in (0, 3, 6, 9)]
        rows.append([entries.setdefault(e, e) for e in row])
    return CellTiles(rows, lines[1:])


def parse(text):
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if lines[0] == CELL_TILES_HEADER:
        return _parse_cell_tiles(lines)
    # name:type, or a plain name (decimal u8) since 2026-11-25
    columns = [tuple(h.split(":", 1)) if ":" in h else (h, "") for h in lines[0].split("\t")]
    rows, spellings = [], []
    values = {}  # spelling -> value: tables repeat a few spellings many times
    for line in lines[1:]:
        cells = line.split("\t")
        row = []
        for c in cells:
            v = values.get(c)
            if v is None:
                v = values[c] = int(c, 0)
            row.append(v)
        rows.append(row)
        spellings.append(cells)
    return Table(columns, rows, spellings)


def load(path):
    with open(path, encoding="utf-8") as f:
        return parse(f.read())


def save(table, path):
    atomic_write(path, table.to_text())
