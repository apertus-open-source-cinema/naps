import subprocess
import unittest
from glob import glob
from os.path import dirname


class TestBuilds(unittest.TestCase):
    def test_builds(self):
        for file in glob("{}/*.py".format(dirname(__file__))):
            if "test_builds" in file:
                continue
            with self.subTest(file.split("/")[-1]):
                process = subprocess.Popen(['python', file, '-c'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                stdout, stderr = process.communicate()
                print(stdout.decode("utf-8"))
                print(stderr.decode("utf-8"))

                self.assertEqual(0, process.returncode, stderr.decode("utf-8"))

