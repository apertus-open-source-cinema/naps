from functools import lru_cache
from json import loads

from nmigen._toolchain.yosys import find_yosys


@lru_cache()
def parse_yosys_json(verilog_paths):
    if isinstance(verilog_paths, str):
        verilog_paths = [verilog_paths]
    json = yosys_script([
        "\n".join("read_verilog {}".format(path) for path in verilog_paths),
        "write_json"
    ])
    return loads(json)


def get_verilog_module_ports(verilog_paths, module_name):
    """Get the ports of a verilog module via yosys

    :param verilog_paths:
    :param module_name:
    :return: the verilog as a string
    """

    parsed_json = parse_yosys_json(verilog_paths)
    module = parsed_json["modules"][module_name]
    ports = module["ports"]

    # do some reformatting of the data:
    def abbrev_direction(long_form):
        if long_form in ("output", "o"):
            return "o"
        elif long_form in ("input", "i"):
            return "i"
        elif long_form in ("inout", "io"):
            return "io"
        else:
            raise Exception("Bad direction: {}".format(long_form))

    for k, v in ports.items():
        if "bits" in v:
            ports[k]["width"] = len(v["bits"])
            del ports[k]["bits"]
        assert "width" in v

        ports[k]["direction"] = abbrev_direction(v["direction"])

    return ports


def yosys_script(commands):
    """Executes a yosys script

    :param commands: a list of commands to run
    :return: the stdout of yosys
    """

    return find_yosys(lambda ver: ver >= (0, 9)).run(["-q", "-p {}".format(";\n".join(commands))])
