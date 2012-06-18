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
    
More informations are available in the :doc:`usage` document.

.. automodule:: scoop.futures
   :members:
   
Future class
------------

The :meth:`scoop.futures.submit` function will return a Future object. This 
instance will possess the following methods.
   
.. autoclass:: scoop._types.Future
   :members: