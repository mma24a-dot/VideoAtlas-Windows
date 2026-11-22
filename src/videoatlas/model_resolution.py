"""Resolve configured offline models, without network access or downloads."""
from pathlib import Path
from .model_registry import load_registry, validate_model


def resolve_model(base, kind, explicit=None, required=True):
    """Explicit user selection wins; otherwise use the saved model registry."""
    candidate = explicit or load_registry(base).get(kind)
    if not candidate:
        if required:
            raise RuntimeError(f'No local {kind} model configured. Open Local AI models.')
        return None
    valid, path = validate_model(kind, candidate)
    if not valid:
        raise RuntimeError(f'Configured {kind} model is missing or invalid: {path}')
    return path


def tesseract_environment(tessdata):
    """Return an environment overlay for an explicitly configured tessdata directory."""
    return {'TESSDATA_PREFIX': str(Path(tessdata).resolve())} if tessdata else {}
