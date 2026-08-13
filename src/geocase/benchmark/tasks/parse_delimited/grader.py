"""Oracle for parse_delimited: a delimiter inside an enclosed field.

``line.split(",")`` returns a plausible list of strings — right type, no
exception, correct for the controls — with one field too many the moment a
comma appears inside quotes.
"""


def _is_str_list(v):
    return isinstance(v, list) and all(isinstance(s, str) for s in v)


def build_checks(f):
    def plain_fields():
        got = f("a,b,c")
        exp = ["a", "b", "c"]
        return _is_str_list(got) and got == exp, f"got {got!r}, expected {exp!r}"

    def empty_fields_preserved():
        got = f("a,,c,")
        exp = ["a", "", "c", ""]
        return _is_str_list(got) and got == exp, f"got {got!r}, expected {exp!r}"

    def quoted_delimiter():
        got = f('a,"b,c",d')
        exp = ["a", "b,c", "d"]
        return _is_str_list(got) and got == exp, f"got {got!r}, expected {exp!r}"

    return [
        ("plain_fields", "control", plain_fields),
        ("empty_fields_preserved", "control", empty_fields_preserved),
        ("quoted_delimiter", "edge", quoted_delimiter),
    ]
