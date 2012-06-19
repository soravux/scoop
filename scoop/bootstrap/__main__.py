#!/usr/bin/env python
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


from scoop.futures import _startup
import runpy
import sys
import os
import functools
import argparse

path = "examples"
tempModule = 'piCalc.py'
arguments = []
basename = os.path.basename(tempModule)[:-3]
programPath = os.path.join(path, os.path.dirname(tempModule))

sys.path.append(programPath)
user_module = __import__(basename)
try:
    attrlist = user_module.__all__
except AttributeError:
    attrlist = dir(user_module)
for attr in attrlist:
    globals()[attr] = getattr(user_module, attr)

sys.argv += arguments
_startup(functools.partial(runpy.run_path, tempModule,
    init_globals=globals(),run_name="__main__"))
