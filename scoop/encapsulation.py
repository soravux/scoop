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
import marshal


def functionFactory(inCode):
    def generatedFunction():
        pass
    generatedFunction.__code__ = marshal.loads(inCode)
    return generatedFunction

class FunctionEncapsulation(object):
    def __init__(self, inFunc):
        self.code = marshal.dumps(inFunc.__code__)
        # TODO: __defaults__, docstrings

    def getFunction(self):
        return functionFactory(self.code)

class ExternalEncapsulation(object):
    pass