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
Example of parallel image resizing using PIL.
"""
import time
import sys
from collections import namedtuple
from scoop import futures

try:
    import Image
except:
    raise Exception("This example uses PIL, the Python Imaging Library."
                    "You must install this library before using this example.")

# Set constants
imageSize = namedtuple('imageSize', ['w', 'y'], verbose=False)
TARGET_SIZE = imageSize(512, 384)
DIVISION_HEIGHT = 2
DIVISION_WIDTH = 2

# Define a serialization for image format
sImage = namedtuple('sImage', ['pixels', 'size', 'mode'], verbose=False)


if len(sys.argv) < 2:
    raise Exception("This example needs an image file path as first parameter."
                    "\nPlease re-execute it using :\n"
                    "   python -m scoop {0} yourImage.jpg".format(__file__))

originalImage = Image.open(sys.argv[-1])


def sliceImage(image, divWidth, divHeight):
    """Divide the received image in multiple tiles"""
    w, h = image.size
    tiles = []
    for y in range(0, h - 1 , h/divHeight):
        my = min(y + h/divHeight, h)
        for x in range(0, w - 1, w/divWidth):
            mx = min(x + w/divWidth, w)
            tiles.append(image.crop((x, y, mx, my)))
    return tiles


def resizeTile(index, size):
    """Apply Antialiasing resizing to tile"""
    resized = tiles[index].resize(size, Image.ANTIALIAS)
    return sImage(resized.tostring(), resized.size, resized.mode)


# Generate image tiles on every workers
ts = time.time()
tiles = sliceImage(originalImage,
                   divWidth=DIVISION_WIDTH,
                   divHeight=DIVISION_HEIGHT)


if __name__ == '__main__':
    # Resize the tiles
    resizedTiles = list(futures.map(resizeTile,
                        range(len(tiles)),
                        size=(TARGET_SIZE[0] // DIVISION_WIDTH,
                              TARGET_SIZE[1] // DIVISION_HEIGHT)))

    # Create the new canvas that will receive the tiles
    resizedParallelImage = Image.new(originalImage.mode, TARGET_SIZE, "white")

    # Fusion the tiles together on the canvas
    imgPosition = imageSize(0, 0)
    for index, tile in enumerate(resizedTiles):
        # Convert the serialized image to a pastable image format
        imgTile = Image.fromstring(tile.mode, tile.size, tile.pixels)
        # Compute tile position in canvas
        imgPosition = ((index % DIVISION_WIDTH) * TARGET_SIZE[0] // DIVISION_WIDTH,
                       (index // DIVISION_WIDTH) * TARGET_SIZE[1] // DIVISION_HEIGHT,
                       )
        # Paste the tile to the canvas
        resizedParallelImage.paste(imgTile,
                                   imgPosition)
    pts = time.time() - ts
    resizedParallelImage.show()

    # Serial computation of tree depth
    ts = time.time()
    resizedImage = originalImage.resize(TARGET_SIZE, Image.ANTIALIAS)
    sts = time.time() - ts
    resizedImage.show()
    
    print("Parallel time: {0:.5f}s\nSerial time:   {1:.5f}s".format(pts, sts))
