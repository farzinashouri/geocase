You are writing one small self-contained Python module. Work exclusively inside {workdir} — do not read or modify anything outside that directory.

Task: Implement a function `elapsed_hours(start, end, tz_name)` where `start` and `end` are ISO 8601 local date-time strings without any offset (for example `"2026-03-01T09:30:00"`) and `tz_name` is an IANA time zone name (for example `"America/New_York"`). Both timestamps are local wall-clock times in that zone. Return, as a float, the number of hours that actually elapse between the two instants.

Requirements:
- Save the module as {module_path}. Importing the module must have no side effects.
- Interpreter: {python} (Python 3 with the standard library only — no third-party packages are installed). Use only the standard library.
- Verify that your code actually runs before finishing; put any scratch test files under {scratch_dir}/, not inside the module.
- When finished, reply with one line starting with DONE, followed by a one-sentence summary of your approach.
