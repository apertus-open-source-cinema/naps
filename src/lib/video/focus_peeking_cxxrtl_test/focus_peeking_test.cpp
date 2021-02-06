#include <backends/cxxrtl/cxxrtl.h>

#if defined(CXXRTL_INCLUDE_CAPI_IMPL) || \
    defined(CXXRTL_INCLUDE_VCD_CAPI_IMPL)
#include <backends/cxxrtl/cxxrtl_capi.cc>
#endif

#if defined(CXXRTL_INCLUDE_VCD_CAPI_IMPL)
#include <backends/cxxrtl/cxxrtl_vcd_capi.cc>
#endif

using namespace cxxrtl_yosys;

namespace cxxrtl_design {

// \nmigen.hierarchy: top
// \top: 1
// \generator: nMigen
struct p_top : public module {
	// \hdlname: video_transformer memory_r_data
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:53
	wire<24> p_video__transformer_2e_memory__r__data;
	// \hdlname: video_transformer memory_r_data$17
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:53
	wire<24> p_video__transformer_2e_memory__r__data_24_17;
	// \init: 0
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:65
	wire<24> i_flatten_5c_video__transformer_2e__24_like {0u};
	// \init: 0
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:65
	wire<24> i_flatten_5c_video__transformer_2e__24_like_24_20 {0u};
	// \init: 0
	// \hdlname: video_transformer input_x
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:14
	wire<9> p_video__transformer_2e_input__x {0u};
	// \init: 0
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:65
	wire<24> i_flatten_5c_video__transformer_2e__24_like_24_41 {0u};
	// \init: 0
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:65
	wire<24> i_flatten_5c_video__transformer_2e__24_like_24_44 {0u};
	// \init: 0
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:65
	wire<24> i_flatten_5c_video__transformer_2e__24_like_24_65 {0u};
	// \init: 0
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:65
	wire<24> i_flatten_5c_video__transformer_2e__24_like_24_68 {0u};
	// \init: 0
	// \hdlname: video_transformer input_y
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:15
	wire<9> p_video__transformer_2e_input__y {0u};
	// \init: 0
	// \hdlname: video_transformer output_x
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:17
	wire<9> p_video__transformer_2e_output__x {0u};
	// \init: 0
	// \hdlname: video_transformer output_y
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:18
	wire<9> p_video__transformer_2e_output__y {0u};
	// \init: 0
	// \hdlname: video_transformer delayed_cycles
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:29
	wire<10> p_video__transformer_2e_delayed__cycles {0u};
	// \src: /data/projects/nmigen/nmigen/hdl/ir.py:526
	/*input*/ value<1> p_rst;
	// \src: /data/projects/nmigen/nmigen/hdl/ir.py:526
	/*input*/ value<1> p_clk;
	value<1> prev_p_clk;
	bool posedge_p_clk() const {
		return !prev_p_clk.slice<0>().val() && p_clk.slice<0>().val();
	}
	// \src: /data/projects/ngateware/src/lib/video/focus_peeking.py:24
	/*input*/ value<8> p_highlight__b;
	// \src: /data/projects/ngateware/src/lib/video/focus_peeking.py:23
	/*input*/ value<8> p_highlight__g;
	// \src: /data/projects/ngateware/src/lib/video/focus_peeking.py:22
	/*input*/ value<8> p_highlight__r;
	// \src: /data/projects/ngateware/src/lib/video/focus_peeking.py:21
	/*input*/ value<16> p_threshold;
	// \src: /data/projects/ngateware/src/lib/bus/stream/stream.py:29
	/*input*/ value<1> p_output____ready;
	// \src: /data/projects/ngateware/src/lib/video/image_stream.py:15
	/*output*/ value<1> p_output____frame__last;
	// \src: /data/projects/ngateware/src/lib/video/image_stream.py:14
	/*output*/ value<1> p_output____line__last;
	// \src: /data/projects/ngateware/src/lib/bus/stream/stream.py:51
	/*output*/ value<24> p_output____payload;
	// \src: /data/projects/ngateware/src/lib/bus/stream/stream.py:30
	/*output*/ value<1> p_output____valid;
	// \src: /data/projects/ngateware/src/lib/bus/stream/stream.py:29
	/*output*/ value<1> p_in__stream____ready;
	// \src: /data/projects/ngateware/src/lib/video/image_stream.py:15
	/*input*/ value<1> p_in__stream____frame__last;
	// \src: /data/projects/ngateware/src/lib/video/image_stream.py:14
	/*input*/ value<1> p_in__stream____line__last;
	// \src: /data/projects/ngateware/src/lib/bus/stream/stream.py:51
	/*input*/ value<24> p_in__stream____payload;
	// \src: /data/projects/ngateware/src/lib/bus/stream/stream.py:30
	/*input*/ value<1> p_in__stream____valid;

	// \hdlname: video_transformer memory
	memory<24> memory_p_video__transformer_2e_memory { 512u,
		memory<24>::init<512> { 0, {
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
		}},
	};
	// \hdlname: video_transformer memory$10
	memory<24> memory_p_video__transformer_2e_memory_24_10 { 512u,
		memory<24>::init<512> { 0, {
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
			value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u}, value<24>{0x000000u},
		}},
	};

	p_top() {}
	p_top(adopt, p_top other) {}

	void reset() override {
		*this = p_top(adopt {}, std::move(*this));
	}

	bool eval() override;
	bool commit() override;
	void debug_info(debug_items &items, std::string path = "") override;
}; // struct p_top

bool p_top::eval() {
	bool converged = true;
	bool posedge_p_clk = this->posedge_p_clk();
	value<10> i_procmux_24_94__Y;
	value<9> i_procmux_24_80__Y;
	value<9> i_procmux_24_65__Y;
	value<9> i_procmux_24_58__Y;
	value<9> i_procmux_24_48__Y;
	value<24> i_procmux_24_41__Y;
	value<24> i_procmux_24_37__Y;
	value<24> i_procmux_24_24__Y;
	value<24> i_procmux_24_20__Y;
	value<24> i_procmux_24_7__Y;
	value<24> i_procmux_24_3__Y;
	// \hdlname: video_transformer output_payload__r
	// \src: /data/projects/ngateware/src/lib/data_structure/packed_struct.py:33
	value<8> p_video__transformer_2e_output__payload____r;
	// \hdlname: video_transformer output_payload__g
	// \src: /data/projects/ngateware/src/lib/data_structure/packed_struct.py:33
	value<8> p_video__transformer_2e_output__payload____g;
	// \hdlname: video_transformer output_payload__b
	// \src: /data/projects/ngateware/src/lib/data_structure/packed_struct.py:33
	value<8> p_video__transformer_2e_output__payload____b;
	// \hdlname: video_transformer video_transformer_output__valid
	// \src: /data/projects/ngateware/src/lib/bus/stream/stream.py:30
	value<1> p_video__transformer_2e_video__transformer__output____valid;
	// \hdlname: video_transformer video_transformer_output__payload
	// \src: /data/projects/ngateware/src/lib/bus/stream/stream.py:51
	value<24> p_video__transformer_2e_video__transformer__output____payload;
	// \hdlname: video_transformer video_transformer_output__line_last
	// \src: /data/projects/ngateware/src/lib/video/image_stream.py:14
	value<1> p_video__transformer_2e_video__transformer__output____line__last;
	// \hdlname: video_transformer video_transformer_output__frame_last
	// \src: /data/projects/ngateware/src/lib/video/image_stream.py:15
	value<1> p_video__transformer_2e_video__transformer__output____frame__last;
	// \hdlname: video_transformer video_transformer_output__ready
	// \src: /data/projects/ngateware/src/lib/bus/stream/stream.py:29
	value<1> p_video__transformer_2e_video__transformer__output____ready;
	// \hdlname: video_transformer in_stream__ready
	// \src: /data/projects/ngateware/src/lib/bus/stream/stream.py:29
	value<1> p_video__transformer_2e_in__stream____ready;
	// \hdlname: video_transformer in_stream__valid
	// \src: /data/projects/ngateware/src/lib/bus/stream/stream.py:30
	value<1> p_video__transformer_2e_in__stream____valid;
	// \hdlname: video_transformer in_stream__payload
	// \src: /data/projects/ngateware/src/lib/bus/stream/stream.py:51
	value<24> p_video__transformer_2e_in__stream____payload;
	// \hdlname: video_transformer in_stream__line_last
	// \src: /data/projects/ngateware/src/lib/video/image_stream.py:14
	value<1> p_video__transformer_2e_in__stream____line__last;
	// \hdlname: video_transformer rst
	// \src: /data/projects/nmigen/nmigen/hdl/ir.py:526
	value<1> p_video__transformer_2e_rst;
	// \hdlname: video_transformer clk
	// \src: /data/projects/nmigen/nmigen/hdl/ir.py:526
	value<1> p_video__transformer_2e_clk;
	// \hdlname: video_transformer memory_w_en
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:47
	value<1> p_video__transformer_2e_memory__w__en;
	// \hdlname: video_transformer memory_w_en$12
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:47
	value<1> p_video__transformer_2e_memory__w__en_24_12;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:65
	value<24> i_flatten_5c_video__transformer_2e__24_like_24_next;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:65
	value<24> i_flatten_5c_video__transformer_2e__24_like_24_20_24_next;
	// \hdlname: video_transformer input_x$next
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:14
	value<9> p_video__transformer_2e_input__x_24_next;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:60
	value<24> i_flatten_5c_video__transformer_2e__24_like_24_40;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:65
	value<24> i_flatten_5c_video__transformer_2e__24_like_24_41_24_next;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:65
	value<24> i_flatten_5c_video__transformer_2e__24_like_24_44_24_next;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:60
	value<24> i_flatten_5c_video__transformer_2e__24_like_24_64;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:65
	value<24> i_flatten_5c_video__transformer_2e__24_like_24_65_24_next;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:65
	value<24> i_flatten_5c_video__transformer_2e__24_like_24_68_24_next;
	// \hdlname: video_transformer input_y$next
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:15
	value<9> p_video__transformer_2e_input__y_24_next;
	// \hdlname: video_transformer output_x$next
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:17
	value<9> p_video__transformer_2e_output__x_24_next;
	// \hdlname: video_transformer output_y$next
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:18
	value<9> p_video__transformer_2e_output__y_24_next;
	// \hdlname: video_transformer delayed_cycles$next
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:29
	value<10> p_video__transformer_2e_delayed__cycles_24_next;
	// \src: /data/projects/ngateware/src/lib/video/focus_peeking.py:42
	value<1> i_279;
	// \src: /data/projects/ngateware/src/lib/video/image_stream.py:15
	value<1> p_video__transformer__video__transformer__output____frame__last;
	// \src: /data/projects/ngateware/src/lib/video/image_stream.py:14
	value<1> p_video__transformer__video__transformer__output____line__last;
	// \src: /data/projects/ngateware/src/lib/bus/stream/stream.py:51
	value<24> p_video__transformer__video__transformer__output____payload;
	// \src: /data/projects/ngateware/src/lib/bus/stream/stream.py:30
	value<1> p_video__transformer__video__transformer__output____valid;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:142
	value<24> p_video__transformer___24_signal_24_8;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:142
	value<24> p_video__transformer___24_signal_24_7;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:142
	value<24> p_video__transformer___24_signal_24_6;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:142
	value<24> p_video__transformer___24_signal_24_5;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:142
	value<24> p_video__transformer___24_signal_24_4;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:142
	value<24> p_video__transformer___24_signal_24_3;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:142
	value<24> p_video__transformer___24_signal_24_2;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:142
	value<24> p_video__transformer___24_signal_24_1;
	// \src: /data/projects/ngateware/src/lib/video/video_transformer.py:142
	value<24> p_video__transformer___24_signal;
	// \src: /data/projects/ngateware/src/lib/data_structure/packed_struct.py:33
	value<8> p_video__transformer__output__payload____b;
	// \src: /data/projects/ngateware/src/lib/data_structure/packed_struct.py:33
	value<8> p_video__transformer__output__payload____g;
	// \src: /data/projects/ngateware/src/lib/data_structure/packed_struct.py:33
	value<8> p_video__transformer__output__payload____r;
	// connection
	p_video__transformer___24_signal_24_1 = i_flatten_5c_video__transformer_2e__24_like_24_68.curr;
	// connection
	p_video__transformer___24_signal = i_flatten_5c_video__transformer_2e__24_like_24_41.curr;
	// connection
	p_video__transformer___24_signal_24_2 = i_flatten_5c_video__transformer_2e__24_like_24_44.curr;
	// connection
	p_video__transformer___24_signal_24_3 = i_flatten_5c_video__transformer_2e__24_like_24_20.curr;
	// connection
	p_video__transformer___24_signal_24_4 = i_flatten_5c_video__transformer_2e__24_like_24_65.curr;
	// connection
	p_video__transformer___24_signal_24_5 = i_flatten_5c_video__transformer_2e__24_like.curr;
	// connection
	i_flatten_5c_video__transformer_2e__24_like_24_64 = p_video__transformer_2e_memory__r__data_24_17.curr;
	// connection
	p_video__transformer___24_signal_24_6 = i_flatten_5c_video__transformer_2e__24_like_24_64;
	// connection
	i_flatten_5c_video__transformer_2e__24_like_24_40 = p_video__transformer_2e_memory__r__data.curr;
	// connection
	p_video__transformer___24_signal_24_7 = i_flatten_5c_video__transformer_2e__24_like_24_40;
	// connection
	p_video__transformer_2e_video__transformer__output____ready = p_output____ready;
	// connection
	p_video__transformer___24_signal_24_8 = p_in__stream____payload;
	// connection
	p_video__transformer_2e_in__stream____valid = p_in__stream____valid;
	// connection
	p_video__transformer_2e_in__stream____ready = (lt_uu<1>(p_video__transformer_2e_delayed__cycles.curr, value<10>{0x201u}) ? value<1>{0x1u} : (gt_uu<1>(p_video__transformer_2e_delayed__cycles.curr, value<10>{0x201u}) ? value<1>{0u} : p_video__transformer_2e_video__transformer__output____ready));
	// connection
	p_video__transformer_2e_video__transformer__output____valid = (lt_uu<1>(p_video__transformer_2e_delayed__cycles.curr, value<10>{0x201u}) ? value<1>{0u} : (gt_uu<1>(p_video__transformer_2e_delayed__cycles.curr, value<10>{0x201u}) ? value<1>{0x1u} : p_video__transformer_2e_in__stream____valid));
	// connection
	p_video__transformer_2e_in__stream____line__last = p_in__stream____line__last;
	// cells $278 $276 $275 $270 $272 $268 $266 $265 $260 $262 $258 $256 $255 $250 $252 $248 $246 $245 $240 $242 $238 $236 $235 $230 $232 $228 $226 $225 $220 $222 $218 $216 $215 $210 $212 $208 $206 $205 $200 $202 $198 $196 $195 $190 $192 $188 $186 $185 $180 $182 $178 $176 $175 $170 $172 $168 $166 $165 $160 $162 $158 $156 $155 $150 $152 $148 $146 $145 $140 $142 $138 $136 $135 $130 $132 $128 $126 $125 $120 $122 $118 $116 $115 $110 $112 $108 $106 $105 $100 $102 $98 $96 $95 $90 $92 $88 $86 $85 $80 $82 $78 $76 $75 $70 $72 $68 $66 $65 $60 $62 $58 $56 $55 $50 $52 $48 $46 $45 $40 $42 $38 $36 $35 $30 $32 $28 $26 $25 $20 $22 $18 $16 $15 $10 $12
	i_279 = gt_uu<1>(add_uu<36>(add_uu<35>(add_uu<34>(add_uu<33>(add_uu<32>(add_uu<31>(add_uu<30>(add_uu<29>(add_uu<28>(add_uu<27>(add_uu<26>(add_uu<25>(add_uu<24>(add_uu<23>(add_uu<22>(add_uu<21>(add_uu<20>(add_uu<19>(add_uu<18>(add_uu<17>(add_uu<16>(add_uu<15>(add_uu<14>(add_uu<13>(add_uu<12>(add_uu<11>(add_uu<10>(value<1>{0u}, (gt_uu<1>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_1.slice<7,0>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_1.slice<7,0>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_1.slice<7,0>().val(), p_video__transformer___24_signal.slice<7,0>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_1.slice<15,8>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_1.slice<15,8>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_1.slice<15,8>().val(), p_video__transformer___24_signal.slice<15,8>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_1.slice<23,16>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_1.slice<23,16>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_1.slice<23,16>().val(), p_video__transformer___24_signal.slice<23,16>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_2.slice<7,0>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_2.slice<7,0>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_2.slice<7,0>().val(), p_video__transformer___24_signal.slice<7,0>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_2.slice<15,8>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_2.slice<15,8>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_2.slice<15,8>().val(), p_video__transformer___24_signal.slice<15,8>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_2.slice<23,16>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_2.slice<23,16>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_2.slice<23,16>().val(), p_video__transformer___24_signal.slice<23,16>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_3.slice<7,0>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_3.slice<7,0>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_3.slice<7,0>().val(), p_video__transformer___24_signal.slice<7,0>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_3.slice<15,8>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_3.slice<15,8>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_3.slice<15,8>().val(), p_video__transformer___24_signal.slice<15,8>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_3.slice<23,16>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_3.slice<23,16>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_3.slice<23,16>().val(), p_video__transformer___24_signal.slice<23,16>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_4.slice<7,0>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_4.slice<7,0>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_4.slice<7,0>().val(), p_video__transformer___24_signal.slice<7,0>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_4.slice<15,8>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_4.slice<15,8>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_4.slice<15,8>().val(), p_video__transformer___24_signal.slice<15,8>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_4.slice<23,16>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_4.slice<23,16>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_4.slice<23,16>().val(), p_video__transformer___24_signal.slice<23,16>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal.slice<7,0>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal.slice<7,0>().val()) : sub_uu<9>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal.slice<7,0>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal.slice<15,8>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal.slice<15,8>().val()) : sub_uu<9>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal.slice<15,8>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal.slice<23,16>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal.slice<23,16>().val()) : sub_uu<9>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal.slice<23,16>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_5.slice<7,0>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_5.slice<7,0>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_5.slice<7,0>().val(), p_video__transformer___24_signal.slice<7,0>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_5.slice<15,8>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_5.slice<15,8>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_5.slice<15,8>().val(), p_video__transformer___24_signal.slice<15,8>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_5.slice<23,16>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_5.slice<23,16>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_5.slice<23,16>().val(), p_video__transformer___24_signal.slice<23,16>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_6.slice<7,0>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_6.slice<7,0>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_6.slice<7,0>().val(), p_video__transformer___24_signal.slice<7,0>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_6.slice<15,8>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_6.slice<15,8>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_6.slice<15,8>().val(), p_video__transformer___24_signal.slice<15,8>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_6.slice<23,16>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_6.slice<23,16>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_6.slice<23,16>().val(), p_video__transformer___24_signal.slice<23,16>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_7.slice<7,0>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_7.slice<7,0>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_7.slice<7,0>().val(), p_video__transformer___24_signal.slice<7,0>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_7.slice<15,8>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_7.slice<15,8>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_7.slice<15,8>().val(), p_video__transformer___24_signal.slice<15,8>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_7.slice<23,16>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_7.slice<23,16>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_7.slice<23,16>().val(), p_video__transformer___24_signal.slice<23,16>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_8.slice<7,0>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<7,0>().val(), p_video__transformer___24_signal_24_8.slice<7,0>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_8.slice<7,0>().val(), p_video__transformer___24_signal.slice<7,0>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_8.slice<15,8>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<15,8>().val(), p_video__transformer___24_signal_24_8.slice<15,8>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_8.slice<15,8>().val(), p_video__transformer___24_signal.slice<15,8>().val()))), (gt_uu<1>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_8.slice<23,16>().val()) ? sub_uu<9>(p_video__transformer___24_signal.slice<23,16>().val(), p_video__transformer___24_signal_24_8.slice<23,16>().val()) : sub_uu<9>(p_video__transformer___24_signal_24_8.slice<23,16>().val(), p_video__transformer___24_signal.slice<23,16>().val()))), p_threshold);
	// connection
	p_video__transformer_2e_in__stream____payload = p_in__stream____payload;
	// connection
	p_video__transformer_2e_rst = p_rst;
	// connection
	p_video__transformer__output__payload____b = (i_279 ? p_highlight__b : p_video__transformer___24_signal.slice<23,16>().val());
	// connection
	p_video__transformer__output__payload____g = (i_279 ? p_highlight__g : p_video__transformer___24_signal.slice<15,8>().val());
	// connection
	p_video__transformer__output__payload____r = (i_279 ? p_highlight__r : p_video__transformer___24_signal.slice<7,0>().val());
	// connection
	p_video__transformer_2e_clk = p_clk;
	// connection
	p_video__transformer_2e_memory__w__en_24_12 = (and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? value<1>{0x1u} : value<1>{0u});
	// connection
	p_video__transformer_2e_memory__w__en = (and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? value<1>{0x1u} : value<1>{0u});
	// cells $procmux$1 $flatten\video_transformer.$19
	i_procmux_24_3__Y = (p_video__transformer_2e_rst ? value<24>{0u} : (and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? p_video__transformer_2e_in__stream____payload : i_flatten_5c_video__transformer_2e__24_like.curr));
	// cells $procmux$5 $flatten\video_transformer.$22
	i_procmux_24_7__Y = (p_video__transformer_2e_rst ? value<24>{0u} : (and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? i_flatten_5c_video__transformer_2e__24_like.curr : i_flatten_5c_video__transformer_2e__24_like_24_20.curr));
	// cells $procmux$18 $flatten\video_transformer.$43
	i_procmux_24_20__Y = (p_video__transformer_2e_rst ? value<24>{0u} : (and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? i_flatten_5c_video__transformer_2e__24_like_24_40 : i_flatten_5c_video__transformer_2e__24_like_24_41.curr));
	// cells $procmux$22 $flatten\video_transformer.$46
	i_procmux_24_24__Y = (p_video__transformer_2e_rst ? value<24>{0u} : (and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? i_flatten_5c_video__transformer_2e__24_like_24_41.curr : i_flatten_5c_video__transformer_2e__24_like_24_44.curr));
	// cells $procmux$35 $flatten\video_transformer.$67
	i_procmux_24_37__Y = (p_video__transformer_2e_rst ? value<24>{0u} : (and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? i_flatten_5c_video__transformer_2e__24_like_24_64 : i_flatten_5c_video__transformer_2e__24_like_24_65.curr));
	// cells $procmux$39 $flatten\video_transformer.$70
	i_procmux_24_41__Y = (p_video__transformer_2e_rst ? value<24>{0u} : (and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? i_flatten_5c_video__transformer_2e__24_like_24_65.curr : i_flatten_5c_video__transformer_2e__24_like_24_68.curr));
	// cells $procmux$46 $flatten\video_transformer.$72 $procmux$44 $flatten\video_transformer.$74 $flatten\video_transformer.$77
	i_procmux_24_48__Y = (p_video__transformer_2e_rst ? value<9>{0u} : (and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? (not_u<1>(p_video__transformer_2e_in__stream____line__last) ? add_uu<10>(p_video__transformer_2e_input__x.curr, value<1>{0x1u}).slice<8,0>().val() : value<9>{0u}) : p_video__transformer_2e_input__x.curr));
	// cells $procmux$56 $flatten\video_transformer.$79 $procmux$54 $flatten\video_transformer.$81 $procmux$51 $flatten\video_transformer.$83 $flatten\video_transformer.$86
	i_procmux_24_58__Y = (p_video__transformer_2e_rst ? value<9>{0u} : (and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? (not_u<1>(p_video__transformer_2e_in__stream____line__last) ? p_video__transformer_2e_input__y.curr : (not_u<1>(p_in__stream____frame__last) ? add_uu<10>(p_video__transformer_2e_input__y.curr, value<1>{0x1u}).slice<8,0>().val() : value<9>{0u})) : p_video__transformer_2e_input__y.curr));
	// cells $procmux$63 $flatten\video_transformer.$88 $procmux$61 $flatten\video_transformer.$90 $flatten\video_transformer.$93
	i_procmux_24_65__Y = (p_video__transformer_2e_rst ? value<9>{0u} : (and_uu<1>(p_video__transformer_2e_video__transformer__output____ready, p_video__transformer_2e_video__transformer__output____valid) ? (lt_uu<1>(p_video__transformer_2e_output__x.curr, value<9>{0x1ffu}) ? add_uu<10>(p_video__transformer_2e_output__x.curr, value<1>{0x1u}).slice<8,0>().val() : value<9>{0u}) : p_video__transformer_2e_output__x.curr));
	// cells $procmux$78 $flatten\video_transformer.$99 $procmux$76 $flatten\video_transformer.$101 $procmux$73 $flatten\video_transformer.$103 $flatten\video_transformer.$106
	i_procmux_24_80__Y = (p_video__transformer_2e_rst ? value<9>{0u} : (and_uu<1>(p_video__transformer_2e_video__transformer__output____ready, p_video__transformer_2e_video__transformer__output____valid) ? (lt_uu<1>(p_video__transformer_2e_output__x.curr, value<9>{0x1ffu}) ? p_video__transformer_2e_output__y.curr : (lt_uu<1>(p_video__transformer_2e_output__y.curr, value<9>{0x1ffu}) ? add_uu<10>(p_video__transformer_2e_output__y.curr, value<1>{0x1u}).slice<8,0>().val() : value<9>{0u})) : p_video__transformer_2e_output__y.curr));
	// cells $procmux$92 $flatten\video_transformer.$120 $flatten\video_transformer.$118 $flatten\video_transformer.$117 $flatten\video_transformer.$114 $flatten\video_transformer.$131 $procmux$90 $flatten\video_transformer.$128 $flatten\video_transformer.$126 $flatten\video_transformer.$124 $flatten\video_transformer.$123 $flatten\video_transformer.$134
	i_procmux_24_94__Y = (p_video__transformer_2e_rst ? value<10>{0u} : (and_uu<1>(and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid), not_u<1>(and_uu<1>(p_video__transformer_2e_video__transformer__output____ready, p_video__transformer_2e_video__transformer__output____valid))) ? add_uu<11>(p_video__transformer_2e_delayed__cycles.curr, value<1>{0x1u}).slice<9,0>().val() : (and_uu<1>(not_u<1>(and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid)), and_uu<1>(p_video__transformer_2e_video__transformer__output____ready, p_video__transformer_2e_video__transformer__output____valid)) ? sub_uu<11>(p_video__transformer_2e_delayed__cycles.curr, value<1>{0x1u}).slice<9,0>().val() : p_video__transformer_2e_delayed__cycles.curr)));
	// connection
	p_video__transformer_2e_video__transformer__output____payload = p_video__transformer__output__payload____b.concat(p_video__transformer__output__payload____g).concat(p_video__transformer__output__payload____r).val();
	// connection
	p_video__transformer_2e_video__transformer__output____line__last = (and_uu<1>(p_video__transformer_2e_video__transformer__output____ready, p_video__transformer_2e_video__transformer__output____valid) ? (lt_uu<1>(p_video__transformer_2e_output__x.curr, value<9>{0x1ffu}) ? value<1>{0u} : value<1>{0x1u}) : value<1>{0u});
	// connection
	p_video__transformer_2e_video__transformer__output____frame__last = (and_uu<1>(p_video__transformer_2e_video__transformer__output____ready, p_video__transformer_2e_video__transformer__output____valid) ? (lt_uu<1>(p_video__transformer_2e_output__x.curr, value<9>{0x1ffu}) ? value<1>{0u} : (lt_uu<1>(p_video__transformer_2e_output__y.curr, value<9>{0x1ffu}) ? value<1>{0u} : value<1>{0x1u})) : value<1>{0u});
	// \hdlname: video_transformer U$$3
	// cell \video_transformer.U$$3
	if (posedge_p_clk) {
		auto tmp_0 = memory_index((and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? (eq_uu<1>(value<10>{0x200u}, value<1>{0u}) ? value<10>{0u} : mod_uu<10>(add_uu<10>(p_video__transformer_2e_input__x.curr, value<1>{0x1u}), value<10>{0x200u})).slice<8,0>().val() : p_video__transformer_2e_input__x.curr), 0, 512);
		if (value<1>{0x1u}) {
			CXXRTL_ASSERT(tmp_0.valid && "out of bounds read");
			if(tmp_0.valid) {
				value<24> tmp_1 = memory_p_video__transformer_2e_memory_24_10[tmp_0.index];
				p_video__transformer_2e_memory__r__data_24_17.next = tmp_1;
			} else {
				p_video__transformer_2e_memory__r__data_24_17.next = value<24> {};
			}
		}
	}
	// \hdlname: video_transformer U$$2
	// cell \video_transformer.U$$2
	if (posedge_p_clk) {
		auto tmp_2 = memory_index((and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? p_video__transformer_2e_input__x.curr : value<9>{0u}), 0, 512);
		CXXRTL_ASSERT(tmp_2.valid && "out of bounds write");
		if (tmp_2.valid) {
			memory_p_video__transformer_2e_memory_24_10.update(tmp_2.index, (and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? i_flatten_5c_video__transformer_2e__24_like_24_40 : value<24>{0u}), p_video__transformer_2e_memory__w__en_24_12.concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).concat(p_video__transformer_2e_memory__w__en_24_12).val(), 0);
		}
	}
	// \hdlname: video_transformer U$$1
	// cell \video_transformer.U$$1
	if (posedge_p_clk) {
		auto tmp_3 = memory_index((and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? (eq_uu<1>(value<10>{0x200u}, value<1>{0u}) ? value<10>{0u} : mod_uu<10>(add_uu<10>(p_video__transformer_2e_input__x.curr, value<1>{0x1u}), value<10>{0x200u})).slice<8,0>().val() : p_video__transformer_2e_input__x.curr), 0, 512);
		if (value<1>{0x1u}) {
			CXXRTL_ASSERT(tmp_3.valid && "out of bounds read");
			if(tmp_3.valid) {
				value<24> tmp_4 = memory_p_video__transformer_2e_memory[tmp_3.index];
				p_video__transformer_2e_memory__r__data.next = tmp_4;
			} else {
				p_video__transformer_2e_memory__r__data.next = value<24> {};
			}
		}
	}
	// \hdlname: video_transformer U$$0
	// cell \video_transformer.U$$0
	if (posedge_p_clk) {
		auto tmp_5 = memory_index((and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? p_video__transformer_2e_input__x.curr : value<9>{0u}), 0, 512);
		CXXRTL_ASSERT(tmp_5.valid && "out of bounds write");
		if (tmp_5.valid) {
			memory_p_video__transformer_2e_memory.update(tmp_5.index, (and_uu<1>(p_video__transformer_2e_in__stream____ready, p_video__transformer_2e_in__stream____valid) ? p_video__transformer_2e_in__stream____payload : value<24>{0u}), p_video__transformer_2e_memory__w__en.concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).concat(p_video__transformer_2e_memory__w__en).val(), 0);
		}
	}
	// cell $procdff$112
	if (posedge_p_clk) {
		i_flatten_5c_video__transformer_2e__24_like.next = i_procmux_24_3__Y;
	}
	// cell $procdff$113
	if (posedge_p_clk) {
		i_flatten_5c_video__transformer_2e__24_like_24_20.next = i_procmux_24_7__Y;
	}
	// cell $procdff$114
	if (posedge_p_clk) {
		i_flatten_5c_video__transformer_2e__24_like_24_41.next = i_procmux_24_20__Y;
	}
	// cell $procdff$115
	if (posedge_p_clk) {
		i_flatten_5c_video__transformer_2e__24_like_24_44.next = i_procmux_24_24__Y;
	}
	// cell $procdff$116
	if (posedge_p_clk) {
		i_flatten_5c_video__transformer_2e__24_like_24_65.next = i_procmux_24_37__Y;
	}
	// cell $procdff$117
	if (posedge_p_clk) {
		i_flatten_5c_video__transformer_2e__24_like_24_68.next = i_procmux_24_41__Y;
	}
	// cell $procdff$118
	if (posedge_p_clk) {
		p_video__transformer_2e_input__x.next = i_procmux_24_48__Y;
	}
	// cell $procdff$119
	if (posedge_p_clk) {
		p_video__transformer_2e_input__y.next = i_procmux_24_58__Y;
	}
	// cell $procdff$120
	if (posedge_p_clk) {
		p_video__transformer_2e_output__x.next = i_procmux_24_65__Y;
	}
	// cell $procdff$121
	if (posedge_p_clk) {
		p_video__transformer_2e_output__y.next = i_procmux_24_80__Y;
	}
	// cell $procdff$122
	if (posedge_p_clk) {
		p_video__transformer_2e_delayed__cycles.next = i_procmux_24_94__Y;
	}
	// connection
	p_video__transformer_2e_delayed__cycles_24_next = i_procmux_24_94__Y;
	// connection
	p_video__transformer_2e_output__y_24_next = i_procmux_24_80__Y;
	// connection
	p_video__transformer_2e_output__x_24_next = i_procmux_24_65__Y;
	// connection
	p_video__transformer_2e_input__y_24_next = i_procmux_24_58__Y;
	// connection
	p_video__transformer_2e_input__x_24_next = i_procmux_24_48__Y;
	// connection
	i_flatten_5c_video__transformer_2e__24_like_24_68_24_next = i_procmux_24_41__Y;
	// connection
	i_flatten_5c_video__transformer_2e__24_like_24_65_24_next = i_procmux_24_37__Y;
	// connection
	i_flatten_5c_video__transformer_2e__24_like_24_44_24_next = i_procmux_24_24__Y;
	// connection
	i_flatten_5c_video__transformer_2e__24_like_24_41_24_next = i_procmux_24_20__Y;
	// connection
	i_flatten_5c_video__transformer_2e__24_like_24_20_24_next = i_procmux_24_7__Y;
	// connection
	i_flatten_5c_video__transformer_2e__24_like_24_next = i_procmux_24_3__Y;
	// connection
	p_output____valid = p_video__transformer_2e_video__transformer__output____valid;
	// connection
	p_output____payload = p_video__transformer_2e_video__transformer__output____payload;
	// connection
	p_output____line__last = p_video__transformer_2e_video__transformer__output____line__last;
	// connection
	p_output____frame__last = p_video__transformer_2e_video__transformer__output____frame__last;
	// connection
	p_video__transformer_2e_output__payload____r = p_video__transformer__output__payload____r;
	// connection
	p_video__transformer_2e_output__payload____g = p_video__transformer__output__payload____g;
	// connection
	p_video__transformer_2e_output__payload____b = p_video__transformer__output__payload____b;
	// connection
	p_video__transformer__video__transformer__output____valid = p_video__transformer_2e_video__transformer__output____valid;
	// connection
	p_video__transformer__video__transformer__output____payload = p_video__transformer_2e_video__transformer__output____payload;
	// connection
	p_video__transformer__video__transformer__output____line__last = p_video__transformer_2e_video__transformer__output____line__last;
	// connection
	p_video__transformer__video__transformer__output____frame__last = p_video__transformer_2e_video__transformer__output____frame__last;
	// connection
	p_in__stream____ready = p_video__transformer_2e_in__stream____ready;
	return converged;
}

bool p_top::commit() {
	bool changed = false;
	changed |= p_video__transformer_2e_memory__r__data.commit();
	changed |= p_video__transformer_2e_memory__r__data_24_17.commit();
	changed |= i_flatten_5c_video__transformer_2e__24_like.commit();
	changed |= i_flatten_5c_video__transformer_2e__24_like_24_20.commit();
	changed |= p_video__transformer_2e_input__x.commit();
	changed |= i_flatten_5c_video__transformer_2e__24_like_24_41.commit();
	changed |= i_flatten_5c_video__transformer_2e__24_like_24_44.commit();
	changed |= i_flatten_5c_video__transformer_2e__24_like_24_65.commit();
	changed |= i_flatten_5c_video__transformer_2e__24_like_24_68.commit();
	changed |= p_video__transformer_2e_input__y.commit();
	changed |= p_video__transformer_2e_output__x.commit();
	changed |= p_video__transformer_2e_output__y.commit();
	changed |= p_video__transformer_2e_delayed__cycles.commit();
	prev_p_clk = p_clk;
	changed |= memory_p_video__transformer_2e_memory.commit();
	changed |= memory_p_video__transformer_2e_memory_24_10.commit();
	return changed;
}

void p_top::debug_info(debug_items &items, std::string path) {
	assert(path.empty() || path[path.size() - 1] == ' ');
	static const value<1> const_p_video__transformer_2e_memory__r__en = value<1>{0x1u};
	items.add(path + "video_transformer memory_r_en", debug_item(const_p_video__transformer_2e_memory__r__en, 0));
	items.add(path + "video_transformer memory_r_data", debug_item(p_video__transformer_2e_memory__r__data, 0, debug_item::DRIVEN_SYNC));
	static const value<1> const_p_video__transformer_2e_memory__r__en_24_15 = value<1>{0x1u};
	items.add(path + "video_transformer memory_r_en$15", debug_item(const_p_video__transformer_2e_memory__r__en_24_15, 0));
	items.add(path + "video_transformer memory_r_data$17", debug_item(p_video__transformer_2e_memory__r__data_24_17, 0, debug_item::DRIVEN_SYNC));
	items.add(path + "video_transformer input_x", debug_item(p_video__transformer_2e_input__x, 0, debug_item::DRIVEN_SYNC));
	items.add(path + "video_transformer input_y", debug_item(p_video__transformer_2e_input__y, 0, debug_item::DRIVEN_SYNC));
	items.add(path + "video_transformer output_x", debug_item(p_video__transformer_2e_output__x, 0, debug_item::DRIVEN_SYNC));
	items.add(path + "video_transformer output_y", debug_item(p_video__transformer_2e_output__y, 0, debug_item::DRIVEN_SYNC));
	items.add(path + "video_transformer delayed_cycles", debug_item(p_video__transformer_2e_delayed__cycles, 0, debug_item::DRIVEN_SYNC));
	items.add(path + "video_transformer_$signal$7", debug_item(debug_alias(), p_video__transformer_2e_memory__r__data, 0));
	items.add(path + "video_transformer_$signal$6", debug_item(debug_alias(), p_video__transformer_2e_memory__r__data_24_17, 0));
	items.add(path + "video_transformer_$signal$5", debug_item(debug_alias(), i_flatten_5c_video__transformer_2e__24_like, 0));
	items.add(path + "video_transformer_$signal$4", debug_item(debug_alias(), i_flatten_5c_video__transformer_2e__24_like_24_65, 0));
	items.add(path + "video_transformer_$signal$3", debug_item(debug_alias(), i_flatten_5c_video__transformer_2e__24_like_24_20, 0));
	items.add(path + "video_transformer_$signal$2", debug_item(debug_alias(), i_flatten_5c_video__transformer_2e__24_like_24_44, 0));
	items.add(path + "video_transformer_$signal$1", debug_item(debug_alias(), i_flatten_5c_video__transformer_2e__24_like_24_68, 0));
	items.add(path + "video_transformer_$signal", debug_item(debug_alias(), i_flatten_5c_video__transformer_2e__24_like_24_41, 0));
	items.add(path + "rst", debug_item(p_rst, 0, debug_item::INPUT|debug_item::UNDRIVEN));
	items.add(path + "clk", debug_item(p_clk, 0, debug_item::INPUT|debug_item::UNDRIVEN));
	items.add(path + "highlight_b", debug_item(p_highlight__b, 0, debug_item::INPUT|debug_item::UNDRIVEN));
	items.add(path + "highlight_g", debug_item(p_highlight__g, 0, debug_item::INPUT|debug_item::UNDRIVEN));
	items.add(path + "highlight_r", debug_item(p_highlight__r, 0, debug_item::INPUT|debug_item::UNDRIVEN));
	items.add(path + "threshold", debug_item(p_threshold, 0, debug_item::INPUT|debug_item::UNDRIVEN));
	items.add(path + "output__ready", debug_item(p_output____ready, 0, debug_item::INPUT|debug_item::UNDRIVEN));
	items.add(path + "output__frame_last", debug_item(p_output____frame__last, 0, debug_item::OUTPUT|debug_item::DRIVEN_COMB));
	items.add(path + "output__line_last", debug_item(p_output____line__last, 0, debug_item::OUTPUT|debug_item::DRIVEN_COMB));
	items.add(path + "output__payload", debug_item(p_output____payload, 0, debug_item::OUTPUT|debug_item::DRIVEN_COMB));
	items.add(path + "output__valid", debug_item(p_output____valid, 0, debug_item::OUTPUT|debug_item::DRIVEN_COMB));
	items.add(path + "in_stream__ready", debug_item(p_in__stream____ready, 0, debug_item::OUTPUT|debug_item::DRIVEN_COMB));
	items.add(path + "in_stream__frame_last", debug_item(p_in__stream____frame__last, 0, debug_item::INPUT|debug_item::UNDRIVEN));
	items.add(path + "in_stream__line_last", debug_item(p_in__stream____line__last, 0, debug_item::INPUT|debug_item::UNDRIVEN));
	items.add(path + "in_stream__payload", debug_item(p_in__stream____payload, 0, debug_item::INPUT|debug_item::UNDRIVEN));
	items.add(path + "in_stream__valid", debug_item(p_in__stream____valid, 0, debug_item::INPUT|debug_item::UNDRIVEN));
	items.add(path + "video_transformer memory", debug_item(memory_p_video__transformer_2e_memory, 0));
	items.add(path + "video_transformer memory$10", debug_item(memory_p_video__transformer_2e_memory_24_10, 0));
}

} // namespace cxxrtl_design

extern "C"
cxxrtl_toplevel cxxrtl_design_create() {
	return new _cxxrtl_toplevel { std::unique_ptr<cxxrtl_design::p_top>(new cxxrtl_design::p_top) };
}
