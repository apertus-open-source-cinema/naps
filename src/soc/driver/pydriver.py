from textwrap import indent
from os.path import dirname, join

from nmigen.build import Platform

from soc.memorymap import MemoryMap
from soc.tracing_elaborate import ElaboratableSames


def gen_mmap_python_code(mmap: MemoryMap, name="top", superclass="") -> str:
    name = name.lower()
    class_name = "_" + name.capitalize()
    to_return = "class {}({}):\n".format(class_name, superclass)
    for row in mmap.normal_resources:
        address = mmap.own_offset.translate(row.address)
        to_return += indent(
            "{} = (0x{:02x}, {}, {})\n".format(row.name, address.address, address.bit_offset, address.bit_len), "    ")
    for row in mmap.subranges:
        to_return += indent(gen_mmap_python_code(row.obj, row.name, superclass=superclass), "    ")
    to_return += "{} = {}()\n".format(name, class_name)
    return to_return


def generate_pydriver(top_memorymap):
    with open(join(dirname(__file__), "pydriver_device_code.py")) as f:
        pycode = f.read()
        pycode += gen_mmap_python_code(top_memorymap, superclass="CSRApiWrapper")
        return pycode


def pydriver_hook(platform: Platform, top_fragment, sames: ElaboratableSames):
    memorymap = top_fragment.memorymap
    pydriver = generate_pydriver(memorymap)
    platform.add_file("pydriver.py", pydriver.encode("utf-8"))
