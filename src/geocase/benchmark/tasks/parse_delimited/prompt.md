You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `parse_delimited(line)` that takes a single comma-separated record as a string (no trailing newline) and returns its fields as a list of strings, following the RFC 4180 dialect: a field may be enclosed in double quotes, the enclosing quotes are not part of the field's value, and a doubled quote inside an enclosed field represents one literal quote character. Empty fields are preserved.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with the standard library only — no third-party packages are installed). Use only the standard library.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.
