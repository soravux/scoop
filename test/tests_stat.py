from scoop._control import _stat

import unittest

class TestStat(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestStat, self).__init__(*args, **kwargs)

    def test_appendleft(self):
        stats = _stat()
        data = list(range(5))
        for i in data[::-1]:
            stats.appendleft(i)
        for i, j in enumerate(stats):
            self.assertEqual(data[i], j)
     
    def test_maxlen(self):
        stats = _stat()
        data = list(range(15))
        for i in data[::-1]:
            stats.appendleft(i)
        for i, j in enumerate(stats):
            self.assertEqual(data[i], j)
        self.assertEqual(len(stats), 10)

    def test_mean(self):
        stats = _stat()
        data = list(range(15))
        for i in data:
            stats.appendleft(float(i))
        self.assertEqual(stats.mean(), 9.5)
        stats.appendleft(1000)
        self.assertEqual(stats.mean(), 109.0)

if __name__ == "__main__":
    t = unittest.TestLoader().loadTestsFromTestCase(TestStat)
    unittest.TextTestRunner(verbosity=2).run(t)
