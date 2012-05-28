API Reference
=============

Futures module
--------------

The following methods are part of the futures module. They can be accessed like
so::
    
    from scoop import futures
    
    results = futures.map(func, data)
    futureObject = futures.submit(func, arg)
    ...

.. automodule:: scoop.futures
   :members:
   
Future class
------------

When you ``submit()`` a task, you receive a Future object. This instance will
possess the following methods.
   
.. autoclass:: scoop.types.Future
   :members: