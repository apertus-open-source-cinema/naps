if __name__ == "__main__":
    import os, atexit, code, readline, rlcompleter
    readline.parse_and_bind("tab: complete")

    class HistoryConsole(code.InteractiveConsole):
        def __init__(self, locals=None, filename="<console>",
                     histfile=os.path.expanduser("~/.pydriver-history")):
            code.InteractiveConsole.__init__(self, locals, filename)
            self.init_history(histfile)

        def init_history(self, histfile):
            readline.parse_and_bind("tab: complete")
            if hasattr(readline, "read_history_file"):
                try:
                    readline.read_history_file(histfile)
                except FileNotFoundError:
                    pass
                atexit.register(self.save_history, histfile)

        def save_history(self, histfile):
            readline.set_history_length(1000)
            readline.write_history_file(histfile)

    shell = HistoryConsole(locals())

    # setup the design variable
    design = Design(MemoryAccessor())

    print("welcome to the python shell to interact with the fpga")
    print("interact with it over the `design` variable and tab completion")
    shell.interact(banner="")
