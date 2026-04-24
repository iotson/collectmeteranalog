import os


def ziffer_data_files(input_dir):
    """Return a sorted list of all .jpg images found recursively in input_dir."""
    imgfiles = []
    for root, _dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".jpg"):
                imgfiles.append(os.path.join(root, file))
    return sorted(imgfiles, key=lambda x: os.path.basename(x))
