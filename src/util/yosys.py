import subprocess
from json import loads
import pandas as pd


def get_module_ports(verilog_path, module_name):
    """Get the ports of a verilog module via yosys

    :param verilog_path: the path of the verilog file
    :return: the verilog as a string
    """
    json = yosys_script([
        "read_verilog {}".format(verilog_path),
        "write_json"
    ])
    parsed_json = loads(json)
    module = parsed_json["modules"][module_name]
    ports = module["ports"]

    # do some reformatting of the data:
    def abbrev_direction(long_form):
        if long_form == "output": return "o"
        elif long_form == "input": return "i"
        elif long_form == "inout": return "io"
        else: raise Exception("Bad direction: {}".format(long_form))

    ports_list = []
    for key in ports:
        ports_list.append({
            "name": key,
            "direction": abbrev_direction(ports[key]["direction"]),
            "width": len(ports[key]["bits"]),
        })

    return ports_list


def yosys_script(commands):
    """Executes a yosys script

    :param commands: a list of commands to run
    :return: the stdout of yosys
    """
    commandline = 'yosys -q -p "{}"'.format(";\n".join(commands))
    return subprocess.check_output(commandline, shell=True)
