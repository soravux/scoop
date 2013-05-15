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

"""This examples imports a list of 100 web sites and returns
the sizes in bytes of every web site. It compares the speed
to do this task of the regular python map, futures.map and
the as_completed function."""

import urllib.request
import urllib.error
from scoop import futures
import socket
import time

def getSize(string):
    """ This functions opens a web sites and then calculate the total
    size of the page in bytes. This is for the sake of the example. Do
    not use this technique in real code as it is not a very bright way
    to do this."""
    try:
        # We open the web page
        with urllib.request.urlopen(string, None, 1) as f:
            return sum(len(line) for line in f)
    except (urllib.error.URLError, socket.timeout) as e:
        return 0

if __name__ == "__main__":
    # The pageurl variable contains a link to a list of web sites. It is
    # commented for security's sake.
    #pageurl = "http://httparchive.org/lists/Fortune%20500.txt"
    pageurl  = "http://www.example.com"
    with urllib.request.urlopen(pageurl) as pagelist:
        pages = [page.decode() for page in pagelist][:30]

    # This will apply the getSize function serially on every item
    # of the pages list.
    for res in map(getSize, pages):
        time.sleep(0.1) # Work on the data ...
        print(res)

    # This will apply the getSize function on every item of the pages list
    # in parallel. The results will be treated in the same order as the
    # pages.
    for res in futures.map(getSize, pages):
        time.sleep(0.1) # Work on the data ...
        print(res)

    # This will apply the getSize function on every item of the pages list
    # in parallel. The results will be treated as they are produced.
    fut = [futures.submit(getSize, page) for page in pages]
    for f in futures.as_completed(fut):
        time.sleep(0.1) # Work on the data
        print(f.result())
