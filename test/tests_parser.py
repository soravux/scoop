from scoop import utils

import unittest
import os

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
        # Since we don't know how many cores has the computer on which these
        # tests will be run, we check that at least, getCPUcount() returns an
        # int larger than 0.
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
