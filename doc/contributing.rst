Contributing
============


Reporting a bug
---------------

You can report a bug on the 
`issue tracker <https://github.com/soravux/scoop/issues>`_ on google code or
on the `mailing list <http://groups.google.com/group/scoop-users>`_.


Retrieving the latest code
--------------------------

You can check the latest sources with the command::

    git clone https://github.com/soravux/scoop.git

Bear in mind that this development code may be partially broken or unfinished.
To get a stable version of the code, checkout to a release tag using
`git checkout tags/<tag name>`.


Coding guidelines
-----------------

Most of those conventions are base on Python `PEP8 <http://www.python.org/dev/peps/pep-0008/>`_.

    *A style guide is about consistency. Consistency with this style guide is important.
    Consistency within a project is more important. Consistency within one module or 
    function is most important.*

Code layout
+++++++++++

Same as PEP8.

Imports
+++++++

Standard library imports must be first, followed by SCOOP imports and finally
custom modules. Each section should be separated by an empty line as such::

  import system
  
  from scoop import futures

  import myModule

Whitespace in Expressions and Statements
++++++++++++++++++++++++++++++++++++++++

Same as PEP8.

Comments
++++++++

Same as PEP8

Documentation Strings
+++++++++++++++++++++

Same as PEP8

Naming Conventions
++++++++++++++++++

- **Module**: lowercase convention.
- **Class**: CapWords (upper camel case) convention (ie. AnExample).
- **Function** / Procedure: mixedCase (lower camel case) convention. First
  word should be an action verb.
- **Variable**: lower_case_with_underscores convention. Should be as short 
  possible as.

If a name already exists in the standard library, an underscore is appended to
it. (ie. a custom `range` function could be called `range_`. A custom `type`
function could be called `type_`.)


Architecture
------------

Communication protocols
+++++++++++++++++++++++

Here are the message types from the point of view of a broker. Message coming from workers are always from their Task socket.

============ ====== ================== ====================
Message name Socket Arguments          Description
INIT         Task                      Handshake from a worker: allows a broker to recognize a new worker and propagate the currently shared variables.
CONNECT      Task   Addresses          Notify a broker of the existence of other brokers.
REQUEST      Task                      Worker requesting task(s).
TASK         Task   Task               A task (future) to be executed.
REPLY        Task*  Task, Destination  The result of a task to be sent to its parent. Communicated directly between workers if possible.
SHUTDOWN     Info                      Request a shutdown of the entire worker pool.
VARIABLE     Info   Key, Value, Source A worker requested the share of a variable. The broker propagates it to its fellow workers.
TASKEND      Info   askResult, groupID A collaborative task (scan, reduce, etc.) have ended, memory can be freed on workers.
BROKER_INFO  Info                      Propagate information about other brokers to workers.
============ ====== ================== ====================
