Project setup & installation
============================

There are two ways of using naps: You can either install it as a normal Python
dependency or develop your project inside the naps source-tree. Developing in-tree
is of advantage if you plan to write large cores that could benefit other projects
and could thus be upstreamed. We currently don't have a very strict definition of 
the scope of things that can live in the naps package and are generally open to
merge other cores / experiments into the codebase.

Upstreaming your projects has the advantage that we catch regressions
when changing internals as none of the interfaces of the naps package currently
provide any stability guarantees. So if the code you write could be useful over a
prologed timespan, consider upstreaming it.

If you however only intend to make a short hack or try something out, it is
better to develop code out-of-tree. This way we can reduce maintainance burden
and limit the growth of the codebase.


Creating a new out-of-tree project
----------------------------------

For creating a new out-of-tree project, we recommend to use `pdm <https://github.com/pdm-project/pdm/>`_.
run::

    pdm new <project-name>
    cd <project-name>
    pdm add naps
    pdm add git+https://github.com/amaranth-lang/amaranth-boards


Creating an new in-tree project
-------------------------------

For creating a new in-tree project, just clone the naps repository::

    git clone https://github.com/apertus-open-source-cinema/naps
    cd naps
    pdm install

We call project entrypoints "applets". If you want
to start a new design, simply create a new python file in the ``applets/``
directory.

Installing the vendor toolchain & tools
---------------------------------------

For using Amaranth (and thus for using naps), you need a working copy of yosys. Because naps also calls 
yosys internally, it is best to install the full version (not amaranth-yowasp). The
easiest way to do that is to install `oss-cad-suite <https://github.com/YosysHQ/oss-cad-suite-build>`__.
If you only want to develop for Lattice ECP5, you are now done.

If you want to develop for Xilinx Zynq, you need Vivado. If amaranth cant find a Vivado installation
naps will download and use a docker container containing Vivado. Note that this container is very large
(>15GB extracted; >5GB download) and downloading it for the first time is very slow.

For using the ``JTAGSoc`` you also need to install openocd. The current platforms
assume that you use a jlink JTAG probe but that can easily be changed (just search for
``jlink`` in the code).
