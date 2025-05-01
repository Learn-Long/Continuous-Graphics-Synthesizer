import os
import sys
from PIL import Image
from datetime import datetime

def get_creation_time(filepath):
    """Gets the creation time of a file."""
    try:
        # Use 'st_birthtime' on macOS/BSD, 'st_ctime' on Windows (creation time)
        # 'st_mtime' is modification time, used as fallback
        if hasattr(os.stat(filepath), 'st_birthtime'):
            return os.stat(filepath).st_birthtime
        else:
            # On Windows, st_ctime is creation time
            # On Linux, st_ctime is metadata change time, use st_mtime instead
            if sys.platform == 'win32':
                return os.stat(filepath).st_ctime
            else:
                 # Fallback to modification time if creation time is unavailable
                 print(f"Warning: Creation time not available for {filepath} on this OS. Using modification time as fallback.")
                 return os.stat(filepath).st_mtime
    except Exception as e:
        print(f"Error getting creation time for {filepath}: {e}")
        # Return a very old date to sort problematic files first or last as needed
        return 0 # Or float('inf') depending on desired sorting for errors

def merge_images_vertically():
    """
    Merges images in the current directory vertically based on creation time,
    cropping newer images from the top based on a user-defined percentage.
    Handles images with different widths by centering them.
    """
    current_dir = os.getcwd()
    image_files = []
    supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')

    print(f"Scanning directory: {current_dir}")
    for filename in os.listdir(current_dir):
        if filename.lower().endswith(supported_formats) and filename != "merged_output.png":
            filepath = os.path.join(current_dir, filename)
            if os.path.isfile(filepath):
                image_files.append(filepath)

    if not image_files:
        print("No image files found in the directory.")
        return

    # Sort images by creation time (oldest first)
    try:
        image_files.sort(key=get_creation_time)
        print("\nImages found and sorted by creation time (oldest first):")
        for i, f in enumerate(image_files):
            c_time = get_creation_time(f)
            dt_object = datetime.fromtimestamp(c_time)
            print(f"{i+1}. {os.path.basename(f)} (Created: {dt_object})")
    except Exception as e:
        print(f"Error sorting image files: {e}")
        return

    # Get user input for percentage
    while True:
        try:
            percentage_str = input("\nEnter the percentage (0-100) of height to keep for newer images (0 means only the oldest image is kept fully): ")
            percentage = float(percentage_str)
            if 0 <= percentage <= 100:
                crop_ratio = percentage / 100.0
                break
            else:
                print("Percentage must be between 0 and 100.")
        except ValueError:
            print("Invalid input. Please enter a number between 0 and 100.")

    processed_images = []
    max_width = 0
    total_height = 0

    print("\nProcessing images...")
    # First pass: Determine max width and process images (open, check width, potentially pad)
    temp_images_data = [] # Store (PIL.Image, original_height) tuples
    try:
        for filepath in image_files:
            img = Image.open(filepath).convert("RGBA") # Ensure RGBA for transparency
            max_width = max(max_width, img.width)
            temp_images_data.append({'img': img, 'path': filepath}) # Store original image and path
        print(f"Maximum width determined: {max_width} pixels")

        # Second pass: Pad, crop, and calculate total height
        for i, data in enumerate(temp_images_data):
            img = data['img']
            filepath = data['path']
            original_height = img.height
            current_width = img.width

            # --- Padding ---
            if current_width < max_width:
                # Create a new transparent background
                padded_img = Image.new('RGBA', (max_width, original_height), (0, 0, 0, 0))
                # Calculate position to paste the original image centered
                paste_x = (max_width - current_width) // 2
                padded_img.paste(img, (paste_x, 0))
                img = padded_img # Use the padded image going forward
                print(f" - Padded '{os.path.basename(filepath)}' to width {max_width}")


            # --- Cropping ---
            final_height = original_height
            if i > 0: # Crop only if it's not the oldest image (index 0)
                if crop_ratio > 0:
                    crop_height = int(original_height * crop_ratio)
                    if crop_height > 0:
                        # Keep the bottom part: (left, upper, right, lower)
                        # upper = original_height - crop_height
                        img = img.crop((0, original_height - crop_height, max_width, original_height))
                        final_height = img.height # Update height after crop
                        print(f" - Cropped '{os.path.basename(filepath)}' to bottom {percentage}% height ({final_height}px)")
                    else:
                         # If crop_height is 0, effectively remove the image unless percentage is exactly 0
                         if percentage == 0:
                             final_height = 0 # Mark for exclusion
                             print(f" - Skipping '{os.path.basename(filepath)}' as percentage is 0.")
                         else: # Very small percentage resulted in 0 pixel height
                             final_height = 1 # Keep at least 1 pixel? Or skip? Let's keep 1.
                             img = img.crop((0, original_height - 1, max_width, original_height))
                             print(f" - Cropped '{os.path.basename(filepath)}' to minimum 1px height.")

                else: # crop_ratio is 0
                    final_height = 0 # Mark for exclusion
                    print(f" - Skipping '{os.path.basename(filepath)}' as percentage is 0.")


            if final_height > 0:
                processed_images.append(img)
                total_height += final_height

        if not processed_images:
             print("\nNo images left after processing/cropping. Cannot create merged image.")
             return

        print(f"\nTotal height for merged image: {total_height} pixels")

        # Create the final canvas
        merged_image = Image.new('RGBA', (max_width, total_height), (0, 0, 0, 0)) # Use RGBA

        # Paste images onto the canvas (oldest at top, newest at bottom)
        current_y = 0
        # Iterate in the original order (oldest first)
        for img in processed_images:
            merged_image.paste(img, (0, current_y), img) # Use img as mask for RGBA paste
            current_y += img.height

        # Save the final image
        output_filename = "merged_output.png"
        merged_image.save(output_filename)
        print(f"\nSuccessfully merged {len(processed_images)} images into '{output_filename}'")

    except FileNotFoundError as e:
        print(f"\nError: File not found during processing - {e}")
    except Exception as e:
        print(f"\nAn error occurred during image processing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        import PIL
        print(f"Pillow version: {PIL.__version__}")
    except ImportError:
        print("Error: Pillow library not found.")
        print("Please install it using: pip install Pillow")
        sys.exit(1)

    merge_images_vertically()
    input("\nPress Enter to exit.") # Keep console open
