DEVICE ?= micro
include src/devices/$(DEVICE)/config.mk


.PHONY: check
check: build/top.edif build/top.xdc
	@echo -e "\ncheck completed, all good :)"

.PHONY: all
all: build/top.bit


build/verilog.v: $(shell find src/*.py)
	@echo "--- elaborating nMigen design ---"

	mkdir -p $(@D)
	pipenv run python src/top.py generate -tv > $@ || rm $@

build/top.edif: build/verilog.v
	@echo -e "\n--- synthesizing design using yosys ---"

	yosys -l build/yosys_synth.log -p "read_verilog $<; synth_xilinx -top top; hilomap -hicell VCC P -locell GND G; write_edif -nogndvcc $@" -q

build/top.xdc: src/devices/$(DEVICE)/gen_xdc.py
	@echo -e "\n--- generating constraints file ---"

	pipenv run python src/devices/$(DEVICE)/gen_xdc.py > $@ || rm $@

build/top.bit: build/top.edif build/top.xdc
	@echo -e "\n --- PnR using vivado ---"

	echo -e "read_xdc src/top.xdc\n read_edif $<\n link_design -part $(PART_NAME) -top top\n \
	    opt_design\n place_design\n route_design\n report_utilization\n report_timing\n write_bitstream -force $@" \
	    > build/vivado_pnr.tcl
	time vivado -mode batch -source build/vivado_pnr.tcl -log build/vivado_pnr.log -nojournal -tempDir /tmp/ > /dev/null


.PHONY: clean
clean:
	rm -rf build