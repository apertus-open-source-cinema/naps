from naps import naps_getenv
from paramiko import SSHClient
from paramiko.py3compat import u
from pathlib import Path
import socket
import sys
import termios
import tty

__all__ = ["program_fatbitstream_ssh"]

default_host = naps_getenv("SSH_HOST", "10.42.0.1")
default_user = naps_getenv("SSH_USER", "operator")
default_password = naps_getenv("SSH_PASSWORD", "axiom")


# The following excerpt is stolen from paramiko:
# Copyright (C) 2003-2007  Robey Pointer <robeypointer@gmail.com>
def interactive_shell(stdin, stdout, stderr):
    import select
    stdout = stdout.channel
    stderr = stderr.channel
    stdout.settimeout(0.0)
    stderr.settimeout(0.0)

    oldtty = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())

        def pump(f, t):
            try:
                x = u(f.recv(1024))
                if len(x) == 0:
                    return True
                t.write(x)
                t.flush()
            except socket.timeout:
                pass
            return False

        while True:
            r, w, e = select.select([stdout, stderr, sys.stdin], [], [])
            if stdout in r and pump(stdout, sys.stdout):
                break
            if stderr in r and pump(stderr, sys.stdout):
                break
            if sys.stdin in r:
                x = sys.stdin.read(1)
                if len(x) == 0:
                    break
                stdin.write(x)

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)


def program_fatbitstream_ssh(fatbitstream_file: Path, *, run=False, dir="fatbitstreams", **kwargs):
    name = fatbitstream_file.name
    with SSHClient() as client:
        client.load_system_host_keys()
        client.connect(hostname=default_host, username=default_user, password=default_password)

        with client.open_sftp() as sftp:
            try:
                sftp.mkdir(f"{dir}")
            except IOError as e:
                # ignore if dir is already existing
                if e.errno:
                    raise e

            sftp.chdir(dir)
            with sftp.file(name, "w") as f:
                f.write(fatbitstream_file.read_bytes())
                f.chmod(0o777)

        (stdin, stdout, stderr) = client.exec_command(f"cd {dir} && sudo ./{name} {'--run' if run else ''}\n",
                                                      get_pty=True)
        # for sudo
        stdin.write(default_password + '\n')
        interactive_shell(stdin, stdout, stderr)
