"""Read and write alchemy's typed table TSVs (cell_pictures.tsv, shapes.tsv).

Header names each column and its type, e.g.

    top_left:u16	top_right:u16	bottom_left:u16	bottom_right:u16
    0xf200	0xf200	0xf200	0xf200

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
        return self.columns[col][1] == "u16"

    def to_text(self):
        out = ["\t".join(f"{n}:{t}" for n, t in self.columns)]
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


def parse(text):
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    columns = [tuple(h.split(":", 1)) for h in lines[0].split("\t")]
    rows, spellings = [], []
    for line in lines[1:]:
        cells = line.split("\t")
        rows.append([int(c, 0) for c in cells])
        spellings.append(cells)
    return Table(columns, rows, spellings)


def load(path):
    with open(path, encoding="utf-8") as f:
        return parse(f.read())


def save(table, path):
    atomic_write(path, table.to_text())
