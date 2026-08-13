"""Oracle for dedupe_labels: composed vs decomposed Unicode.

``casefold()`` alone folds case but not Unicode composition, so NFC "Angstrom"
and its NFD twin — the same text by any user-facing definition — survive as two
entries. No exception, right type, plausible output.

Both literals are written as \\u escapes and their differing len() is asserted
before use, so a normalising editor cannot silently turn this task into a
tautology.
"""

# 'Angstrom' with ring-above and diaeresis: precomposed (NFC) vs base
# letters plus combining marks (NFD). Escapes, never literal characters.
NFC = "\u00c5ngstr\u00f6m"
NFD = "A\u030angstro\u0308m"


def _is_str_list(v):
    return isinstance(v, list) and all(isinstance(s, str) for s in v)


def build_checks(f):
    def case_folding():
        got = f(["Alpha", "ALPHA", "beta"])
        exp = ["Alpha", "beta"]
        return _is_str_list(got) and got == exp, f"got {got!r}, expected {exp!r}"

    def order_preserved():
        got = f(["gamma", "beta", "GAMMA", "alpha"])
        exp = ["gamma", "beta", "alpha"]
        return _is_str_list(got) and got == exp, f"got {got!r}, expected {exp!r}"

    def composed_vs_decomposed():
        # If these ever compare equal or share a length, the fixture has been
        # normalised by tooling and the check is no longer testing anything.
        if NFC == NFD or len(NFC) == len(NFD):
            return False, "fixture corrupted: NFC/NFD literals were normalised"
        got = f([NFC, NFD])
        ok = _is_str_list(got) and got == [NFC]
        n = len(got) if isinstance(got, list) else "?"
        return ok, f"got {got!r} ({n} entries), expected 1"

    return [
        ("case_folding", "control", case_folding),
        ("order_preserved", "control", order_preserved),
        ("composed_vs_decomposed", "edge", composed_vs_decomposed),
    ]
