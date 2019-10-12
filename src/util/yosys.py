import subprocess
from json import loads, dumps


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
#    print(dumps(parsed_json, indent=2))
    module = parsed_json["modules"][module_name]
    ports = module["ports"]

    # do some reformatting of the data:
    def abbrev_direction(long_form):
        if long_form == "output": return "o"
        elif long_form == "input": return "i"
        elif long_form == "inout": return "io"
        else: raise Exception("Bad direction: {}".format(long_form))

    for k, v in ports.items():
        ports[k]["width"] = len(v["bits"])
        del ports[k]["bits"]

        ports[k]["direction"] = abbrev_direction(v["direction"])

    return ports


def yosys_script(commands):
    """Executes a yosys script

    :param commands: a list of commands to run
    :return: the stdout of yosys
    """
    commandline = 'yosys -q -p "{}"'.format(";\n".join(commands))
    return subprocess.check_output(commandline, shell=True)
