import shlex
from dataclasses import dataclass

__all__ = ['VideoTiming', 'parse_modeline']


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


def parse_modeline(modeline: str):
    assert modeline.startswith("Modeline")
    modeline = shlex.split(modeline)

    pxclk = float(modeline[2])

    names = ["hres", "hsync_start", "hsync_end", "hscan", "vres", "vsync_start", "vsync_end", "vscan"]
    values = map(int, modeline[3:-2])

    return_dict = dict(zip(names, values))
    return_dict["pxclk"] = pxclk

    return VideoTiming(**return_dict)
