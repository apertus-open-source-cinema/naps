import re
import subprocess
import unittest
from glob import glob
from os.path import dirname


class TestBuilds(unittest.TestCase):
    pass


for file in glob("{}/*.py".format(dirname(__file__))):
    if "test_builds" in file:  # we are not executing ourselves
        continue

    try:
        subprocess.check_output(['python', file], stderr=subprocess.PIPE)
        continue
    except subprocess.CalledProcessError as e:
        usage = e.stderr.decode("utf-8")
    print(file, usage)
    devices = re.search("-d\\W*{(.*)}", usage).group(1).split(",")

    for device in devices:
        def make_test_builds(file, device):
            def test_builds(self):

                process = subprocess.Popen(['python', file, '-e', '-d', device, '-s', 'Zynq'], stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                stdout, stderr = process.communicate()
                print(stdout.decode("utf-8"))
                print(stderr.decode("utf-8"))

                self.assertEqual(0, process.returncode)

            return test_builds


        filename_stripped = file.split("/")[-1].replace(".py", "")
        setattr(TestBuilds, "test_{}_{}".format(filename_stripped, device), make_test_builds(file, device))
