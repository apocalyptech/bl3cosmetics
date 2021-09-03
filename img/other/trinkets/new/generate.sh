#!/bin/bash
# vim: set expandtab tabstop=4 shiftwidth=4:

montage individual/*.png -geometry 200x130+1+1 -tile 5x6 -background black master.png
ls -l master*.png

