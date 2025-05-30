from enum import Enum

from amaranth import *

from naps import StatusSignal, SocPlatform

__all__ = ["fsm_status_reg"]


def fsm_status_reg(platform, m, fsm):
    if isinstance(platform, SocPlatform):
        fsm_state = StatusSignal(name=f"{fsm.state.name}_reg")  # TODO: use meaningful shape value here (needs deferring)
        def signal_fixup_hook(platform, top_fragment: Fragment):
            fsm_state.width = fsm.state.width
            fsm_state.decoder = fsm.state.decoder
        platform.prepare_hooks.insert(0, signal_fixup_hook)
        m.d.comb += fsm_state.eq(fsm.state)
