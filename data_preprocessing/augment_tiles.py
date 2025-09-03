"""
augment_tiles.py
----------------

This module provides data augmentation functionality for image tiles.
It creates rotated (90°, 180°, 270°) and flipped versions of input tiles,
resulting in 7 augmented tiles for every input tile (8 total including original).

Functions:
    - augment_tiles(tile_path, output_path, max_tiles=40): Creates augmented versions of tiles
    - _augment_and_write(bands, output_path, meta, rotation_angle): Helper function for rotation
    - _flip_bands(bands): Helper function for flipping
"""

import rasterio as rio
import numpy as np
import os
import glob
import sys

# Add parent directory to path to import load_config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from load_config import load_config, get_tile_images_output_folder, get_augment_tiles_output_folder

def _augment_and_write(bands, output_path, meta, rotation_angle):
    """
    Helper function to rotate bands and write to file
    
    Args:
        bands: Tuple of band arrays
        output_path: Path to save the augmented image
        meta: Rasterio metadata
        rotation_angle: Rotation angle (0=no rotation, 1=90°, 2=180°, 3=270°)
    """
    rotated_bands = []
    for band in bands:
        if rotation_angle == 0:
            rotated_band = band
        elif rotation_angle == 1:  # 90 degrees
            rotated_band = np.rot90(band, k=1)
        elif rotation_angle == 2:  # 180 degrees
            rotated_band = np.rot90(band, k=2)
        elif rotation_angle == 3:  # 270 degrees
            rotated_band = np.rot90(band, k=3)
        rotated_bands.append(rotated_band)
    
    # Update metadata for rotated image
    meta_rot = meta.copy()
    if rotation_angle in [1, 3]:  # 90 or 270 degrees
        meta_rot['width'], meta_rot['height'] = meta['height'], meta['width']
    
    with rio.open(output_path, 'w', **meta_rot) as dst:
        for i, band in enumerate(rotated_bands, 1):
            dst.write(band, i)

def _flip_bands(bands):
    """
    Helper function to flip bands vertically
    
    Args:
        bands: Tuple of band arrays
    
    Returns:
        List of flipped band arrays
    """
    return [np.flipud(band) for band in bands]

def augment_tiles(tile_path, output_path, max_tiles=40):
    """
    Takes the path to image tiles and creates tiles that are rotated 90°, 180° and 270° 
    as well as their flipped counterparts. This results in 7 augmented tiles for every input tile 
    (8 total including the original tile).
    
    Args:
        tile_path: Path to the directory containing input tiles
        output_path: Path to the directory where augmented tiles will be saved
        max_tiles: Maximum number of tiles to process (default: 40)
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    
    files = glob.glob(os.path.join(tile_path, "*.tif"))
    
    # Filter out already augmented files
    files = set(files) - set(glob.glob(os.path.join(tile_path, "*rot*")))
    files = set(files) - set(glob.glob(os.path.join(tile_path, "*flip*")))
    
    # Take only the first max_tiles
    files = sorted(list(files))[:max_tiles]
    
    print(f"Processing {len(files)} tiles for augmentation...")
    print(f"Each tile will generate 7 additional augmented versions (8 total per tile)")
    print(f"Output directory: {output_path}")
    
    successful = 0
    failed = 0
    
    for i, file in enumerate(files):
        filename = os.path.basename(file)
        file_base, file_extension = os.path.splitext(filename)
        
        # Generate filepaths for new tiles in the output directory
        path_90 = os.path.join(output_path, file_base + "_rot90" + file_extension)
        path_180 = os.path.join(output_path, file_base + "_rot180" + file_extension)
        path_270 = os.path.join(output_path, file_base + "_rot270" + file_extension)
        path_flip_name = os.path.join(output_path, file_base + "_flip" + file_extension)
        path_flip_90 = os.path.join(output_path, file_base + "_rot90_flip" + file_extension)
        path_flip_180 = os.path.join(output_path, file_base + "_rot180_flip" + file_extension)
        path_flip_270 = os.path.join(output_path, file_base + "_rot270_flip" + file_extension)
        
        try:
            with rio.open(file, driver="GTiff") as src:
                # Read all bands
                num_bands = src.count
                bands = tuple(src.read(i) for i in range(1, num_bands + 1))
                meta = src.meta
                
                # Create augmented versions
                _augment_and_write(bands, path_90, meta, 1)  # 90°
                _augment_and_write(bands, path_180, meta, 2)  # 180°
                _augment_and_write(bands, path_270, meta, 3)  # 270°
                
                flipped_bands = _flip_bands(bands)
                _augment_and_write(flipped_bands, path_flip_name, meta, 0)  # flipped up/down
                _augment_and_write(flipped_bands, path_flip_90, meta, 1)  # flipped & 90°
                _augment_and_write(flipped_bands, path_flip_180, meta, 2)  # flipped & 180°
                _augment_and_write(flipped_bands, path_flip_270, meta, 3)  # flipped & 270°
                
                successful += 1
                
                if (i + 1) % 10 == 0:
                    print(f"Processed {i + 1}/{len(files)} tiles")
                    
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            failed += 1
            continue
    
    print(f"\n=== Augmentation Summary ===")
    print(f"Successfully processed: {successful} tiles")
    print(f"Failed: {failed} tiles")
    print(f"Total augmented tiles created: {successful * 7} (7 per input tile)")
    print(f"Total tiles after augmentation: {successful * 8} (including originals)")

if __name__ == '__main__':
    # Load configuration
    try:
        config = load_config()
    except FileNotFoundError:
        print("Error: config.json not found!")
        print("Please copy config_template.json to config.json and update the paths.")
        exit()
    
    # Get paths from configuration
    tiles_dir = get_tile_images_output_folder(config)
    output_dir = get_augment_tiles_output_folder(config)
    
    # Check if tiles directory exists
    if not os.path.exists(tiles_dir):
        print(f"Error: {tiles_dir} directory not found!")
        print("Please run tiles.py first to generate tiles.")
        exit()
    
    # Check if there are any tiles to process
    tile_files = glob.glob(os.path.join(tiles_dir, "*.tif"))
    if not tile_files:
        print(f"No .tif files found in {tiles_dir}")
        print("Please run tiles.py first to generate tiles.")
        exit()
    
    print("=== Data Augmentation Workflow ===")
    print(f"Input directory: {tiles_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Found {len(tile_files)} total tiles")
    print("Will process the first 40 tiles (or all if less than 40)")
    print("Each tile will generate 7 augmented versions:")
    print("  - 90° rotation")
    print("  - 180° rotation") 
    print("  - 270° rotation")
    print("  - Vertical flip")
    print("  - Vertical flip + 90° rotation")
    print("  - Vertical flip + 180° rotation")
    print("  - Vertical flip + 270° rotation")
    print()
    
    # Run augmentation
    augment_tiles(tiles_dir, output_dir, max_tiles=40)
    
    print("\nAugmentation complete!")
