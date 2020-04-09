import subprocess
import tempfile


def run_on_camera(cmd, camera_host="10.42.0.1", camera_user="operator"):
    return subprocess.check_output("ssh {}@{} '{}'".format(camera_user, camera_host, cmd), shell=True)


def program_bitstream_camera(camera_host, bitstream, name, camera_user="operator"):
    open_file, bitstream_path = tempfile.mktemp(suffix=".bit")
    open_file.write(bitstream)
    open_file.close()

    subprocess.check_output("scp '{}' '{}@{}:~/{}.bit'".format(bitstream_path, camera_user, camera_host, name))
    run_on_camera("/opt/axiom-firmware/makefiles/in_chroot/to_raw_bitstream.py -f "
                  "/home/operator/{name}.bit "
                  "/usr/lib/firmware/{name}.bin".format(name=name))
    run_on_camera("echo {}.bin > /sys/class/fpga_manager/fpga0/firmware".format(name))
