VIVADO ?= vivado
DEVICE ?= micro
include src/devices/$(DEVICE)/config.mk

.DEFAULT_GOAL := check
.PHONY: check
check: build/top.edif build/top.xdc
	@echo -e "\ncheck completed, all good :)"

.PHONY: all
all: build/top.bit build/top.bin


.DELETE_ON_ERROR:
build/verilog.v: $(shell find src/)
	@echo "--- elaborating nMigen design ---"

	mkdir -p $(@D)
	pipenv run python src/top.py generate -tv > $@

build/top.edif: build/verilog.v
	@echo -e "\n--- synthesizing design using yosys ---"

	yosys -l build/yosys_synth.log -p "read_verilog $<; synth_xilinx -top top; opt; hilomap -hicell VCC P -locell GND G; write_edif -nogndvcc $@" -q

build/top.xdc: src/devices/$(DEVICE)/gen_xdc.py build/verilog.v
	@echo -e "\n--- generating constraints file ---"

	pipenv run python src/devices/$(DEVICE)/gen_xdc.py > $@

build/top.bin: build/top.bit
	pipenv run python src/util/to_raw_bitstream.py -f $< $@

build/top.bit: build/top.edif build/top.xdc
	@echo -e "\n --- PnR using vivado ---"

	echo -e "read_xdc build/top.xdc\n read_edif $<\n link_design -part $(PART_NAME) -top top\n \
	    opt_design\n place_design\n route_design\n report_utilization\n report_timing\n write_bitstream -force $@" \
	    > build/vivado_pnr.tcl
	time $(VIVADO) -mode batch -source build/vivado_pnr.tcl -log build/vivado_pnr.log -nojournal -tempDir /tmp/ > /dev/null


.PHONY: clean
clean:
	rm -rf build
