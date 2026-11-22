# VideoAtlas 1.2 — Portable library migration

- Adds a ZIP export of a consistent SQLite snapshot, thumbnails, and folder settings. **Original videos are not copied.**
- Adds GUI backup package validation with SHA-256 verification and SQLite integrity check.
- Adds `restore_library.py backup.zip NEW_DIRECTORY` for safe restoration into a non-existing directory. Shut down VideoAtlas before manually migrating restored data into the application profile.
- Rejects duplicate/unsafe ZIP entries, unsupported manifests, tampering, and archives exceeding 8 GiB uncompressed or 250,000 entries.
- No bundled Windows executable, FFmpeg, or AI models; Windows installation and actual AI inference remain unverified.
