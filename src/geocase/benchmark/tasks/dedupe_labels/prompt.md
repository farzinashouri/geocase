You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `dedupe_labels(labels)` that takes a list of strings and returns a new list with duplicates removed, where two labels count as duplicates if they are the same text differing only in letter case. Keep the first occurrence of each label, unchanged, and preserve the input order.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with the standard library only — no third-party packages are installed). Use only the standard library.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.
