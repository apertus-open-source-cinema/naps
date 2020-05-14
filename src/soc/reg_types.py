from nmigen import Signal


class ControlSignal(Signal):
    """ Just a Signal. Indicator, that it is for controlling some parameter (i.e. can be written from the outside)
    Is mapped as a CSR in case the design is build with a SocPlatform.
    """


class StatusSignal(Signal):
    """ Just a Signal. Indicator, that it is for communicating the state to the outside world (i.e. can be read but not written from the outside)
        Is mapped as a CSR in case the design is build with a SocPlatform.
    """