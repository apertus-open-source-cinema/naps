# Utils for generating "fatbitstreams" (files that contain loading-logic, a bitstream, initialization and maybe drivers)
import enum
import textwrap
from enum import Enum
from typing import BinaryIO, Union, Iterable
from zipfile import ZipFile, ZIP_DEFLATED

__all__ = ["FatbitstreamContext", "File", "CommandPosition"]

from nmigen.build.run import BuildProducts


class CommandPosition(Enum):
    Front = enum.auto()
    Back = enum.auto()


class File:
    def __init__(self, name, contents):
        self.name = name
        self.contents = contents


class FatbitstreamContext:
    platform_to_context_dict = {}

    @classmethod
    def get(cls, platform):
        """
        Implements a singleton-like pattern here to have exactly one FatbitstreamContext per Platform instance
        :rtype: FatbitstreamContext
        """
        while hasattr(platform, "_wrapped_platform"):  # we cant check directly for isinstance SocPlatform here because of cyclic imports
            platform = platform._wrapped_platform

        if platform not in cls.platform_to_context_dict:
            cls.platform_to_context_dict[platform] = FatbitstreamContext(platform, called_by_get_classmethod=True)
        return cls.platform_to_context_dict[platform]

    def __init__(self, platform, called_by_get_classmethod=False):
        assert called_by_get_classmethod

        self._files = {}  # a dict of filename -> contents
        self._init_commands = []

        self._platform = platform

    def __iadd__(self, other):
        if isinstance(other, File):
            self._files[other.name] = other.contents
        elif isinstance(other, str):
            self.add_cmds(other, CommandPosition.Back)
        else:
            raise TypeError("only Files or shell commands can be added to the fatbitstream")
        return self

    def add_cmds(self, new_cmds: Union[str, Iterable[str]], new_pos=CommandPosition.Back):
        if isinstance(new_cmds, str):
            new_cmds = [new_cmds]

        if new_pos == CommandPosition.Back:
            self._init_commands.extend(new_cmds)
        else:
            self._init_commands[0:0] = new_cmds

    def add_cmd_unique(self, new_cmd: str, new_pos=CommandPosition.Back):
        assert isinstance(new_cmd, str)

        for cmd in self._init_commands:
            if new_cmd == cmd:
                break
        else:
            self.add_cmds(new_cmd, new_pos)

    def generate_fatbitstream(self, file: BinaryIO, build_name: str, build_products: BuildProducts):
        file.write(b'#!/usr/bin/env -S python3\n')

        def dedent(str):
            return "".join(textwrap.dedent(str).splitlines(keepends=True)[1:])

        main_script = dedent("""
            #!/usr/bin/env python3
            
            import os
            import sys
            from pathlib import Path


            def system(cmd, print_error=True):
                print(f"\\033[1;31m$ {cmd}\\033[0m")
                exit_code = os.waitstatus_to_exitcode(os.system(cmd))
                if exit_code != 0:
                    if print_error:
                        print(f"{cmd} failed with exit code {exit_code}")
                    sys.exit(exit_code)
            
            
            __dir__ = Path(__file__).parent
            if __dir__.suffix == ".zip":
                from zipfile import ZipFile                
                dir_name = __dir__.stem
                with ZipFile(sys.argv[0], "r") as f:
                    f.extractall(dir_name)

            os.chdir(__dir__.with_suffix(""))
            
        """)

        def py_quote(str):
            return str.replace("'''", "\\'\\'\\'")

        for element in self._platform._soc_platform.pack_bitstream_fatbitstream(build_name, build_products):
            if isinstance(element, str):
                main_script += f"system('''{py_quote(element)}''')\n"
            else:
                self.__iadd__(element)
        main_script += "\n".join(f"system('''{py_quote(cmd)}''')" for cmd in self._init_commands) + "\n"
        main_script += dedent("""
            if '--run' in sys.argv:
                system('/usr/bin/env python3 pydriver.py')
        """)

        with ZipFile(file, 'w', ZIP_DEFLATED) as f:
            f.writestr("__main__.py", main_script)
            for name, contents in self._files.items():
                f.writestr(name, contents)
