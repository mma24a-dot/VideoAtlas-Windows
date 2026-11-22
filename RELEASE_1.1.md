# VideoAtlas 1.1 — Offline asset integrity release (source candidate)

New: `offline_bundle.py` and `verify_offline_bundle.py` provide local SHA-256 manifests for optional AI models, OCR language packs, FFmpeg binaries and other packaged assets. This enables integrity checks after transferring files to an air-gapped Windows PC. **The manifest itself must come from a trusted source**; hashes do not certify publisher authenticity. Symlinks escaping the bundle root and path traversal are rejected.

Example from the project directory (Python dependencies not needed for this CLI):

```bat
python verify_offline_bundle.py create C:\VideoAtlasAssets C:\VideoAtlasAssets\manifest.json bin/ffmpeg.exe bin/ffprobe.exe
python verify_offline_bundle.py verify C:\VideoAtlasAssets C:\VideoAtlasAssets\manifest.json
```

To create a manifest for AI model weights, list all required relative files; incomplete manifests cannot detect omitted files. Model inference is **not** made available by the manifest alone.

The Windows installer build remains a **Windows-only build step**. The archive is not a compiled `.exe` and does not contain FFmpeg or AI weights. No clean Windows installation, codec or GPU test has been performed.
