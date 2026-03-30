import sys
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parents[1]
source_dir_str = str(SOURCE_DIR)
if source_dir_str not in sys.path:
    sys.path.insert(0, source_dir_str)