#include "focus_peeking_test.cpp"
#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"
#include <backends/cxxrtl/cxxrtl_vcd.h>
#include <cassert>
#include <fstream>
#include <ostream>

auto main() -> int {
    cxxrtl_design::p_top top;

    std::ofstream      waves_fd;
    cxxrtl::vcd_writer vcd;
    auto               dump_waves = true;
    if(dump_waves) {
        waves_fd.open("focus_test.vcd");
        cxxrtl::debug_items all_debug_items;
        top.debug_info(all_debug_items);
        vcd.timescale(1, "us");
        vcd.add(all_debug_items);
    }

    int       width, height, channels;
    stbi_uc * image_data = stbi_load("cat512.jpg", &width, &height, &channels, 3);
    assert(("need rgb image", channels == 3));
    assert(("need 512x512 image", width == 512 and height == 512));
    int pixel_position = 0;

    auto data           = new uint8_t[3 * width * height];
    int  write_position = 0;

    top.p_rst.set<bool>(true);
    top.step();
    top.p_clk.set<bool>(true);
    top.step();
    top.p_clk.set<bool>(false);
    top.p_rst.set<bool>(false);
    top.step();

    auto stop = false;


    top.p_threshold.set<uint16_t>(255);
    top.p_highlight__r.set<uint16_t>(255);
    top.p_highlight__g.set<uint16_t>(0);
    top.p_highlight__b.set<uint16_t>(0);

    for(auto cycle = 0; !stop && cycle < 1000000; ++cycle) {
        top.p_clk.set<bool>(false);
        top.step();
        if(dump_waves) vcd.sample(cycle * 2);
        top.p_clk.set<bool>(true);
        top.step();

        top.p_in__stream____line__last.set<bool>(((pixel_position + 1) % width) == 0);
        top.p_in__stream____frame__last.set<bool>((pixel_position + 1) == (width * height));

        value<32> tmp;
        tmp.set<uint32_t>(((image_data[3 * pixel_position + 2] << 16) | (image_data[3 * pixel_position + 1] << 8) |
                           (image_data[3 * pixel_position + 0] << 0)));
        const auto & sub            = tmp.slice<23, 0>();
        top.p_in__stream____payload = sub;
        top.p_in__stream____valid.set<bool>(true);

        if(top.p_in__stream____ready.get<bool>()) { pixel_position++; }

        top.p_output____ready.set<bool>(true);

        if(top.p_output____valid.get<bool>()) {
            data[3 * write_position + 2] = top.p_output____payload.get<uint32_t>() >> 16;
            data[3 * write_position + 1] = top.p_output____payload.get<uint32_t>() >> 8;
            data[3 * write_position + 0] = top.p_output____payload.get<uint32_t>() >> 0;

            write_position++;
            if(top.p_output____frame__last.get<bool>()) {
                stop = true;
                assert(("did not conserve image size", write_position == width * height));
            }
        }

        if(dump_waves) {
            top.step();
            vcd.sample(cycle * 2 + 1);
            waves_fd << vcd.buffer;
            vcd.buffer.clear();
        }
    }

    stbi_write_png("focus_peak_test.png", width, height, 3, data, 3 * width);

    return 0;
}
