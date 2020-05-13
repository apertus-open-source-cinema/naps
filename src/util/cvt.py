import subprocess
import shlex
from dataclasses import dataclass

CVT_BIN = "cvt"

@dataclass
class VideoTiming:
    pxclk: float
    hres: int
    hsync_start: int
    hsync_end: int
    hscan: int
    vres: int
    vsync_start: int
    vsync_end: int
    vscan: int


def generate_modeline(width, height, refresh, reduced_blanking=True):
    if (refresh % 60) != 0:
        reduced_blanking = False  # only possible for multiples of 60 Hz

    cvt_bin = ([CVT_BIN] + ["-r"]) if reduced_blanking else [CVT_BIN]
    out, _ = subprocess.Popen(cvt_bin + [str(width), str(height), str(refresh)],
                              stdout=subprocess.PIPE).communicate()
    return out.split(b"\n")[1].decode("utf-8")


def parse_modeline(modeline: str):
    assert modeline.startswith("Modeline")
    modeline = shlex.split(modeline)

    pxclk = float(modeline[2])

    names = ["hres", "hsync_start", "hsync_end", "hscan", "vres", "vsync_start", "vsync_end", "vscan"]
    values = map(int, modeline[3:-2])

    return_dict = dict(zip(names, values))
    return_dict["pxclk"] = pxclk

    return VideoTiming(**return_dict)
