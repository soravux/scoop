API Reference
=============

.. note:

    Please note that the current version of SCOOP doesn't support timeout. Its
    support has been scheduled in a future version.

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

The :meth:`~scoop.futures.submit` function returns a :class:`scoop._types.Future` object. This 
instance possess the following methods.
   
.. autoclass:: scoop._types.Future
   :members: