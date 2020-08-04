from textwrap import dedent

from nmigen import *

import os
import subprocess

from nmigen.back import cxxrtl

from cores.hdmi.cvt import generate_modeline
from cores.hdmi.hdmi import Hdmi
from soc.zynq import ZynqSocPlatform
from util.bundle import Bundle
from util.sim import SimPlatform

if __name__ == '__main__':
    m = Module()


    class FakeHdmiPlugin(Bundle):
        clock = Signal()
        data_r = Signal()
        data_g = Signal()
        data_b = Signal()


    fake_hdmi_plugin = FakeHdmiPlugin(name='fake_hdmi_plugin')
    hdmi = m.submodules.hdmi = Hdmi(plugin=fake_hdmi_plugin, modeline=generate_modeline(1920, 1080, 60), generate_clocks=False)

    rgb = hdmi.pattern_generator.out
    r = Signal(8)
    m.d.comb += r.eq(rgb.r)
    g = Signal(8)
    m.d.comb += g.eq(rgb.g)
    b = Signal(8)
    m.d.comb += b.eq(rgb.b)

    platform = ZynqSocPlatform(SimPlatform())
    output = cxxrtl.convert(platform.prepare(m), platform=platform)

    root = os.path.join("../build")
    filename = os.path.join(root, "top.cpp")
    elfname = os.path.join(root, "top.elf")

    with open(filename, "w") as f:
        f.write(output)
        f.write(dedent(r"""
            #include <iostream>
            #include <fstream>
            #include "SDL2/SDL.h"
            int main()
            {
                const int width = 1280;
                const int height = 720;
                const int bpp = 3;
                static uint8_t pixels[width * height * bpp];
                int frames = 0;
                unsigned int lastTime = 0;
                unsigned int currentTime;
                // Set this to 0 to disable vsync
                unsigned int flags = SDL_RENDERER_PRESENTVSYNC;
                if(SDL_Init(SDL_INIT_VIDEO) != 0) {
                    fprintf(stderr, "Could not init SDL: %s\n", SDL_GetError());
                    return 1;
                }
                SDL_Window *screen = SDL_CreateWindow("cxxrtl",
                        SDL_WINDOWPOS_UNDEFINED,
                        SDL_WINDOWPOS_UNDEFINED,
                        width, height,
                        0);
                if(!screen) {
                    fprintf(stderr, "Could not create window\n");
                    return 1;
                }
                SDL_Renderer *renderer = SDL_CreateRenderer(screen, -1, flags);
                if(!renderer) {
                    fprintf(stderr, "Could not create renderer\n");
                    return 1;
                }
                SDL_Texture* framebuffer = SDL_CreateTexture(renderer, SDL_PIXELFORMAT_RGB24, SDL_TEXTUREACCESS_STREAMING, width, height);
                cxxrtl_design::p_top top;
                for (int i = 0; i < 1000; i++) {
                    size_t ctr = 0;
                    value<1> old_vs{0u};
                    // Render one frame
                    while (true) {
                        //top.step();
                        //top.p_clk = value<1>{0u};
                        // Inofficial cxxrtl hack that improves performance
                        //top.prev_p_clk = value<1>{0u};
                        //top.p_clk = value<1>{1u};
                        top.step();
                        if (top.hdmi.timing_generator.x) {
                            pixels[ctr++] = (uint8_t) top.hdmi.pattern_generator.out.r[0];
                            pixels[ctr++] = (uint8_t) top.p_g.data[0];
                            pixels[ctr++] = (uint8_t) top.p_b.data[0];
                        }
                        // Break when vsync goes low again
                        if (old_vs && !top.p_vga__output____vs)
                            break;
                        old_vs = top.p_vga__output____vs;
                    }
                    SDL_UpdateTexture(framebuffer, NULL, pixels, width * bpp);
                    SDL_RenderCopy(renderer, framebuffer, NULL, NULL);
                    SDL_RenderPresent(renderer);
                    SDL_Event event;
                    if (SDL_PollEvent(&event)) {
                        if (event.type == SDL_KEYDOWN)
                            break;
                    }
                    // SDL_Delay(10);
                    frames++;
                    currentTime = SDL_GetTicks();
                    float delta = currentTime - lastTime;
                    if (delta >= 1000) {
                        std::cout << "FPS: " << (frames / (delta / 1000.0f)) << std::endl;
                        lastTime = currentTime;
                        frames = 0;
                    }
                }
                SDL_DestroyWindow(screen);
                SDL_Quit();
                return 0;
            }
        """))
        f.close()

    print(subprocess.check_call([
        "clang++", "-I", "/usr/share/yosys/include",
        "-O3", "-fno-exceptions", "-std=c++11", "-lSDL2", "-o", elfname, filename]))

    print(subprocess.check_call([elfname]))
