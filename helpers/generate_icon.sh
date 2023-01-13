#!/bin/bash

# only needed for flatpak
# shopt -s expand_aliases
# alias inkscape='flatpak run org.inkscape.Inkscape'

inkscape -o autotag_metadata.png -w 256 -h 256 autotag_metadata.svg >/dev/null 2>/dev/null
convert autotag_metadata.png -define icon:auto-resize=256,128,64,48,32,16 autotag_metadata.ico

# for size in 16 32 48; do
#     inkscape -o $size.png -w $size -h $size icon.svg >/dev/null 2>/dev/null
# done
# convert -background white -flatten 16.png 32.png 48.png 128.png 256.png icon.ico
