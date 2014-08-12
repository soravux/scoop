from scoop._control import _stat
import unittest

class TestStat(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestStat, self).__init__(*args, **kwargs)

    def test_appendleft_with_zero(self):
        stats = _stat()
        data = list(range(0, 5))
        for i in data[::-1]:
            stats.appendleft(i)
        for i, j in enumerate(stats):
            self.assertEqual(data[i], j)

    def test_appendleft(self):
        stats = _stat()
        data = list(range(1, 5))
        for i in data[::-1]:
            stats.appendleft(i)
        for i, j in enumerate(stats):
            self.assertEqual(data[i], j)
     
    def test_maxlen(self):
        stats = _stat()
        data = list(range(1, 15))
        for i in data[::-1]:
            stats.appendleft(i)
        for i, j in enumerate(stats):
            self.assertEqual(data[i], j)
        self.assertEqual(len(stats), 10)

    def test_mean(self):
        stats = _stat()
        data = list(range(1, 11))
        for i in data:
            stats.appendleft(float(i))
        self.assertAlmostEqual(stats.mean(), 1.51044125730)
        stats.appendleft(1000)
        self.assertAlmostEqual(stats.mean(), 2.20121678520)

    def test_std(self):
        stats = _stat()
        data = list(range(1, 11))
        for i in data:
            stats.appendleft(float(i))
        self.assertAlmostEqual(stats.std(), 0.695407498476473)
        stats.appendleft(1000)
        self.assertAlmostEqual(stats.std(), 1.640541783885151)

    def test_mode(self):
        stats = _stat()
        data = list(range(1, 11))
        for i in data:
            stats.appendleft(float(i))
        self.assertAlmostEqual(stats.mode(), 2.79225543353)
        stats.appendleft(1000)
        self.assertAlmostEqual(stats.mode(), 0.61252803911)

    def test_median(self):
        stats = _stat()
        data = list(range(1, 11))
        for i in data:
            stats.appendleft(float(i))
        self.assertAlmostEqual(stats.median(), 4.52872868811)
        stats.appendleft(1000)
        self.assertAlmostEqual(stats.median(), 9.03600168611)

if __name__ == "__main__":
    t = unittest.TestLoader().loadTestsFromTestCase(TestStat)
    unittest.TextTestRunner(verbosity=2).run(t)
