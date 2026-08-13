You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `allocate_cents(total, weights)` where `total` is a non-negative integer number of cents and `weights` is a list of positive numbers. Return a list of integers, the same length as `weights`, giving each entry's share of `total` in proportion to its weight. The returned integers must sum to exactly `total`, and each share must be within one cent of its exact proportional value.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with the standard library only — no third-party packages are installed). Use only the standard library.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.
