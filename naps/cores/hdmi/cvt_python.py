# this code is a translation of the original cvt.c from http://www.uruk.org/~erich/projects/cvt/cvt.c

# cvt.c  Generate mode timings using the CVT 1.1 Timing Standard
#  gcc cvt.c -O2 -o cvt -lm -Wall
#  November 2005:
# CVT revision 1.1 changes made by Erich Boleyn <erich@uruk.org>
# CVT is the VESA followon after GTF including new mode capabilities.
#  The CVT EXCEL(TM) SPREADSHEET, a sample (and the definitive)
# implementation of the CVT Timing Standard, is available at:
#  http://www.vesa.org/Public/CVT/CVTd6r1.xls
#  The GTF EXCEL(TM) SPREADSHEET can now be found at:
#  http://www.vesa.org/Public/GTF/GTF_V1R1.xls
#   Notes:
#   -- Didn't egregiously rewrite the program from scratch.
#   -- This is a different program than "gtf" because the CVT
#       timings are a bit different, and have some extra
#       features therein.
#   -- When producing interlaced modes, don't use non-intuitive
#       "full frame" frequency as the Vertical Frequency.  The more
#       intuitive definition is how often vertical retrace occurs.
#   Originally created from "gtf" written by Andy Ritger at NVidia.
# Original block comment at the beginning of the program follows:
# */
#
#/* gtf.c  Generate mode timings using the GTF Timing Standard
#  gcc gtf.c -o gtf -lm -Wall
#  Copyright (c) 2001, Andy Ritger  aritger@nvidia.com
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# o Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# o Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer
#   in the documentation and/or other materials provided with the
#   distribution.
# o Neither the name of NVIDIA nor the names of its contributors
#   may be used to endorse or promote products derived from this
#   software without specific prior written permission.
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
# THE REGENTS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
#  This program is based on the Generalized Timing Formula(GTF TM)
# Standard Version: 1.0, Revision: 1.0
#  The GTF Document contains the following Copyright information:
#  Copyright (c) 1994, 1995, 1996 - Video Electronics Standards
# Association. Duplication of this document within VESA member
# companies for review purposes is permitted. All other rights
# reserved.
#  While every precaution has been taken in the preparation
# of this standard, the Video Electronics Standards Association and
# its contributors assume no responsibility for errors or omissions,
# and make no warranties, expressed or implied, of functionality
# of suitability for any purpose. The sample code contained within
# this standard may be used without restriction.
#
#  The GTF EXCEL(TM) SPREADSHEET, a sample (and the definitive)
# implementation of the GTF Timing Standard, is available at:
#  ftp://ftp.vesa.org/pub/GTF/GTF_V1R1.xls
#    This program takes a desired resolution and vertical refresh rate,
# and computes mode timings according to the GTF Timing Standard.
# These mode timings can then be formatted as an XFree86 modeline
# or a mode description for use by fbset(8).
#    NOTES:
#  The GTF allows for computation of "margins" (the visible border
# surrounding the addressable video); on most non-overscan type
# systems, the margin period is zero.  I've implemented the margin
# computations but not enabled it because 1) I don't really have
# any experience with this, and 2) neither XFree86 modelines nor
# fbset fb.modes provide an obvious way for margin timings to be
# included in their mode descriptions (needs more investigation).
#
# The GTF provides for computation of interlaced mode timings;
# I've implemented the computations but not enabled them, yet.
# I should probably enable and test this at some point.
#
#  TODO:
#  o Add support for interlaced modes.
#  o Implement the other portions of the GTF: compute mode timings
#   given either the desired pixel clock or the desired horizontal
#   frequency.
#  o It would be nice if this were more general purpose to do things
#   outside the scope of the GTF: like generate double scan mode
#   timings, for example.
#
# o Printing digits to the right of the decimal point when the
#   digits are 0 annoys me.
#  o Error checking.

import math

CLOCK_STEP = 0.25  # Clock steps in MHz
MARGIN_PERCENT = 1.8  # % of active vertical image
H_SYNC_PER = 8.0  # sync % of horizontal image
CELL_GRAN = 8.4999  # assumed character cell granularity
CELL_GRAN_RND = 8.0  # assumed character cell granularity (round)
MIN_V_BPORCH = 3.0  # width of vsync in lines
MIN_V_PORCH_RND = 3.0  # width of vsync in lines
M = 600.0  # blanking formula gradient
C = 40.0  # blanking formula offset
K = 128.0  # blanking formula scaling factor
J = 20.0  # blanking formula scaling factor

# Standard Timing Parameters 
MIN_VSYNC_BP = 550.0  # min time of vsync + back porch (us)
H_SYNC_PERCENT = 8.0  # width of hsync as % of total line

# Reduced Blanking defines 
RB_MIN_V_BPORCH = 6.0  # lines
RB_V_FPORCH = 3.0  # lines
RB_MIN_V_BLANK = 460.0  # us
RB_H_SYNC = 32.0  # pixels
RB_H_BLANK = 160.0  # pixels

# C' and M' are part of the Blanking Duty Cycle computation 

C_PRIME = (((C - J) * K / 256.0) + J)
M_PRIME = (K / 256.0 * M)


#
#  - print the result of the named computation; this is
# useful when comparing against the CVT EXCEL spreadsheet.
#

#
# print_fb_mode() - print a mode description in fbset(8) format
# see the fb.modes(8) manpage.  The timing description used in
# this is rather odd; they use "left and right margin" to refer
# to the portion of the hblank before and after the sync pulse
# by conceptually wrapping the portion of the blank after the pulse
# to infront of the visible region; ie:
#
# Timing description I'm accustomed to:
# <--------1--------> <--2--> <--3--> <--4-->
# _________
# |-------------------|_______|       |_______
# R       SS      SE     FL
#
# 1: visible image
# 2: blank before sync (aka front porch)
# 3: sync pulse
# 4: blank after sync (aka back porch)
# R: Resolution
# SS: Sync Start
# SE: Sync End
# FL: Frame Length
# But the fb.modes format is:
# <--4--> <--------1--------> <--2--> <--3-->
# _________
# _______|-------------------|_______|       |
#
# The fb.modes(8) manpage refers to <4> and <2> as the left and
# right "margin" (as well as upper and lower margin in the vertical
# direction) -- note that this has nothing to do with the term
# "margin" used in the CVT Timing Standard.
# XXX always prints the 32 bit mode -- should I provide a command
# line option to specify the bpp?  It's simple enough for a user
# to edit the mode description after it's generated.
# 

#
# vert_refresh() - as defined by the CVT Timing Standard, compute the
# Stage 1 Parameters using the vertical refresh frequency.  In other
# words: input a desired resolution and desired refresh rate, and
# output the CVT mode timings.
# XXX margin computations are implemented but not tested (nor used by
# XFree86 of fbset mode descriptions, from what I can tell).


__all__ = ["generate_modeline"]


def generate_modeline(width, height, refresh, reduced_blanking=True):
    if (refresh % 60) != 0:
        reduced_blanking = False  # only possible for multiples of 60 Hz

    margins = 0
    interlaced = False

    #  1. Required Field Rate
    #       This is slightly different from the spreadsheet because we use
    #       a different result for interlaced video modes.  Simplifies this
    #       to the input field rate.
    #       [V FIELD RATE RQD] = [I/P FREQ RQD]
    #

    v_field_rate_rqd = refresh

    #  2. Horizontal Pixels
    #       In order to give correct results, the number of horizontal
    #       pixels requested is first processed to ensure that it is divisible
    #       by the character size, by rounding it to the nearest character
    #       cell boundary.
    #       [H PIXELS RND] = ((ROUNDDOWN([H PIXELS]/[CELL GRAN RND],0))
    #       *[CELLGRAN RND])
    #

    h_pixels_rnd = math.floor(width / CELL_GRAN_RND) * CELL_GRAN_RND

    #  2.5th Calculation, aspect_ratio & v_sync_rnd
    #       [ASPECT_RATIO] = IF(H_PIXELS_RND = CELL_GRAN_RND*ROUND((V_LINES*
    #       4.0/3.0)/CELL_GRAN_RND),"4:3")
    #       etc...
    #       [V_SYNC] = [value from table based on aspect ratio]
    #       [V_SYNC_RND] = ROUND(V_SYNC,0)  // Not needed in principle
    #

    if h_pixels_rnd == CELL_GRAN_RND * math.floor((height * 4.0 / 3.0) / CELL_GRAN_RND):
        aspect_ratio = "4:3"
        v_sync = 4
    elif h_pixels_rnd == CELL_GRAN_RND * math.floor((height * 16.0 / 9.0) / CELL_GRAN_RND):
        aspect_ratio = "16:9"
        v_sync = 5
    elif h_pixels_rnd == CELL_GRAN_RND * math.floor((height * 16.0 / 10.0) / CELL_GRAN_RND):
        aspect_ratio = "16:10"
        v_sync = 6
    elif h_pixels_rnd == CELL_GRAN_RND * math.floor((height * 5.0 / 4.0) / CELL_GRAN_RND):
        aspect_ratio = "5:4"
        v_sync = 7
    elif h_pixels_rnd == CELL_GRAN_RND * math.floor((height * 15.0 / 9.0) / CELL_GRAN_RND):
        aspect_ratio = "15:9"
        v_sync = 7
    else:
        # Default case of unknown aspect ratio
        aspect_ratio = "Custom"
        v_sync = 10

    v_sync_rnd = v_sync

    #
    # 3. Determine Left & Right Borders
    # Calculate the margins on the left and right side.
    # [LEFT MARGIN (PIXELS)] = (IF( [MARGINS RQD?]="Y",
    # (ROUNDDOWN( ([H PIXELS RND] * [MARGIN%] / 100 /
    # [CELL GRAN RND]),0)) * [CELL GRAN RND],
    # 0))
    # [RIGHT MARGIN (PIXELS)] = (IF( [MARGINS RQD?]="Y",
    # (ROUNDDOWN( ([H PIXELS RND] * [MARGIN%] / 100 /
    # [CELL GRAN RND]),0)) * [CELL GRAN RND],
    # 0))
    # 

    left_margin = math.floor(h_pixels_rnd * MARGIN_PERCENT / 100.0 / CELL_GRAN_RND) * CELL_GRAN_RND if margins else 0.0
    right_margin = left_margin

    #  4. Find total active pixels.
    #       Find total number of active pixels in image and left and right
    #       margins.
    #       [TOTAL ACTIVE PIXELS] = [H PIXELS RND] + [LEFT MARGIN (PIXELS)] +
    #       [RIGHT MARGIN (PIXELS)]
    #

    total_active_pixels = h_pixels_rnd + left_margin + right_margin

    #  5. Find number of lines per field.
    #       If interlace is requested, the number of vertical lines assumed
    #       by the calculation must be halved, as the computation calculates
    #       the number of vertical lines per field. In either case, the
    #       number of lines is rounded to the nearest integer.
    #
    #       [V LINES RND] = IF([INT RQD?]="y", ROUNDDOWN([V LINES]/2,0),
    #       ROUNDDOWN([V LINES],0))
    #

    v_lines_rnd = math.floor(height / 2.0) if interlaced else math.floor(height)

    #  6. Find Top and Bottom margins.
    #       [TOP MARGIN (LINES)] = IF([MARGINS RQD?]="Y",
    #       ROUNDDOWN(([MARGIN%]/100*[V LINES RND]),0),
    #       0)
    #       [BOT MARGIN (LINES)] = IF([MARGINS RQD?]="Y",
    #       ROUNDDOWN(([MARGIN%]/100*[V LINES RND]),0),
    #       0)
    #

    top_margin = math.floor(MARGIN_PERCENT / 100.0 * v_lines_rnd) if margins else (0.0)
    bot_margin = top_margin

    #  7. If interlace is required, then set variable [INTERLACE]=0.5:
    #       [INTERLACE]=(IF([INT RQD?]="y",0.5,0))
    #

    interlace = 0.5 if interlaced else 0.0

    # Here it diverges for "reduced blanking" or normal blanking modes.
    # 

    if reduced_blanking:
        h_blank = RB_H_BLANK

        #  8. Estimate Horiz. Period (us).
        #	   [H PERIOD EST] = ((1000000/V_FIELD_RATE_RQD)-RB_MIN_V_BLANK)/(V_LINES_RND+TOP_MARGIN+BOT_MARGIN)
        #

        h_period_est = (1000000.0 / v_field_rate_rqd - RB_MIN_V_BLANK) / (v_lines_rnd + top_margin + bot_margin)

        #  9. Find number of lines in vertical blanking.
        #	   [Actual VBI_LINES] = RB_MIN_V_BLANK/H_PERIOD_EST
        #	   [VBI_LINES] = ROUNDDOWN(RB_MIN_V_BLANK/H_PERIOD_EST,0) + 1
        #

        vbi_lines = RB_MIN_V_BLANK / h_period_est

        vbi_lines = math.floor(vbi_lines) + 1.0

        #  10. Check Vertical Blanking is sufficient.
        #	   [RB MIN VBI] = RB_V_FPORCH+V_SYNC_RND+RB_MIN_V_BPORCH
        #	   [ACT VBI LINES] = IF(VBI_LINES<RB_MIN_VBI,RB_MIN_VBI,VBI_LINES)
        #

        rb_min_vbi = RB_V_FPORCH + v_sync_rnd + RB_MIN_V_BPORCH
        act_vbi_lines = rb_min_vbi if (vbi_lines < rb_min_vbi) else vbi_lines

        #  11. Find total number of lines in vertical field.
        #	   [TOTAL V LINES] = ACT_VBI_LINES+V_LINES_RND+TOP_MARGIN+BOT_MARGIN+INTERLACE
        #

        total_v_lines = act_vbi_lines + v_lines_rnd + top_margin + bot_margin + interlace

        #  12. Find total number of pixels in a line (pixels).
        #	   [TOTAL PIXELS] = RB_H_BLANK+TOTAL_ACTIVE_PIXELS
        #

        total_pixels = total_active_pixels + RB_H_BLANK

        #  13. Find Pixel Clock Frequency (MHz).
        #	   [Non-rounded PIXEL_FREQ] = V_FIELD_RATE_RQD*TOTAL_V_LINES*TOTAL_PIXELS/1000000
        #	   [ACT PIXEL FREQ] = CLOCK_STEP * ROUND((V_FIELD_RATE_RQD*TOTAL_V_LINES*TOTAL_PIXELS/1000000)/CLOCK_STEP,0)
        #

        act_pixel_freq = v_field_rate_rqd * total_v_lines * total_pixels / 1000000.0

        act_pixel_freq = CLOCK_STEP * math.floor(act_pixel_freq / CLOCK_STEP)

        stage = 14

    else:  # Normal Blanking

        #  8. Estimate Horiz. Period (us).
        #	   [H PERIOD EST] = ((1/V_FIELD_RATE_RQD)-MIN_VSYNC_BP/1000000)/(V_LINES_RND+(2*TOP_MARGIN)+MIN_V_PORCH_RND+INTERLACE)*1000000
        #

        h_period_est = ((1 / v_field_rate_rqd) - MIN_VSYNC_BP / 1000000.0) / (
                v_lines_rnd + (2 * top_margin) + MIN_V_PORCH_RND + interlace) * 1000000.0

        #  9. Find number of lines in (SYNC + BACK PORCH).
        #	   [Estimated V_SYNC_BP] = ROUNDDOWN((MIN_VSYNC_BP/H_PERIOD_EST),0)+1
        #	   [Actual V_SYNC_BP] = MIN_VSYNC_BP/H_PERIOD_EST
        #	   [V_SYNC_BP] = IF(Estimated V_SYNC_BP<(V_SYNC+MIN_V_BPORCH),
        #	   V_SYNC+MIN_V_BPORCH,Estimated V_SYNC_BP)
        #

        v_sync_bp = MIN_VSYNC_BP / h_period_est

        v_sync_bp = math.floor(v_sync_bp) + 1

        v_sync_bp = v_sync + MIN_V_BPORCH if (v_sync_bp < v_sync + MIN_V_BPORCH) else v_sync_bp

        #  10. Find number of lines in back porch (Lines).
        #	   [Back porch] = V_SYNC_BP - V_SYNC_RND
        #

        #  11. Find total number of lines in vertical field.
        #	   [TOTAL V LINES] = V_LINES_RND+TOP_MARGIN+BOT_MARGIN
        #	   +V_SYNC_BP+INTERLACE+MIN_V_PORCH_RND
        #

        total_v_lines = v_lines_rnd + top_margin + bot_margin + v_sync_bp + interlace + MIN_V_PORCH_RND

        #  12. Find ideal blanking duty cycle from formula (%):
        #	   [IDEAL DUTY CYCLE] = C_PRIME-(M_PRIME*H_PERIOD_EST/1000)
        #

        ideal_duty_cycle = C_PRIME - (M_PRIME * h_period_est / 1000.0)

        #  13. Find blanking time to nearest cell (Pixels).
        #	   [H BLANK] = IF(IDEAL_DUTY_CYCLE<20,(ROUNDDOWN((TOTAL_ACTIVE_PIXELS*20/(100-20)/(2*CELL_GRAN_RND)),0))*(2*CELL_GRAN_RND),(ROUNDDOWN((TOTAL_ACTIVE_PIXELS*IDEAL_DUTY_CYCLE/(100-IDEAL_DUTY_CYCLE)/(2*CELL_GRAN_RND)),0))*(2*CELL_GRAN_RND))
        #

        cur_duty_cycle = 20.0 if (ideal_duty_cycle < 20.0) else ideal_duty_cycle
        h_blank = math.floor(
            (total_active_pixels * cur_duty_cycle / (100.0 - cur_duty_cycle) / (2.0 * CELL_GRAN_RND))) * (
                          2.0 * CELL_GRAN_RND)

        #  14. Find total number of pixels in a line (Pixels).
        #	   [TOTAL PIXELS] = TOTAL_ACTIVE_PIXELS + H_BLANK
        #

        total_pixels = total_active_pixels + h_blank

        #  15. Find pixel clock frequency (MHz).
        #	   [Non-rounded PIXEL FREQ] = TOTAL_PIXELS / H_PERIOD_EST
        #	   [ACT PIXEL FREQ] = CLOCK_STEP * ROUNDDOWN(
        #

        act_pixel_freq = total_pixels / h_period_est

        act_pixel_freq = CLOCK_STEP * math.floor(act_pixel_freq / CLOCK_STEP)

        stage = 16

    #  14/16. Find actual horizontal frequency (kHz)
    #       [ACT H FREQ] = 1000*ACT_PIXEL_FREQ/TOTAL_PIXELS
    #

    act_h_freq = 1000 * act_pixel_freq / total_pixels

    stage += 1

    #  15/17. Find actual field rate (Hz)
    #       [ACT FIELD RATE] = 1000*ACT_H_FREQ/TOTAL_V_LINES
    #

    act_field_rate = 1000 * act_h_freq / total_v_lines

    stage += 1

    #  16/18. Find actual vertical frame frequency (Hz)
    #       [ACT FRAME RATE] = IF(INT_RQD?=Y,ACT_FIELD_RATE/2,ACT_FIELD_RATE)
    #

    act_frame_rate = (act_field_rate / 2) if interlace else act_field_rate

    #
    # Extra computations not numbered in the CVT spreadsheet.
    # 

    #  20. Find Horizontal Back Porch.
    #       [H BACK PORCH] = H_BLANK/2
    #

    h_back_porch = h_blank / 2

    #  21. Find Horizontal Front Porch.
    #       [H SYNC RND] = IF(RED_BLANK_RQD?="Y",RB_H_SYNC,(ROUNDDOWN((H_SYNC_PER/100*TOTAL_PIXELS/CELL_GRAN_RND),0))*CELL_GRAN_RND)
    #

    if reduced_blanking:
        h_sync_rnd = RB_H_SYNC
    else:
        h_sync_rnd = math.floor(H_SYNC_PER / 100.0 * total_pixels / CELL_GRAN_RND) * CELL_GRAN_RND

    #  22. Find Horizontal Front Porch.
    #       [H FRONT PORCH] = H_BLANK - H_BACK_PORCH - H_SYNC_RND
    #

    h_front_porch = h_blank - h_back_porch - h_sync_rnd

    #  23. Find Vertical Front Porch.
    #       [V FRONT PORCH] = IF(RED_BLANK_RQD?="y",RB_V_FPORCH,MIN_V_PORCH_RND)
    #

    v_front_porch = RB_V_FPORCH if reduced_blanking else MIN_V_PORCH_RND

    return "Modeline \"{:d}x{:d}_{:.2f}{}{}\"  {:.2f}" "  {:d} {:d} {:d} {:d}" "  {:d} {:d} {:d} {:d}" "  {}{}HSync {}Vsync".format(
        int(h_pixels_rnd),
        int(height),
        refresh,
        "i" if interlaced else "",
        "R" if reduced_blanking else "",

        act_pixel_freq,

        int(h_pixels_rnd),
        int(h_pixels_rnd + h_front_porch),
        int(h_pixels_rnd + h_front_porch + h_sync_rnd),
        int(total_pixels),

        int(height),
        int(height + v_front_porch),
        int(height + v_front_porch + v_sync_rnd),
        int(total_v_lines - v_lines_rnd + height),

        "Interlace  " if interlaced else "",
        "+" if reduced_blanking else "-",
        "-" if reduced_blanking else "+",
    )
