import re
from inspect import getsource
from os.path import dirname, join
from textwrap import indent, dedent

from nmigen.build import Platform

from ..fatbitstream import FatbitstreamContext
from ..memorymap import MemoryMap
from ..tracing_elaborate import ElaboratableSames


def gen_hardware_proxy_python_code(mmap: MemoryMap, name="design", superclass="", top=True) -> str:
    name = name.lower()
    class_name = ("_" if not top else "") + name.capitalize()
    to_return = "class {}({}):\n".format(class_name, superclass)
    for row in mmap.direct_children:
        address = mmap.own_offset.translate(row.address)
        to_return += indent(
            "{} = (0x{:02x}, {}, {})\n".format(row.name, address.address, address.bit_offset, address.bit_len),
            "    "
        )
    for name, method in mmap.driver_methods.items():
        function_body = dedent(getsource(method.function))
        function_body_without_decorator = re.sub("^@.*$", "", function_body, flags=re.MULTILINE).strip()
        function_string = ("@property\n" if method.is_property else "") + function_body_without_decorator
        to_return += indent("\n" + function_string + "\n", "    ")

    for row in mmap.subranges:
        to_return += indent(gen_hardware_proxy_python_code(row.obj, row.name, superclass=superclass, top=False), "    ")
    return to_return


def generate_pydriver(top_memorymap, memory_accessor):
    pycode = "# pydriver hardware access file"
    pycode += "\n\n## HARDWARE PROXY STATIC: ###\n"
    pycode += open(join(dirname(__file__), "hardware_proxy.py")).read()
    pycode += "\n\n## HARDWARE PROXY DYNAMIC: ###\n"
    pycode += gen_hardware_proxy_python_code(top_memorymap, superclass="HardwareProxy")
    pycode += "\n\n## MEMORY ACCESSOR: ###\n"
    pycode += memory_accessor
    pycode += "\n\n## INTERACTIVE SHELL: ###\n"
    pycode += open(join(dirname(__file__), "interactive.py")).read()
    return pycode


def pydriver_hook(platform: Platform, top_fragment, sames: ElaboratableSames):
    if hasattr(platform, "pydriver_memory_accessor"):
        memorymap = top_fragment.memorymap
        pydriver = generate_pydriver(memorymap, platform.pydriver_memory_accessor)
        fc = FatbitstreamContext.get(platform)
        fc.self_extracting_blobs["pydriver.py"] = pydriver
