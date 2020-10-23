class JTAGAccessor:
    base = 0

    def __init__(self, addr="127.0.0.1", port=4444, timeout=1024, debug=False, spawn_server=True, tap_name="dut.tap",
                 lattice_quirk=True):
        import socket
        import os
        import time

        self.tap_name = tap_name

        if spawn_server:
            addr = "127.0.0.1"
            port = 4444
            os.system('openocd -f openocd.cfg > /dev/null 2>&1 &')
            time.sleep(0.1)

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((addr, port))
        self.timeout = timeout
        self.debug = debug
        self.spawn_server = spawn_server
        self.lattice_quirk = lattice_quirk

        # skip some strange random shit
        self._readline(decode=False)

    def __del__(self):
        if self.spawn_server:
            self._writeline("shutdown")

    def read(self, addr):
        # RESET jtag csr
        self._reset()

        # USER1
        self._irscan(0x32)

        # READ command
        self._drscan(1, 0)

        # ADDRESS
        self._drscan(32, addr)

        # POLL for read completion
        timeout = self.timeout
        while self._drscan(1, 0) != "01":
            if timeout == 0:
                raise Exception("read poll completion polling timeout")

            timeout -= 1

            pass

        # DATA
        data = self._drscan(32, 0)

        # RESP code
        resp = int(self._drscan(1, 0))
        if resp != 0:
            raise TransactionNotSuccessfulException()

        data = int(data, 16)
        if self.lattice_quirk:
            data = data >> 1

        return data

    def write(self, addr, value):
        # RESET jtag csr
        self._reset()

        # USER1
        self._irscan(0x32)

        # WRITE command
        self._drscan(1, 1)

        # ADDRESS
        self._drscan(32, addr)

        # DATA
        self._drscan(32, value)

        # Poll for write completion
        timeout = self.timeout
        while self._drscan(1, 0) != "01":
            if timeout == 0:
                raise Exception("write poll completion polling timeout")

            timeout -= 1
            pass

        # RESP code
        resp = int(self._drscan(1, 0))
        if resp != 0:
            raise TransactionNotSuccessfulException()

        return

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
        return self._writecmd('irscan {} {}'.format(self.tap_name, instruction))

    def _reset(self):
        return self._writecmd('reset halt')

    def _drscan(self, len, value):
        return self._writecmd('drscan {} {} {}'.format(self.tap_name, len, value))


MemoryAccessor = JTAGAccessor


class TransactionNotSuccessfulException(Exception):
    pass
