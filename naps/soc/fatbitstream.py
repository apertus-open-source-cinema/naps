# Utils for generating "fatbitstreams" (files that contain loading-logic, a bitstream, initialization and maybe drivers)
from base64 import b64encode
from datetime import datetime
from shlex import quote

__all__ = ["FatbitstreamContext"]


class FatbitstreamContext:
    platform_to_context_dict = {}

    @classmethod
    def get(cls, platform):
        """
        Implements a singleton-like pattern here to have exactly one FatbitstreamContext per Platform instance
        :rtype: FatbitstreamContext
        """
        if hasattr(platform, "_wrapped_platform"):  # we cant check directly for isinstance SocPlatform here because of cyclic imports
            platform = platform._wrapped_platform

        if platform not in cls.platform_to_context_dict:
            cls.platform_to_context_dict[platform] = FatbitstreamContext(platform, called_by_get_classmethod=True)
        return cls.platform_to_context_dict[platform]

    def __init__(self, platform, called_by_get_classmethod=False):
        assert called_by_get_classmethod
        self.self_extracting_blobs = {}  # a dict of filename -> contents
        self.init_commands = []
        self.pre_init_commands = []
        self._platform = platform

    def generate_fatbitstream_generator(self, build_name):
        """
        Generates shell code that is inserted into the nmigen build file that generates the bash file.
        BEWARE: this has kind of a double indirection because we write bash that generates bash that is then executed.
        Yields the commands that are to be executed during build time.
        """
        builder = _FatbitstreamBuilder()
        builder.append_host("\n")
        builder.append_host("touch {{name}}.fatbitstream.sh")
        builder.append_command("#!/bin/bash\n")
        builder.append_command('"# Fatbitstream for "{}" on platform {} with soc {}. Build on $(date)\n"'.format(
            build_name, self._platform.__class__.__name__, self._platform._soc_platform.__class__.__name__,
            datetime.now().strftime("%d.%b.%Y %H:%M:%S")
        ), do_quote=False)
        builder.append_command("set -euo pipefail\n")

        # we create a directory for all the files we will eventually unpack to allow multiple fatbitstreams
        # to coexist in the same top directory. this is for example important when we want to load a plugin module
        # (with JTAGSoc) in parallel with a Zynq bitstream.
        builder.append_command("mkdir -p '{{name}}.fatbitstream.d'\n")
        builder.append_command("cd '{{name}}.fatbitstream.d'\n")

        builder.append_command("\n\n### driver unpacking ###\n")
        for filename, contents in self.self_extracting_blobs.items():
            builder.append_self_extracting_blob_from_string(contents, filename)

        builder.append_command("\n\n### pre init script ###\n")
        for cmd in self.pre_init_commands:
            builder.append_command(cmd + "\n")

        assert hasattr(self._platform._soc_platform, "pack_bitstream_fatbitstream")
        builder.append_command("\n\n### fpga bitstream loading  ###\n")
        self._platform._soc_platform.pack_bitstream_fatbitstream(builder)

        builder.append_command("\n\n### init script ###\n")
        for cmd in self.init_commands:
            builder.append_command(cmd + "\n")

        builder.append_host("chmod +x {{name}}.fatbitstream.sh")

        return builder.cmds


class _FatbitstreamBuilder:
    def __init__(self):
        self.cmds = []

    def append_host(self, cmd):
        self.cmds.append(cmd)

    def append_command(self, cmd, do_quote=True):
        self.append_host("echo -ne {} >> {{{{name}}}}.fatbitstream.sh".format(quote(cmd.replace("\n", "\\n")) if do_quote else cmd.replace("\n", "\\n")))

    def append_self_extracting_blob_from_string(self, string, path):
        self.append_command("base64 -d > {} <<EOF\n{}\nEOF\n".format(quote(path), b64encode(string.encode("utf-8")).decode("ASCII")))

    def append_self_extracting_blob_from_file(self, src_path, target_path):
        self.append_command(
            '"base64 -d > {} <<EOF\\n$(base64 -w0 {})\\nEOF\\n"'.format(quote(target_path), quote(src_path)),
            do_quote=False
        )
