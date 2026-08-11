"""Oracle for shapefile_attrs (Plan 17 Phase 3).

A genuinely new trap category (`encoding`) with no geodesy in it.

The trap: a Shapefile's attributes live in its `.dbf` sidecar, and the DBF
field descriptor allocates **exactly 11 bytes for a field name, the last of
which is a terminator** — so a field name can be at most 10 characters. Names
longer than that were truncated when the file was written, and collisions among
the truncations were resolved by numbering (`temperatur`, `temperat_1`). The
silent failure is a function that reports the names a caller *expects* — the
original, untruncated ones — whether by hardcoding, by guessing from a schema,
or by reading a sidecar that preserved them. It returns a plausible list of
strings, raises nothing, and is wrong about what the file actually contains.

**The oracle is stated from the format spec, not read from the corpus.** dBASE
III+ / dBASE IV field descriptors are normative: 32 bytes each, starting at
offset 32, terminated by `0x0D`, with the name in bytes 0-10 as a
NUL-padded ASCII string. This grader parses that structure directly, so what it
asserts is what the bytes on disk say — never what `case.yaml` claims about
them. `case.yaml` for this case does carry `params.truncated_field_names`, and
reading it is exactly what `benchmark/fixtures.py` exists to prevent: the
oracle would then be only as correct as whoever wrote the YAML (Plan 15,
trap 1).
"""

import tempfile
from pathlib import Path

from geocase.benchmark.fixtures import stage_fixtures
from geocase.benchmark.registry import get_task

#: DBF field descriptors start here, are this long, and end at this byte.
_HEADER_LEN = 32
_DESCRIPTOR_LEN = 32
_TERMINATOR = 0x0D
#: The normative limit: 11 bytes for the name, the 11th being the terminator.
_MAX_FIELD_NAME_LEN = 10


def _dbf_field_names(dbf_path: Path) -> list[str]:
    """Field names straight out of the DBF header, per the dBASE spec."""
    data = dbf_path.read_bytes()
    names: list[str] = []
    offset = _HEADER_LEN
    while offset < len(data) and data[offset] != _TERMINATOR:
        raw = data[offset : offset + 11]
        names.append(raw.split(b"\x00")[0].decode("ascii"))
        offset += _DESCRIPTOR_LEN
    return names


def build_checks(f):
    staged = stage_fixtures(get_task("shapefile_attrs"), Path(tempfile.mkdtemp()))
    shp_path = staged["shp"]
    expected = _dbf_field_names(staged["dbf"])

    def field_count():
        got = f(str(shp_path))
        if not isinstance(got, (list, tuple)) or not all(
            isinstance(x, str) for x in got
        ):
            return False, f"got {got!r}, expected a list of strings"
        return (
            len(got) == len(expected),
            f"got {len(got)} field(s) {list(got)!r}, expected {len(expected)}",
        )

    def dbf_truncated_names():
        got = f(str(shp_path))
        if not isinstance(got, (list, tuple)) or not all(
            isinstance(x, str) for x in got
        ):
            return False, f"got {got!r}, expected a list of strings"
        got = list(got)
        # Stated from the spec: no DBF field name can exceed 10 characters, so
        # any longer name is one the file does not contain.
        overlong = [n for n in got if len(n) > _MAX_FIELD_NAME_LEN]
        if overlong:
            return (
                False,
                f"got {got!r} containing {overlong!r} — a DBF field name "
                f"cannot exceed {_MAX_FIELD_NAME_LEN} characters, so these "
                f"are not the names stored in the file",
            )
        return (
            got == expected,
            f"got {got!r}, expected {expected!r} (the names as the DBF "
            f"header stores them)",
        )

    return [
        ("field_count", "control", field_count),
        ("dbf_truncated_names", "edge", dbf_truncated_names),
    ]
