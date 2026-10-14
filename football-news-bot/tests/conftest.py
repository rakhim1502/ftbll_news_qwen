"""pytest sozlamalari: `app` paketini import qilish uchun loyiha ildizini sys.path'ga qo'shamiz."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
