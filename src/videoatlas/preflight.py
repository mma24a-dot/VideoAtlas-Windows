"""Offline preflight checks for processing jobs. No network calls or model downloads."""
from pathlib import Path
from .deployment import find_tool
from .model_resolution import resolve_model

REQUIRED_TOOLS = {
    'scenes': ('ffmpeg',),
    'hash': (),
    'ocr': ('ffmpeg', 'tesseract'),
    'transcript': ('ffmpeg', 'whisper-cli'),
    'semantic': ('ffmpeg',),
}
MODEL_KINDS = {'ocr': 'tesseract', 'transcript': 'whisper', 'semantic': 'clip'}


def check_job(kind, base, explicit_model=None, root=None):
    """Return a structured readiness report without executing a video job."""
    if kind not in REQUIRED_TOOLS:
        raise ValueError(f'Unknown job type: {kind}')
    missing = []
    tools = {}
    for name in REQUIRED_TOOLS[kind]:
        path = find_tool(name, root)
        tools[name] = path
        if not path:
            missing.append(f'Missing executable: {name}')
    model = None
    if kind in MODEL_KINDS:
        try:
            model = resolve_model(base, MODEL_KINDS[kind], explicit=explicit_model)
        except (RuntimeError, ValueError, OSError) as exc:
            missing.append(str(exc))
    return {'job': kind, 'ready': not missing, 'tools': tools,
            'model': model, 'problems': missing}


def check_all(base, root=None):
    return {kind: check_job(kind, base, root=root) for kind in REQUIRED_TOOLS}
