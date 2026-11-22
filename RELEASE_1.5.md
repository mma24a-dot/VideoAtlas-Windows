# VideoAtlas v1.5 — Local model integration

- Registered local Whisper model now used for selected-video transcription and batch transcription.
- Registered CLIP model now used for semantic search and batch semantic indexing.
- Registered Tesseract tessdata path passed into OCR subprocesses, both single-frame and batch.
- Clear errors when a registered model is missing or invalid.
- No automatic downloads or cloud calls introduced.

**Limitations:** Windows installer has not been compiled or tested; AI inference requires local executables, dependencies, and genuine models. No runtime GPU benchmark has been performed.
