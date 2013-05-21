from scoop._types import StopWatch

import unittest
import time

class TestStopWatch(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestStopWatch, self).__init__(*args, **kwargs)

    def test_get(self):
        watch = StopWatch()
        first = watch.get()
        time.sleep(0.1)
        second = watch.get()
        self.assertGreater(second - first, 0.1)

    def test_halt(self):
        watch = StopWatch()
        watch.halt()
        first = watch.get()
        time.sleep(0.1)
        second = watch.get()
        self.assertEqual(first, second)

    def test_resume(self):
        watch = StopWatch()
        watch.halt()
        first = watch.get()
        watch.resume()
        time.sleep(0.1)
        second = watch.get()
        self.assertGreater(second - first, 0.1)

    def test_reset(self):
        watch = StopWatch()
        time.sleep(0.1)
        watch.reset()
        self.assertLess(watch.get(), 0.1)


if __name__ == "__main__":
    t = unittest.TestLoader().loadTestsFromTestCase(TestStopWatch)
    unittest.TextTestRunner(verbosity=2).run(t)
