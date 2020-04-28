import subprocess
from shlex import quote


def run_on_camera(cmd, host="10.42.0.1", user="operator", password="axiom", sudo=True, sshpass=True):
    if sudo:
        cmd = "echo {} | sudo -S bash -c {}".format(password, quote(cmd))
    ssh_cmd = "ssh {}@{} {}".format(user, host, quote(cmd))
    if sshpass:
        ssh_cmd = "sshpass -p{} {}".format(password, ssh_cmd)
    print("\nexecuting: ", ssh_cmd)
    return subprocess.check_output(ssh_cmd, shell=True)


def copy_to_camera(source, destination, host="10.42.0.1", user="operator", password="axiom", sshpass=True):
    scp_cmd = "scp {} {}".format(quote(source), quote("{}@{}:{}".format(user, host, destination)))
    if sshpass:
        scp_cmd = "sshpass -p{} {}".format(password, scp_cmd)
    print("\nexecuting: ", scp_cmd)
    return subprocess.check_output(scp_cmd, shell=True)


def program_bitstream_camera(build_products, name, **kwargs):
    print("\n\nprogramming camera...")
    bitstream_name = "{}.bit".format(name)
    with build_products.extract(bitstream_name, "mmap/regs.sh", "mmap/init.sh") as (bitstream_file, regs_script, init_script):
        copy_to_camera(bitstream_file, "~/{}".format(bitstream_name), **kwargs)
        copy_to_camera(regs_script, "~/regs.sh", **kwargs)
        copy_to_camera(init_script, "~/init.sh", **kwargs)

    run_on_camera("/opt/axiom-firmware/makefiles/in_chroot/to_raw_bitstream.py -f "
                  "/home/operator/{name} "
                  "/usr/lib/firmware/{name}".format(name=bitstream_name), **kwargs)
    run_on_camera("echo {} > /sys/class/fpga_manager/fpga0/firmware".format(bitstream_name), **kwargs)
    run_on_camera("sh /home/operator/init.sh".format(bitstream_name), **kwargs)
