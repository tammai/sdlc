# Recurring defects

Defects that shipped past review before, from the plugin's evals. Every code reviewer checks each one. A project adds its own in `<docs>/recurring-defects.md`, in the same shape: Learn (in Ship) appends each defect Prove fixed that a reviewer could check next time, and the user can add one at any time. Keep each entry to one line: what it looks like, then the severity.

- **Raw system errors reach the user:** an `ENOENT`, `EACCES` or stack trace printed instead of the spec's message and exit code. High.
- **No fsync before rename:** a "safe write" that renames a temp file without flushing and syncing it, or leaves the temp file behind on failure. High when the data is persisted.
- **Duplicates in stored data accepted:** a second record with the same id or key is written, or a stored file with duplicates loads without error. High when ids must be unique.
- **Verbose library errors:** a parser's or library's raw message (JSON position, schema dump) shown to the user instead of a short message naming what's wrong. Medium.
- **Unrequested dev dependencies or manifest fields:** a new devDependency, lint plugin, `bin`, `engines` or `packageManager` field the spec didn't ask for. High (unrequested public surface).
