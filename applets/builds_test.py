import re
import subprocess
import unittest
from glob import glob
from os.path import dirname
from typing import Tuple


class TestBuilds(unittest.TestCase):
    pass

process_handles: list[Tuple[str, subprocess.Popen]] = []
for file in glob("{}/*.py".format(dirname(__file__))):
    if "builds_test" in file:  # we are not executing ourselves
        continue
    process_handles.append((file, subprocess.Popen(['python', file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)))

for file, p in process_handles:
    stdout, stderr = p.communicate()
    usage = stderr.decode("utf-8")
    try:
        devices = re.search("-d\\W*{(.*?)}", usage).group(1).split(",")
        socs = re.search("-s\\W*{(.*?)}", usage).group(1).split(",")
    except Exception as e:
        print(e)
        print(file, usage)
        raise e

    for device in devices:
        for soc in socs:
            def make_test_builds(file, device):
                soc_local = str(soc)

                def test_builds(self):
                    command = ['python', file, '-e', '-d', device, '-s', soc_local]
                    print("running '{}'".format(' '.join(command)))
                    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                    stdout, stderr = process.communicate()
                    print(stdout.decode("utf-8"))
                    print(stderr.decode("utf-8"))

                    self.assertEqual(0, process.returncode)

                return test_builds


            filename_stripped = file.split("/")[-1].replace(".py", "")
            setattr(TestBuilds, "test_{}_{}_{}".format(filename_stripped, device, soc), make_test_builds(file, device))
