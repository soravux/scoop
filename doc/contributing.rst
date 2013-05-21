Contributing
============


Reporting a bug
---------------

You can report a bug on the 
`issue tracker <http://code.google.com/p/scoop/issues/list>`_ on google code or
on the `mailing list <http://groups.google.com/group/scoop-users>`_.


Retrieving the latest code
--------------------------

You can check the latest sources with the command::

    hg clone https://code.google.com/p/scoop/ 

Bear in mind that this development code may be partially broken or unfinished.
To get a stable version of the code, update to a release tag using 
`hg update <tag name>`.


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