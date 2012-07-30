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
from __future__ import print_function
from scoop import futures
from scoop import _control
import scoop
import unittest
import subprocess
import time
import copy
import os
import sys
    
def func0(n):
    task = futures.submit(func1, n)
    result = task.result()
    return result

def func1(n):
    result = futures.map(func2, [i+1 for i in range(n)])
    return sum(result)

def func2(n):
    launches = []
    for i in range(n):
        launches.append(futures.submit(func3, i + 1))
    result = futures.as_completed(launches)
    return sum(r.result() for r in result)

def func3(n):
    result = list(futures.map(func4, [i+1 for i in range(n)]))
    return sum(result)

def func4(n):
    result = n*n
    return result
    
def funcCallback():
    f = futures.submit(func4, 100)
    
    def callBack(future):
        future.was_callabacked = True
        
    f.add_done_callback(callBack)
    if len(f.callback) == 0:
        return False
    futures.wait((f,))
    try:
        return f.was_callabacked
    except:
        return False
        
def funcCancel():
    f = futures.submit(func4, 100)
    f.cancel()
    return f.cancelled()
            
def funcCompleted(n):
    launches = []
    for i in range(n):
        launches.append(futures.submit(func4, i + 1))
    result = futures.as_completed(launches)
    return sum(r.result() for r in result)

def funcDone():
    f = futures.submit(func4, 100)
    futures.wait((f,))
    done = f.done()
    if done != True:
        return done
    res = f.result()
    done = f.done()
    return done
    
def funcExcept(n):
    f = futures.submit(funcRaise, n)
    try:
        f.result()
    except:
        return True

    return False

def funcRaise(n):
    raise Exception("Test exception")
    
def funcSub(n):
    f = futures.submit(func4, n)
    return f.result()

def main(n):
    task = futures.submit(func0, n)
    futures.wait([task], return_when=futures.ALL_COMPLETED)
    result = task.result()
    return result
    
def main_simple(n):
    task = futures.submit(func3, n)
    futures.wait([task], return_when=futures.ALL_COMPLETED)
    result = task.result()
    return result

def port_ready(port, socket):
    """Checks if a given port is already binded"""
    try:
        socket.connect(('127.0.0.1', port))
    except IOError:
        return False
    else:
        socket.shutdown(2)
        socket.close()
        return True
        
    
class TestScoopCommon(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        #self.default_highwatermark = Task.execQueue.highwatermark
        # Parent initialization
        super(TestScoopCommon, self).__init__(*args, **kwargs)
        
    def multiworker_set(self):
        #Backupenv = os.environ.copy()
        #os.environ.update({'WORKER_NAME': 'worker',
        #               'BROKER_NAME':'broker',
        #               'IS_ORIGIN': '0',
        #               'BROKER_ADDRESS': 'tcp://127.0.0.1:5555',
        #               'META_ADDRESS': 'tcp://127.0.0.1:5556'})   
        worker = subprocess.Popen([sys.executable, "-m", "scoop.bootstrap",
        "--workerName", "worker", "--brokerName", "broker", "--brokerAddress",
        "tcp://127.0.0.1:5555", "--metaAddress", "tcp://127.0.0.1:5556", "tests.py"])
        #os.environ = Backupenv
        return worker

        
    def setUp(self):
        # Start the server
        self.server = subprocess.Popen([sys.executable,"-m", "scoop.broker",
        "--tPort", "5555", "--mPort", "5556"])
        import socket, datetime, time
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        begin = datetime.datetime.now()
        while not port_ready(5555, s):
            if (datetime.datetime.now() - begin > datetime.timedelta(seconds=3)):
                raise Exception('Could not start server!')
            pass
        scoop.IS_ORIGIN = True
        scoop.WORKER_NAME = 'origin'.encode()
        scoop.BROKER_NAME = 'broker'.encode()
        scoop.BROKER_ADDRESS = 'tcp://127.0.0.1:5555'
        scoop.META_ADDRESS = 'tcp://127.0.0.1:5556'
        scoop.worker = (scoop.WORKER_NAME, scoop.BROKER_NAME)
        scoop.VALID = True
        scoop.DEBUG = False
        scoop.SIZE = 2
        
        #os.environ.update({'WORKER_NAME': 'origin', # this is the default name
        #               'BROKER_NAME':'broker',
        #               'IS_ORIGIN': '1',
        #               'BROKER_ADDRESS': 'tcp://127.0.0.1:5555',
        #               'META_ADDRESS': 'tcp://127.0.0.1:5556'})
        #try:
        #    reload(scoop)
        #except:
        #    import imp
        #    imp.reload(scoop)
        
    
    def tearDown(self):
        try: self.w.kill()
        except: pass
        # Destroy the server
        if self.server.poll() == None:
            try: self.server.kill()
            except: pass
            


class TestMultiFunction(TestScoopCommon):
    def __init__(self, *args, **kwargs):
        # Parent initialization
        super(TestMultiFunction, self).__init__(*args, **kwargs)
        self.main_func = main
        self.small_result = 77
        self.large_result = 76153

    def test_small_uniworker(self):
        _control.FutureQueue.highwatermark = 10
        _control.FutureQueue.lowwatermark = 5
        result = futures._startup(self.main_func, 4)
        self.assertEqual(result, self.small_result)
        
    def test_small_no_lowwatermark_uniworker(self):
        _control.FutureQueue.highwatermark = 9999999999999
        _control.FutureQueue.lowwatermark = 1
        result = futures._startup(self.main_func, 4)
        self.assertEqual(result, self.small_result)
    
    def test_small_foreign_uniworker(self):
        _control.FutureQueue.highwatermark = 1
        result = futures._startup(self.main_func, 4)
        self.assertEqual(result, self.small_result)
        
    def test_small_local_uniworker(self):
        _control.FutureQueue.highwatermark = 9999999999999
        result = futures._startup(self.main_func, 4)
        self.assertEqual(result, self.small_result)
    
    def test_large_uniworker(self):
        _control.FutureQueue.highwatermark = 9999999999999
        result = futures._startup(self.main_func, 20)
        self.assertEqual(result, self.large_result)
        
    def test_large_no_lowwatermark_uniworker(self):
        _control.FutureQueue.lowwatermark = 1
        _control.FutureQueue.highwatermark = 9999999999999
        result = futures._startup(self.main_func, 20)
        self.assertEqual(result, self.large_result)

    def test_large_foreign_uniworker(self):
        _control.FutureQueue.highwatermark = 1
        result = futures._startup(self.main_func, 20)
        self.assertEqual(result, self.large_result)
        
    def test_large_local_uniworker(self):
        _control.FutureQueue.highwatermark = 9999999999999
        result = futures._startup(self.main_func, 20)
        self.assertEqual(result, self.large_result)
        
    def test_small_local_multiworker(self):
        self.w = self.multiworker_set()
        _control.FutureQueue.highwatermark = 9999999999
        Backupenv = os.environ.copy()
        result = futures._startup(self.main_func, 4)
        self.assertEqual(result, self.small_result)
        time.sleep(0.5)
        os.environ = Backupenv
    
    def test_small_foreign_multiworker(self):
        self.w = self.multiworker_set()
        _control.FutureQueue.highwatermark = 1
        Backupenv = os.environ.copy()
        result = futures._startup(self.main_func, 4)
        self.assertEqual(result, self.small_result)
        time.sleep(0.5)
        os.environ = Backupenv

class TestSingleFunction(TestMultiFunction):
    def __init__(self, *args, **kwargs):
        # Parent initialization
        super(TestSingleFunction, self).__init__(*args, **kwargs)
        self.main_func = main_simple
        self.small_result = 30
        self.large_result = 2870 

class TestApi(TestScoopCommon):
    def __init(self, *args, **kwargs):
        super(TestApi, self).__init(*args, **kwargs)

    def test_as_Completed_single(self):
        result = futures._startup(funcCompleted, 30)
        self.assertEqual(result, 9455)

    def test_as_Completed_multi(self):
        self.w = self.multiworker_set()
        result = futures._startup(funcCompleted, 30)
        self.assertEqual(result, 9455)

    def test_map_single(self):
        result = futures._startup(func3, 30)
        self.assertEqual(result, 9455)

    def test_map_multi(self):
        self.w = self.multiworker_set()
        result = futures._startup(func3, 30)
        self.assertEqual(result, 9455)

    def test_submit_single(self):
        result = futures._startup(funcSub, 10)
        self.assertEqual(result, 100)

    def test_submit_multi(self):
        self.w = self.multiworker_set()
        result = futures._startup(funcSub, 10)
        self.assertEqual(result, 100)

    def test_exception_single(self):
        result = futures._startup(funcExcept, 19)
        self.assertTrue(result)

    def test_exception_multi(self):
        self.w = self.multiworker_set()
        result = futures._startup(funcExcept, 19)
        self.assertTrue(result)

    def test_done(self):
        result = futures._startup(funcDone)
        self.assertTrue(result)

    def test_cancel(self):
        self.assertTrue(futures._startup(funcCancel))

    def test_callback(self):
        self.assertTrue(futures._startup(funcCallback))

if __name__ == '__main__' and os.environ.get('IS_ORIGIN', "1") == "1":
    simple = unittest.TestLoader().loadTestsFromTestCase(TestSingleFunction)
    complex = unittest.TestLoader().loadTestsFromTestCase(TestMultiFunction)
    api = unittest.TestLoader().loadTestsFromTestCase(TestApi)
    if len(sys.argv) > 1:
        if sys.argv[1] == "simple":
            unittest.TextTestRunner(verbosity=2).run(simple)
        elif sys.argv[1] == "complex":
            unittest.TextTestRunner(verbosity=2).run(complex)
        elif sys.argv[1] == "api":
            unittest.TextTestRunner(verbosity=2).run(api)
    else:
        unittest.main()
elif __name__ == '__main__':
    futures._startup(main_simple)
