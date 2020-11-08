import subprocess

CVT_BIN = "cvt"


def generate_modeline(width, height, refresh, reduced_blanking=True):
    if (refresh % 60) != 0:
        reduced_blanking = False  # only possible for multiples of 60 Hz

    cvt_bin = ([CVT_BIN] + ["-r"]) if reduced_blanking else [CVT_BIN]
    out, _ = subprocess.Popen(cvt_bin + [str(width), str(height), str(refresh)],
                              stdout=subprocess.PIPE).communicate()
    return out.split(b"\n")[1].decode("utf-8")
