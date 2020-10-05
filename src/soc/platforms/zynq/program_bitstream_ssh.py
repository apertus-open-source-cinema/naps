import subprocess
from base64 import b64encode
from shlex import quote

from nmigen.build.run import BuildProducts

from .to_raw_bitstream import bit2bin

default_host = "10.42.0.224"
default_user = "operator"
default_password = "axiom"


def run_on_camera(cmd, host=default_host, user=default_user, password=default_password, sudo=True, sshpass=True):
    if sudo:
        cmd = "echo {} | sudo -S bash -c {}".format(password, quote(cmd))
    ssh_cmd = "ssh {}@{} {}".format(user, host, quote(cmd))
    if sshpass:
        ssh_cmd = "sshpass -p{} {}".format(password, ssh_cmd)
    print("\nexecuting: ", ssh_cmd)
    return subprocess.check_output(ssh_cmd, shell=True)


def copy_to_camera(source, destination, host=default_host, user=default_user, password=default_password, sshpass=True):
    scp_cmd = "scp {} {}".format(quote(source), quote("{}@{}:{}".format(user, host, destination)))
    if sshpass:
        scp_cmd = "sshpass -p{} {}".format(password, scp_cmd)
    print("\nexecuting: ", scp_cmd)
    return subprocess.check_output(scp_cmd, shell=True)


def self_extracting_blob(data, path):
    return "base64 -d > {} <<EOF\n{}\nEOF\n\n".format(quote(path), b64encode(data).decode("ASCII"))


def pack_zynq_bitstream():
    pass


def build_fatbitstream(pack_bitstream=pack_zynq_bitstream):
    fatstring = ""

    bitstream_name = "{}.bit".format(name)
    bin_bitstream = bit2bin(build_products.get(bitstream_name), flip_data=True)
    fatstring += self_extracting_blob(bin_bitstream, "/usr/lib/firmware/{}.bin".format(name))

    fatstring += "\n# extra files:\n"
    for path, contents in platform.extra_files.items():
        fatstring += self_extracting_blob(contents, path) + "\n"

    init_script = "\n# init script:\n"
    init_script += "echo {}.bin > /sys/class/fpga_manager/fpga0/firmware\n".format(name)
    init_script += platform.init_script
    fatstring += init_script

    fatstring


def program_bitstream_ssh(platform, build_products: BuildProducts, name, **kwargs):
    fatfile_name = "{}.fatbitstream.sh".format(name)
    with open(fatfile_name, "w") as f:
        f.write()
    copy_to_camera(fatfile_name, "/home/operator/{}.fatbitstream.sh".format(name), **kwargs)
    run_on_camera("bash /home/operator/{}.fatbitstream.sh".format(name), **kwargs)
