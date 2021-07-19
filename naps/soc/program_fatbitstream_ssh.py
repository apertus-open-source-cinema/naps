import subprocess
from pathlib import Path
from shlex import quote
import os

__all__ = ["run_ssh", "copy_ssh", "program_fatbitstream_ssh"]


default_host = os.getenv("SSH_HOST", "10.42.0.1")
default_user = os.getenv("SSH_USER", "operator")
default_password = os.getenv("SSH_PASSWORD", "axiom")


def run_ssh(cmd, host=default_host, user=default_user, password=default_password, sudo=False, sshpass=True):
    if sudo:
        cmd = f"echo {password} | sudo -S bash -c {quote(cmd)}"
    ssh_cmd = f"ssh {user}@{host} {quote(cmd)}"
    if sshpass:
        ssh_cmd = f"sshpass -p{password} {ssh_cmd}"
    print("\nexecuting: ", ssh_cmd)
    return subprocess.check_output(ssh_cmd, shell=True)


def copy_ssh(source, destination, host=default_host, user=default_user, password=default_password, sshpass=True):
    dst_string = f"{user}@{host}:{destination}"
    scp_cmd = f"scp {quote(source)} {quote(dst_string)}"
    if sshpass:
        scp_cmd = f"sshpass -p{password} {scp_cmd}"
    print("\nexecuting: ", scp_cmd)
    return subprocess.check_output(scp_cmd, shell=True)


def program_fatbitstream_ssh(fatbitstream_file, run=False, **kwargs):
    name = Path(fatbitstream_file).name
    copy_ssh(fatbitstream_file, f"~/{name}")
    run_ssh(f"chmod +x ./{name}")
    run_ssh(f"./{name}  {'--run' if run else ''}", sudo=True)
