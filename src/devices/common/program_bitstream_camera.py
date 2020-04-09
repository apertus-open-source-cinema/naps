import subprocess
import tempfile


def program_bitstream_camera(camera_host, bitstream):
    with tempfile.mktemp(suffix=".bit") as (open_file, bitstream_path):
        open_file.write(bitstream)

    subprocess.check_output("scp '{}' '{}:~/'".format(bitstream_path, camera_host))
    subprocess.check_output("ssh {} -e '{}'".format(camera_host, "/opt/axiom_firmware/makefiles/in_chroot/hsienar"))
    subprocess.check_output("ssh {} -e '{}'".format(camera_host, "echo {} > /sys/class/fpga"))