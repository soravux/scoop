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
"""
Example of Future callback usage.
"""
from scoop import futures
import time

def myFunc(n):
    time.sleep(n)
    return n

def doneElement(inFuture):
    print("Done: {0}".format(inFuture.result()))

def main():
    # Create launches
    launches = [futures.submit(myFunc, i + 1) for i in range(5)]

    # Add a callback on every launches
    for launch in launches:
        launch.add_done_callback(doneElement)

    # Wait for the launches to complete.
    [completed for completed in futures.as_completed(launches)]


if __name__ == "__main__":
    main()
