import os
from pathlib import Path

__all__ = ["program_fatbitstream_local"]


def program_fatbitstream_local(fatbitstream, run=False):
    os.chdir(Path(fatbitstream).parent)
    os.system(f"./{Path(fatbitstream).name} {'--run' if run else ''}")
