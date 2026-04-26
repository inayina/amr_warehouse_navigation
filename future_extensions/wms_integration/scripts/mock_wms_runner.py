#!/usr/bin/env python3

from pathlib import Path
import sys


EXTENSION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXTENSION_ROOT))

from task_manager.wms_dispatcher import main


if __name__ == '__main__':
    main()
