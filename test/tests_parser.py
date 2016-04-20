#!/usr/bin/env python
#
#    This file is part of Scalable COncurrent Operations in Python (SCOOP).
#
#    SCOOP is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of
#    the License, or (at your option) any later version.
#
#    SCOOP is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with SCOOP. If not, see <http://www.gnu.org/licenses/>.
#
import unittest
import os
from itertools import repeat

from scoop import utils

# This is a subset of a SGE environment for testing
SGE_ENV = {'NHOSTS':'2', 'PE_HOSTFILE':"sgehostssim.txt",
'NSLOTS': '16', 'PE': 'default', 'ENVIRONMENT': 'BATCH'}

# This is a subset of a PBS environment for testing
PBS_ENV = {'ENVIRONMENT': 'BATCH', 'PBS_ENVIRONMENT': 'PBS_BATCH',
'MOAB_PROCCOUNT': '16', 'PBS_NUM_NODES': '2', 'PBS_NP': '16', 
'PBS_NODEFILE': 'pbshostssim.txt'} 

# This is the logical content of the hostfiles
hosts = [("host1", 8), ("host2", 4), ("host3", 2), ("host4", 2)]

class TestUtils(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestUtils, self).__init__(*args, **kwargs)

    def setUp(self):
        self.backup = os.environ.copy()

    def tearDown(self):
        os.environ = self.backup

    def test_getCpuCount(self):
        """Since we don't know how many cores has the computer on which these
        tests will be run, we check that at least, getCPUcount() returns an
        int larger than 0."""
        self.assertIsInstance(utils.getCPUcount(), int)
        self.assertTrue(utils.getCPUcount() > 0)

    def test_getEnvPBS(self):
        os.environ.update(PBS_ENV)
        self.assertEqual(utils.getEnv(), "PBS")

    def test_getEnvSGE(self):
        os.environ.update(SGE_ENV)
        self.assertEqual(utils.getEnv(), "SGE")

    def test_getEnvOther(self):
        self.assertEqual(utils.getEnv(), "other")

    def test_getHostsPBS(self):
        os.environ.update(PBS_ENV)
        # We used the set because the order of the hosts is not important.
        self.assertEqual(set(utils.getHosts()), set(hosts))

    def test_getHostsSGE(self):
        os.environ.update(SGE_ENV)
        # We used the set because the order of the hosts is not important.
        self.assertEqual(set(utils.getHosts()), set(hosts))

    def test_getHostsFromSLURM(self):
        pass

    def test_parseSLURM_dashOneDecimal(self):
        hosts = utils.parseSLURM("n[1-4]")
        result = zip(("n{0}".format(x) for x in range(1, 5)), repeat(1))
        self.assertEqual(set(hosts), set(result))

    def test_parseSLURM_dashTwoDecimals(self):
        hosts = utils.parseSLURM("n[5-10]")
        result = zip(("n{0:02d}".format(x) for x in range(5, 11)), repeat(1))
        self.assertEqual(set(hosts), set(result))

    def test_parseSLURM_dashTwonames(self):
        hosts = utils.parseSLURM("x[1-2]y[1-2]")
        result = []
        for num in range(1, 3):
            for prefix in ["x", "y"]:
                result.append(("{prefix}{num}".format(**locals()), 1))
        self.assertEqual(set(hosts), set(result))

    def test_parseSLURM_nondashOneDecimal(self):
        hosts = utils.parseSLURM("n[1,4]")
        result = []
        result = zip(("n{0}".format(x) for x in [1, 4]), repeat(1))
        self.assertEqual(set(hosts), set(result))

    def test_parseSLURM_nondash_and_dashOneDecimal(self):
        hosts = utils.parseSLURM("n[1,5-9]")
        result = []
        result = zip(("n{0}".format(x) for x in [1, 5, 6, 7, 8, 9]), repeat(1))
        self.assertEqual(set(hosts), set(result))
        
    def test_getHostsFile(self):
        self.assertEqual(set(utils.getHosts("hostfilesim.txt")), set(hosts))

    def test_getWorkerQtePBS(self):
        os.environ.update(PBS_ENV)
        self.assertEqual(utils.getWorkerQte(utils.getHosts()), 16)

    def test_getWorkerQteSGE(self):
        os.environ.update(SGE_ENV)
        self.assertEqual(utils.getWorkerQte(utils.getHosts()), 16)

    def test_getWorkerQteFile(self):
        self.assertEqual(utils.getWorkerQte(utils.getHosts("hostfilesim.txt")), 16)


if __name__ == "__main__":
    t = unittest.TestLoader().loadTestsFromTestCase(TestUtils)
    unittest.TextTestRunner(verbosity=2).run(t)
