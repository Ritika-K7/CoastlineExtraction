"""
Georeference Script

This script aligns a set of satellite images to a reference base image using spatial correction.
It is useful when images are slightly misaligned after reprojection.

Main Features:
- Uses the AROSICS library for fine-tuning image alignment (coregistration)
- Works with already aligned images and applies small adjustments if needed
- Automatically saves the output to a results folder

Inputs:
- Base Image: A well-aligned reference image (e.g., ground truth coastline)
- Target Images: Satellite images to be aligned (from aligned_data/)

Outputs:
- Georeferenced images saved in results_georeference/ folder
"""


# Input :
# Base Image :9-5-2016_Ortho_4Band_NDWI_3.125m.tif(from config)
# Target Image for Geo reference  : aligned_data
# Output : results_georeference 


import os
import shutil
from arosics import COREG
import glob
import rasterio
import sys

# Add parent directory to path to import load_config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from load_config import load_config, get_ground_truth_path, get_aligned_data_folder, get_georeference_output_folder

def check_image_extent(image_path):
    """Check the spatial extent of an image"""
    try:
        with rasterio.open(image_path) as src:
            bounds = src.bounds
            print(f"Image: {os.path.basename(image_path)}")
            print(f"  Bounds: {bounds}")
            print(f"  Width: {src.width}, Height: {src.height}")
            print(f"  CRS: {src.crs}")
            return bounds
    except Exception as e:
        print(f"Error reading {image_path}: {e}")
        return None

def georeference(base_image, target_image, outfile=None, wp=None, ws=None, force=False, output_dir=None):
    # Check if files exist
    if not os.path.isfile(base_image):
        raise FileNotFoundError(f"Base image not found: {base_image}")
    if not os.path.isfile(target_image):
        raise FileNotFoundError(f"Target image not found: {target_image}")

    # Use provided output directory or get from configuration
    if output_dir:
        results_dir = output_dir
    else:
        config = load_config()
        results_dir = get_georeference_output_folder(config)
    os.makedirs(results_dir, exist_ok=True)

    target_filename = os.path.basename(target_image)

    # Specify correct output filepath
    if outfile:
        path_out = os.path.join(results_dir, outfile)
    else:
        out_name = target_filename.split(sep=".")[0] + "_GeoRegistered.tif"
        path_out = os.path.join(results_dir, out_name)

    # Use Deering Airstrip coordinates for coregistration
    try:
        print(f"Aligning {target_filename} using Deering Airstrip reference...")
        
        # Coregister imagery using airstrip coordinates
        CR = COREG(base_image, target_image, 
                   wp=(600578.602641986, 7328849.357436092),  # Airstrip center
                   ws=(965, 1089.7365),  # Airstrip area
                   path_out=path_out,
                   max_shift=10,  # Allow larger shifts for rotated/tiled images
                   window_size=(256, 256),  # Larger window to capture airstrip features
                   grid_res=100,  # Coarser grid for initial alignment
                   min_corr=0.2)  # Lower correlation threshold for airport features
        
        print(f"Calculating spatial shifts for {target_filename}...")
        CR.calculate_spatial_shifts()
        
        # Check if any significant shifts were detected
        shifts = CR.shifts
        if shifts and any(abs(shift) > 0.1 for shift in shifts.values()):
            print(f"Significant shifts detected: {shifts}")
            print(f"Correcting shifts for {target_filename}...")
            CR.correct_shifts()
            print(f'Successfully saved airport-aligned image as {path_out}')
        else:
            print(f"No significant shifts detected for {target_filename}. Image already well-aligned.")
            # Copy the original aligned image to results if no correction needed
            shutil.copy2(target_image, path_out)
            print(f'Copied original aligned image to {path_out}')
        
        return path_out
        
    except Exception as e:
        print(f"Error during airport-based alignment {target_filename}: {str(e)}")
        
        if not force:
            print(f"Since images are pre-aligned, copying original to results: {path_out}")
            shutil.copy2(target_image, path_out)
            return path_out
        else:
            # Try with even more aggressive parameters if force=True
            try:
                print(f"Retrying with aggressive parameters for {target_filename}...")
                CR = COREG(base_image, target_image, 
                          wp=(600578.602641986, 7328849.357436092),  # Airstrip center
                          ws=(500, 500),  # Smaller window
                          path_out=path_out,
                          max_shift=20,  # Allow even larger shifts
                          window_size=(128, 128),  # Very small windows
                          grid_res=50,  # Very fine grid
                          min_corr=0.1)  # Very low correlation threshold
                
                CR.calculate_spatial_shifts()
                CR.correct_shifts()
                
                print(f'Successfully saved Georegistered image as {path_out}')
                return path_out
                
            except Exception as e2:
                print(f"All attempts failed for {target_filename}: {str(e2)}")
                raise e2





if __name__ == "__main__":
    # Load configuration
    config = load_config()
    
    # Get base image from ground truth files (NDWI image)
    base_img = get_ground_truth_path(config, 4)  # Index 4 for 9-5-2016_Ortho_4Band_NDWI_3.125m.tif
    
    # Path to aligned data folder from config
    aligned_data_dir = get_aligned_data_folder(config)
    
    # Path to georeference output folder from config
    output_dir = get_georeference_output_folder(config)
    
    print("=== Airport-Based Georeferencing Workflow ===")
    print("Using Deering Airstrip as reference point for alignment")
    print("This approach is effective for rotated or tiled images")
    print(f"Output directory: {output_dir}")
    print()
    
    # Check if base image exists
    if not os.path.exists(base_img):
        print(f"Error: Base image not found: {base_img}")
        print("Please ensure the ground truth files are properly configured.")
        sys.exit(1)
    
    # Check if aligned data directory exists
    if not os.path.exists(aligned_data_dir):
        print(f"Error: Aligned data directory not found: {aligned_data_dir}")
        print("Please run batch_align.py first to create aligned images.")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory created/verified: {output_dir}")
    
    # Check base image extent
    print("=== Base Image Information ===")
    check_image_extent(base_img)
    
    # Get all .tif files in the aligned data folder
    target_images = glob.glob(os.path.join(aligned_data_dir, "*.tif"))
    print(f"\nFound {len(target_images)} images to align using airport reference")
    
    # Check first few target images for debugging
    print("\n=== Sample Target Images Information ===")
    for target_img in target_images[:3]:  # Check first 3 images
        check_image_extent(target_img)
        print()
    
    print("=== Starting Airport-Based Alignment Process ===")
    successful = 0
    failed = 0
    
    for target_img in target_images:
        print(f"\nProcessing: {os.path.basename(target_img)}")
        try:
            output = georeference(base_img, target_img, force=False, output_dir=output_dir)  # Use force=False for gentle approach
            print("Airport alignment complete. Output:", output)
            successful += 1
        except Exception as e:
            print("Error during airport alignment:", e)
            failed += 1
            continue  # Continue with next image instead of stopping
    
    print(f"\n=== Summary ===")
    print(f"Successfully aligned: {successful}")
    print(f"Failed: {failed}")
    print(f"Total images: {len(target_images)}")
    print(f"Results saved to: {output_dir}")



# Note : reprojected the base image using the command-       
# base_img = r"C:\Users\91730\Desktop\Plante_Sentinal_Fusion_Exp\2016_HiRes_Final_Coastline_UTM3N.tif"     

# gdalinfo 2016_HiRes_Final_Coastline_UTM3N.tif
# gdalinfo "C:\Users\91730\Desktop\Plante_Sentinal_Fusion_Exp\sample_data\369619_2018-06-15_RE1_3A_Analytic_SR_clip.tif"