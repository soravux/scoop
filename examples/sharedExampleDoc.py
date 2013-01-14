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
Example of shared constants use.
This is a synthetic partition and evaluation example that should only be
analysed for its shared module API.
"""
from itertools import combinations_with_replacement, tee
import string
from scoop import futures, shared

HASH_TO_FIND = hash("SCOOP")


def generateHashes(inIterator):
    """Compute hashes."""
    for combination in inIterator:
        # Stop as soon as a worker finds the solution
        if shared.getConst('Done', timeout=0):
            return False

        # Compute the current combination hash
        inString = "".join(combination).strip()
        if hash(inString) == HASH_TO_FIND:
            # Share to every other worker that the solution has been found
            shared.setConst(Done=True)
            return inString

    return False


if __name__ == "__main__":
    # Generate possible characters
    possibleCharacters = []
    possibleCharacters.extend(list(string.ascii_uppercase))
    possibleCharacters.extend(' ')

    # Generate the solution space.
    stringIterator = combinations_with_replacement(possibleCharacters, 5)

    # Partition the solution space into iterators 
    # Keep in mind that the tee operator evaluates the whole solution space
    # making it pretty memory inefficient.
    SplittedIterator = tee(stringIterator, 1000)

    # Parallelize the solution space evaluation
    results = futures.map(generateHashes, SplittedIterator)

    # Loop until a solution is found
    for result in results:
        if result:
            break

    print(result)
