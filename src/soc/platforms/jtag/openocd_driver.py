class JtagCsr:
    def __init__(self, addr="127.0.0.1", port=4444, timeout=1024, debug=False, spawn_server=False):
        import socket
        import os
        import time

        if spawn_server:
            addr = "127.0.0.1"
            port = 4444
            os.system('openocd -c "source [find interface/ftdi/digilent_jtag_hs3.cfg]; source [find cpld/xilinx-xc7.cfg]; transport select jtag; adapter_khz 20000; bindto 0.0.0.0; init;" > /dev/null 2>&1 &')
            time.sleep(0.1)

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((addr, port))
        self.timeout = timeout
        self.debug = debug
        self.spawn_server = spawn_server


        # skip some strange random shit
        self._readline(decode=False)

    def __del__(self):
        if self.spawn_server:
            self._writeline("shutdown")

    def _writeline(self, message):
        message += "\n"
        self.s.send(message.encode('utf-8'))

    def _readline(self, decode=True):
        buf = b""

        while buf[-2:] != b'> ':
            buf += self.s.recv(1)

        if decode and self.debug:
            print(buf.decode('utf-8'))

        buf = buf.rsplit(b'\r\n', 2)[1][1:]

        if decode:
            buf = buf.decode('utf-8')

        return buf

    def _writecmd(self, cmd):
        # print(cmd)
        self._writeline(cmd)
        ret = self._readline()
        # print(ret)
        return ret

    def _irscan(self, instruction):
        return self._writecmd('irscan xc7.tap {}'.format(instruction))

    def _drscan(self, len, value):
        return self._writecmd('drscan xc7.tap {} {}'.format(len, value))

    def write(self, addr, value):
        # RESET jtag csr
        self._irscan(0)

        # USER1
        self._irscan(2)

        # WRITE command
        self._drscan(1, 1)

        # ADDRESS
        self._drscan(32, addr)

        # DATA
        self._drscan(32, value)

        timeout = self.timeout
        while self._drscan(1, 0) != "01":
            if timeout == 0:
                raise Exception("write poll completion polling timeout")

            timeout -= 1
            pass

        # RESP code
        resp = self._drscan(1, 0)

        return int(resp)

    def read(self, addr):
        # RESET jtag csr
        self._irscan(0)

        # USER1
        self._irscan(2)

        # READ command
        self._drscan(1, 0)

        # ADDRESS
        self._drscan(32, addr)

        # POLL for read completion
        while self._drscan(1, 0) != "01":
            if timeout == 0:
                raise Exception("read poll completion polling timeout")

            timeout -= 1

            pass

        # DATA
        data = self._drscan(32, 0)

        # RESP code
        resp = self._drscan(1, 0)

        return int(data, 16), int(resp)


if __name__ == "__main__":
    jtag_csr = JtagCsr("127.0.0.1", 4444, debug=False, spawn_server=True)

    import random

    for _ in range(0, 1024):
        rand = random.randint(0, 2**32 - 1)
        # rand = random.randint(2**32 - 1024, 2**32)
        jtag_csr.write(4, rand)
        read = jtag_csr.read(3)[0]
        assert read == rand, "{} != {}".format(read, rand)
