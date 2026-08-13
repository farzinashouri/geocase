"""Oracle for allocate_cents: the rounding residue.

Rounding each share independently loses (or invents) cents whenever the total
is not divisible by the weight sum: 1000 split three ways becomes
``[333, 333, 333]``, which sums to 999. Right length, right types, plausible
values, no exception — the missing cent shows up only if someone adds them up.
"""


def _is_int_list(v, n):
    return (
        isinstance(v, list)
        and len(v) == n
        and all(isinstance(x, int) and not isinstance(x, bool) for x in v)
    )


def build_checks(f):
    def exact_split():
        got = f(900, [1, 1, 1])
        exp = [300, 300, 300]
        return _is_int_list(got, 3) and got == exp, f"got {got!r}, expected {exp!r}"

    def unequal_weights():
        got = f(1000, [3, 1])
        exp = [750, 250]
        return _is_int_list(got, 2) and got == exp, f"got {got!r}, expected {exp!r}"

    def indivisible_total():
        got = f(1000, [1, 1, 1])
        if not _is_int_list(got, 3):
            return False, f"got {got!r}, expected three ints summing to 1000"
        ok = sum(got) == 1000 and all(abs(x - 1000 / 3) <= 1 for x in got)
        return ok, (
            f"got {got!r} summing to {sum(got)}, expected three ints "
            f"summing to exactly 1000"
        )

    return [
        ("exact_split", "control", exact_split),
        ("unequal_weights", "control", unequal_weights),
        ("indivisible_total", "edge", indivisible_total),
    ]
