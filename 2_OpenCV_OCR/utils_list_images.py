import os

def list_images_in_folder(folder_path):
    """Return list of all image file paths in a folder."""
    supported_ext = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    return [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(supported_ext)]
import os

def list_images_recursively(folder_path):
    """
    Return a list of all image file paths in a folder (including subfolders).
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    supported_ext = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
    image_paths = []

    for root, _, files in os.walk(folder_path):
        for f in files:
            if f.lower().endswith(supported_ext):
                image_paths.append(os.path.join(root, f))

    return image_paths
