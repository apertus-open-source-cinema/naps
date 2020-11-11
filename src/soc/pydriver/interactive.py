if __name__ == "__main__":
    import readline
    import rlcompleter
    readline.parse_and_bind("tab: complete")
    import code
    shell = code.InteractiveConsole(locals())

    # setup the design variable
    design = Design(MemoryAccessor())

    print("welcome to the python shell to interact with the fpga")
    print("interact with it over the `design` variable and tab completion")
    shell.interact(banner="")
