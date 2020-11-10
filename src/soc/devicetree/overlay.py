# utility functions for generating and loading devicetree overlays
from textwrap import dedent, indent

from nmigen import Fragment

from soc.fatbitstream import FatbitstreamContext


def devicetree_overlay(platform, overlay_name, overlay_content, placeholder_substitutions_dict=None):
    if placeholder_substitutions_dict is None:
        placeholder_substitutions_dict = {}

    if not hasattr(platform, "used_devicetree_names"):
        platform.used_devicetree_names = set()
    assert overlay_name not in platform.used_devicetree_names
    platform.used_devicetree_names.add(overlay_name)

    def overlay_hook(platform, top_fragment: Fragment, sames):
        assert hasattr(top_fragment, "memorymap")
        memorymap = top_fragment.memorymap

        things_to_replace = {k: v if isinstance(v, str) else "0x{:x}".format(memorymap.find_recursive(v).address) for k, v in
                             placeholder_substitutions_dict.items()}
        things_to_replace["overlay_name"] = overlay_name

        formatted_overlay_text = dedent(overlay_content)
        for name, replacement in things_to_replace.items():
            formatted_overlay_text = formatted_overlay_text.replace("%{}%".format(name), replacement)

        overlay_text = dedent("""
            /dts-v1/;
            /plugin/;
    
            / {
                fragment@0 {
                    target = <&amba>;
                    
                    __overlay__ {
                        %s
                    };
                };
            };
        """ % indent(formatted_overlay_text, "                        "))
        print(overlay_text)

        fc = FatbitstreamContext.get(platform)
        fc.self_extracting_blobs["{}_overlay.dts".format(overlay_name)] = overlay_text
        fc.init_commands.append("mkdir -p /sys/kernel/config/device-tree/overlays/{}\n".format(overlay_name))
        fc.init_commands.append(
            "dtc -O dtb -@ {0}_overlay.dts -o - > /sys/kernel/config/device-tree/overlays/{0}/dtbo\n\n"
                .format(overlay_name)
        )

    platform.prepare_hooks.append(overlay_hook)
    return overlay_name
