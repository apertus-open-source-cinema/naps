import re
import subprocess
from typing import Dict

from nmigen.back import rtlil


def get_module_sizes(module, *args, **kwargs):
    rtlil_text = rtlil.convert(module, *args, **kwargs)

    script = """
        read_ilang <<rtlil
        {}
        rtlil
        
        expose top
        
        synth_xilinx -abc9
    """.format(rtlil_text)

    popen = subprocess.Popen(["yosys", "-s", "-"],
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             encoding="utf-8")
    output, error = popen.communicate(script)

    return {
        re.findall("== (.*?) ===", section)[0]: re.findall("Estimated number of LCs:\\W*(\\d+)", section)[0]
        for section in re.findall("== .*? ===.*?=", output, flags=re.DOTALL)
    }


def print_module_sizes(module, *args, **kwargs):
    module_sizes: Dict[str, str] = get_module_sizes(module, *args, **kwargs)
    max_module_size = max(int(v) for v in module_sizes.values())

    for name, size in module_sizes.items():
        print(name.ljust(30), size.ljust(3), "".join("=" for _ in range(int(int(size) / max_module_size * 80))))