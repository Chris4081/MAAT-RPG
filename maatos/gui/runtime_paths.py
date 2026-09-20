"""Optional portable/test data root, applied before importing profile modules."""
import os
from pathlib import Path


def configure():
    override = os.environ.get('MAAT_GUI_DATA_ROOT')
    if not override:
        return
    from shared.core import maat_paths
    def base():
        path = Path(override).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    maat_paths.get_default_app_support_dir = base
    maat_paths._default_app_support_dir = base
