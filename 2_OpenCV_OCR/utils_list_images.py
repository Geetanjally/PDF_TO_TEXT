import os

def list_images_in_folder(folder_path):
    """Return list of all image file paths in a folder."""
    supported_ext = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    return [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(supported_ext)]
