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
from scoop.types import Task
import unittest
import subprocess
import time
import copy
import os
import sys

def func0(n):
    task = futures.submit(func1, n)
    result = futures.join(task)
    return result

def func1(n):
    result = futures.mapJoin(func2, [i+1 for i in range(0,n)])
    return sum(result)

def func2(n):
    result = futures.mapJoin(func3, [i+1 for i in range(0,n)])
    return sum(result)

def func3(n):
    result = futures.mapJoin(func4, [i+1 for i in range(0,n)])
    return sum(result)

def func4(n):
    result = n*n
    return result

def main(n):
    task = futures.submit(func0, n)
    return futures.join(task)

def main_simple(n):
    task = futures.submit(func3, n)
    return futures.join(task)
        
    
class TestScoopCommon(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.default_highwatermark = Task.execQueue.highwatermark
        self.default_Task = copy.deepcopy(Task)
        # Parent initialization
        super(TestScoopCommon, self).__init__(*args, **kwargs)
        
    def multiworker_set(self):
        Backupenv = os.environ.copy()
        os.environ.update({'WORKER': '1-2', 'IS_ORIGIN': '0'})    
        worker = subprocess.Popen([sys.executable, "tests.py"])
        os.environ = Backupenv
        return worker

        
    def setUp(self):
        # Start the server
        self.server = subprocess.Popen([sys.executable, "broker.py"])
        import socket, datetime, time
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        begin = datetime.datetime.now()
        while(datetime.datetime.now() - begin < datetime.timedelta(seconds=10)):
            time.sleep(0.1)
            try:
                s.connect(('127.0.0.1', 5555))
                s.shutdown(2)
                break
            except:
                pass
        else:
            raise Exception('Could not start server!')
        # Reset any previously setted static variable
        Task = copy.deepcopy(self.default_Task)
    
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
        Task.execQueue.highwatermark = 10
        Task.execQueue.lowwatermark = 5
        result = futures.startup(self.main_func, 4)
        self.assertEqual(result, self.small_result)
        
    def test_small_no_lowwatermark_uniworker(self):
        Task.execQueue.highwatermark = 9999999999999
        Task.execQueue.lowwatermark = 1
        result = futures.startup(self.main_func, 4)
        self.assertEqual(result, self.small_result)
    
    def test_small_foreign_uniworker(self):
        Task.execQueue.highwatermark = 1
        result = futures.startup(self.main_func, 4)
        self.assertEqual(result, self.small_result)
        
    def test_small_local_uniworker(self):
        Task.execQueue.highwatermark = 9999999999999
        result = futures.startup(self.main_func, 4)
        self.assertEqual(result, self.small_result)
    
    def test_large_uniworker(self):
        Task.execQueue.highwatermark = 9999999999999
        result = futures.startup(self.main_func, 20)
        self.assertEqual(result, self.large_result)
        
    def test_large_no_lowwatermark_uniworker(self):
        Task.execQueue.lowwatermark = 1
        Task.execQueue.highwatermark = 9999999999999
        result = futures.startup(self.main_func, 20)
        self.assertEqual(result, self.large_result)

    def test_large_foreign_uniworker(self):
        Task.execQueue.highwatermark = 1
        result = futures.startup(self.main_func, 20)
        self.assertEqual(result, self.large_result)
        
    def test_large_local_uniworker(self):
        Task.execQueue.highwatermark = 9999999999999
        result = futures.startup(self.main_func, 20)
        self.assertEqual(result, self.large_result)
        
    def test_small_local_multiworker(self):
        self.w = self.multiworker_set()
        Task.execQueue.highwatermark = 9999999999
        Backupenv = os.environ.copy()
        os.environ.update({'WORKER': 'master-node',
                           'IS_ORIGIN': '1'})
        result = futures.startup(self.main_func, 4)
        self.assertEqual(result, self.small_result)
        time.sleep(0.5)
        os.environ = Backupenv
    
    def test_small_foreign_multiworker(self):
        self.w = self.multiworker_set()
        Task.execQueue.highwatermark = 1
        Backupenv = os.environ.copy()
        os.environ.update({'WORKER': 'master-node',
                           'IS_ORIGIN': '1'})
        result = futures.startup(self.main_func, 4)
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

if __name__ == '__main__' and os.environ.get('IS_ORIGIN', "1") == "1":
    simple = unittest.TestLoader().loadTestsFromTestCase(TestSingleFunction)
    complex = unittest.TestLoader().loadTestsFromTestCase(TestMultiFunction)
    if len(sys.argv) > 1:
        if sys.argv[1] == "simple":
            unittest.TextTestRunner(verbosity=2).run(simple)
        elif sys.argv[1] == "complex":
            unittest.TextTestRunner(verbosity=2).run(complex)
    else:
        unittest.main()
elif __name__ == '__main__':
    futures.startup(main_simple)