naps.platform
-------------

The naps.platform package contains board descriptions for various boards.
The board descriptions are plain ``amaranth-boards`` descriptions with sometimes extra functionality.

``JTAGSoc`` requires platform classes to implement the ``generate_jtag_conf`` method 
(an `example can be found here <https://github.com/apertus-open-source-cinema/naps/blob/main/naps/platform/colorlight_5a_75b_7_0.py#L110>`__).

If you have a board that is not supported at the moment, you can create a file that is similiar
to one of the existing ones - possibly also by just inheriting from one of the boards from
`amaranth-boards <https://github.com/amaranth-lang/amaranth-boards>`__.
