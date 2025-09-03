"""
Tile Images Script

This script splits large satellite images into smaller tiles for processing and analysis.
It is useful for handling large images that may be too memory-intensive to process as a whole.

Main Features:
- Splits images into configurable tile sizes (default: 512x512 pixels)
- Uses overlapping tiles (50% overlap) to ensure complete coverage
- Supports multiband images
- Optional filtering of tiles with no-data values
- Parallel processing for improved performance

Inputs:
- Georeferenced images from results_georeference/ folder
- Configurable tile dimensions (height and width)

Outputs:
- Tiled images saved in results_tile_images/ folder
- Each tile is named with format: original_name_XX-of-YY.tif
"""

import rasterio as rio
from rasterio import windows

from itertools import product
from matplotlib import pyplot as plt
import numpy as np
import os
import glob
import sys

# Add parent directory to path to import load_config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from load_config import load_config, get_georeference_output_folder, get_tile_images_output_folder

# adapted from https://gis.stackexchange.com/questions/285499/how-to-split-multiband-image-into-image-tiles-using-rasterio
def make_tiles(image, output_folder, tile_height=512, tile_width=512, skip_no_data=False):
    with rio.open(image) as src:
        filepath, filename = os.path.split(image)
        file_base, file_extension = os.path.splitext(filename)
        meta = src.meta.copy()
        num_cols, num_rows = src.meta['width'], src.meta['height']
        overall_window = windows.Window(col_off=0, row_off=0, width=num_cols, height=num_rows)
        offsets = product(range(0, num_cols, tile_height//2), range(0, num_rows, tile_width//2))
        tiles = []
        for col_off, row_off in offsets:
            curr_window = windows.Window(col_off=col_off, row_off=row_off, width=tile_width, height=tile_height)
            curr_transform = windows.transform(curr_window, src.transform)
            tiles.append((curr_window.intersection(overall_window), curr_transform))
        for i in range(len(tiles)):
            window, transform = tiles[i]
            meta['transform'] = transform
            meta['width'] = tile_width
            meta['height'] = tile_height
            window_data = src.read(window=window)
            # optionally skip tiles with no data values
            if skip_no_data:
                if 0 in window_data[..., :-1]:
                    continue
            out_name = file_base + "_" + str(i + 1).zfill(2) + "-of-" + str(len(tiles)) + file_extension
            out_path = os.path.join(output_folder, out_name)
            with rio.open(out_path, 'w', **meta) as dst:
                dst.write(src.read(window=window))

# example usage
if __name__ == '__main__':
    # Load configuration
    config = load_config()
    
    # Get input and output folders from config
    input_folder = get_georeference_output_folder(config)
    output_folder = get_tile_images_output_folder(config)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Get all .tif files from the georeference output folder
    files = glob.glob(os.path.join(input_folder, "*.tif"))
    
    print(f"Processing {len(files)} files from {input_folder}")
    print(f"Output will be saved to {output_folder}")
    
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=6) as p:
        # Pass both the file and output_folder to make_tiles
        p.map(lambda f: make_tiles(f, output_folder), files)