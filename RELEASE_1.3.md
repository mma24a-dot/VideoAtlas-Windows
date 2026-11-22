# VideoAtlas 1.3 — GUI restoration and offline drive remapping

- GUI menu action **Restore to new folder** validates a ZIP backup and extracts it into a newly created folder without overwriting the running catalog.
- `remap_restored_library.py RESTORED_DIR OLD_ROOT NEW_ROOT` previews path changes; add `--apply` to modify only that restored database and its `folders.txt`.
- Windows drive-letter and UNC-root handling uses path-component-aware prefix matching; collision detection prevents duplicate paths.
- Does not change original video files, thumbnails, or the live catalog. A restored catalog still requires deliberate manual migration into the active profile after exiting VideoAtlas.
- Windows installer and bundled AI runtimes remain unverified; this is a source release.
