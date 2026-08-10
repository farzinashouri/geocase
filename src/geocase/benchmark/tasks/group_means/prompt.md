You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `group_means(rows)` where `rows` is a list of `(key, value)` pairs; `key` is a string and `value` is a float or `None`. Return a dict mapping each key that appears in the input to the mean of that key's values, using SQL `AVG` semantics: `None` values are excluded from both the numerator and the denominator, and a group whose values are all `None` maps to `None` rather than to a number. Every key present in the input must be present in the result.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with the standard library only — no third-party packages are installed). Use only the standard library.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.
