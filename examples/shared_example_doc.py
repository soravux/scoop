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
"""
from scoop import futures, shared


def getValue(words):
    """Computes the sum of the values of the words."""
    value = 0
    for word in words:
        for letter in word:
            # shared.getConst will evaluate to the dictionary broadcasted by
            # the root Future
            value += shared.getConst('lettersValue')[letter]
    return value


if __name__ == "__main__":
    # Set the values of the letters according to the language and broadcast it
    # This list is set at runtime
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'francais':
        shared.setConst(lettersValue={'a': 1, 'b': 3, 'c': 3, 'd': 2, 'e': 1,
        'f': 4, 'g': 2, 'h': 4, 'i': 1, 'j': 8, 'k':10, 'l': 1, 'm': 2, 'n': 1,
        'o': 1, 'p': 3, 'q': 8, 'r': 1, 'r': 1, 's': 1, 't': 1, 'u': 1, 'v': 4,
        'w':10, 'x':10, 'y':10, 'z': 10})
        print("French letter values used.")
    else:
        shared.setConst(lettersValue={'a': 1, 'b': 3, 'c': 3, 'd': 2, 'e': 1,
        'f': 4, 'g': 2, 'h': 4, 'i': 1, 'j': 8, 'k': 5, 'l': 1, 'm': 3, 'n': 1,
        'o': 1, 'p': 3, 'q':10, 'r': 1, 'r': 1, 's': 1, 't': 1, 'u': 1, 'v': 4,
        'w': 4, 'x': 8, 'y': 4, 'z': 10})
        print("English letter values used.")

    # Get the player words (generate a list of random letters 
    import random
    import string
    random.seed(3141592653)
    words = []
    player_quantity = 4
    words_per_player = 10
    word_letters = (1, 6)
    for pid in range(player_quantity):
        player = []
        for _ in range(words_per_player):
            word = "".join(random.choice(string.ascii_lowercase) for _ in range(random.randint(*word_letters)))
            player.append(word)
        print("Player {pid} played words: {player}".format(**locals()))
        words.append(player)
    
    # Compute the score of every player and display it
    results = list(futures.map(getValue, words))
    for pid, result in enumerate(results):
        print("Player {pid}: {result}".format(**locals()))
