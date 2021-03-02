class JTAGAccessor:
    base = 0

    def __init__(self, addr="127.0.0.1", port=4444, timeout=1024, debug=False, spawn_server=True, tap_name="dut.tap"):
        import socket
        import os
        import time
        from os.path import dirname, abspath

        self.tap_name = tap_name

        if spawn_server:
            addr = "127.0.0.1"
            port = 4444
            os.system('cd {}; openocd -f openocd.cfg > /dev/null 2>&1 &'.format(dirname(abspath(__file__))))
            time.sleep(0.1)

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((addr, port))
        self.timeout = timeout
        self.debug = debug
        self.spawn_server = spawn_server

        # skip some strange random shit
        self._readline(decode=False)
        self._irscan(0x32)
        for i in range(3):
            self._shift_word(0)

    def __del__(self):
        if hasattr(self, "spawn_server") and self.spawn_server:
            self._writeline("shutdown")

    def read(self, addr):
        self._shift_bit(0)  # wakeup
        self._shift_bit(1)  # wakeup
        self._shift_word(addr)  # address
        self._shift_bit(0)  # read

        # read wait
        timeout = self.timeout
        for t in range(timeout):
            if self._shift_bit(1) == 1:
                break
            if t == timeout - 1:
                raise TimeoutError()

        data = self._shift_word(0)
        if self._shift_bit(0) != 0:  # read status
            raise TransactionNotSuccessfulException()

        return data

    def write(self, addr, value):
        self._shift_bit(0)  # wakeup
        self._shift_bit(1)  # wakeup
        self._shift_word(addr)  # address
        self._shift_bit(1)  # write
        self._shift_word(value)

        # write wait
        timeout = self.timeout
        for t in range(timeout):
            if self._shift_bit(1) == 1:
                break
            if t == timeout - 1:
                raise TimeoutError()
        if self._shift_bit(0) != 0:  # write status
            raise TransactionNotSuccessfulException()

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
        self._writeline(cmd)
        ret = self._readline()
        if self.debug:
            print(cmd, "->", ret)
        return ret

    def _shift_word(self, write):
        return int(self._drscan(32, write), 16)

    def _shift_bit(self, write):
        return int(self._drscan(1, write), 16)

    def _irscan(self, instruction):
        return self._writecmd('irscan {} {}'.format(self.tap_name, instruction))

    def _drscan(self, len, value):
        return self._writecmd('drscan {} {} {}'.format(self.tap_name, len, value))


MemoryAccessor = JTAGAccessor


class TransactionNotSuccessfulException(Exception):
    pass
