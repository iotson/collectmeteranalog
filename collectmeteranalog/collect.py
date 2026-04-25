from urllib.error import HTTPError, URLError
import urllib.request
import re
import requests
import os
import sys
from PIL import Image
from datetime import date, timedelta
import imagehash
import secrets
import shutil
from collectmeteranalog.labeling import label
from collectmeteranalog.utils import ziffer_data_files
import time


target_raw_path =  "data/raw_images"   # here all raw images will be stored
target_label_path = "data/labeled"
target_store_duplicates = "data/raw_images/duplicates"
target_hash_data = "data/HistoricHashData.txt"


def yesterday(daysbefore=1):
    ''' return the date of yesterday as string in format yyyymmdd'''
    yesterday = date.today() - timedelta(days=daysbefore)
    return yesterday.strftime("%Y%m%d")


def readimages(servername, output_dir, daysback=3):
    '''get all images taken within defined days back and store it in target path'''
    
    if not servername.startswith(("http://", "https://")):
        serverurl = "http://" + servername
    else:
        serverurl = servername

    from urllib.parse import urlparse
    if urlparse(serverurl).scheme not in ("http", "https"):
        raise ValueError(f"Only http/https URLs are supported: {serverurl!r}")

    print(f"Download images from {serverurl} ...")
    count = 0

    for datesbefore in range(0, daysback):
        picturedate = yesterday(daysbefore=datesbefore)

        for i in range(24):
            hour = f'{i:02d}'
            
            path = os.path.join(output_dir, servername, picturedate, hour)
            if os.path.exists(path):
                continue

            try:
                print("Download images from folder: /fileserver/log/analog/" + picturedate + "/" + hour)
                url_list = f"{serverurl}/fileserver/log/analog/{picturedate}/{hour}/"
                fp = urllib.request.urlopen(url_list)  # nosec B310 — scheme validated above
                url_list_str = fp.read().decode("utf8")
                fp.close()

            except HTTPError as h:
                print(f"{url_list} not found")
                continue
            
            except URLError as ue:
                print("URL-Error! Server not available? Requested URL was:", url_list)
                sys.exit(1)
            
            urls = re.findall(r'href=[\'"]?([^\'" >]+)', url_list_str)
            os.makedirs(path, exist_ok=True) 

            for url in urls:
                # Skip files which are not jpg
                if not url.lower().endswith(('.jpg', '.jpeg')):
                    continue

                prefix = os.path.basename(url).split('_', 1)[0]
                if (prefix == os.path.basename(url)):
                    prefix = ''
                else:
                    prefix = prefix + '_'
                
                filename = secrets.token_hex(nbytes=16) + ".jpg"
                filepath = os.path.join(path, prefix + filename)

                # Skip existing path
                if os.path.exists(filepath):
                    continue

                countrepeat = 10
                while countrepeat > 0:
                    try:
                        print(serverurl+url)
                        with requests.get(serverurl+url, stream=True, timeout=15) as response:
                            # Check for HTTP errors
                            response.raise_for_status()

                            content_type = response.headers.get("Content-Type", "")

                            if content_type == "image/jpeg":
                                # Save directly without re-encoding
                                with open(filepath, "wb") as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        f.write(chunk)
                            else:
                                # Re-encode to JPEG
                                img = Image.open(response.raw)
                                img = img.convert("RGB")  # ensures JPEG compatibility
                                img.save(filepath, format="JPEG", quality=100)

                            count += 1
                            break
                
                    except requests.exceptions.Timeout:
                        print(filepath + " timed out - Retrying in 10 s ... | (%d)..." % (countrepeat - 1))
                        countrepeat -= 1
                        time.sleep(10)
                        continue

                    except (requests.exceptions.RequestException, OSError) as e:
                        print(filepath + f" failed to load: {e}")
                        break

                    except Exception as e:
                        print(filepath + f" unexpected error: {e}")
                        break

    print(f"{count} images downloaded from {servername}")


def save_hash_file(images, hashfilename):
    with open(hashfilename, 'w', encoding='utf-8') as f:
        for img_hash, img, meter, today in images:
            s_meter = meter.replace("\t", " ")
            s_img = img.replace("\t", " ")
            f.write(f"{today}\t{s_meter}\t{s_img}\t{img_hash}\n")


def load_hash_file(hashfilename):
    images = []

    try:
        with open(hashfilename, 'r') as f:
            lines = f.readlines()
    except OSError as e:
        print(f'No historic hash data could be loaded ({hashfilename}): {e}')
        return images

    for line in lines:
        cut = line.strip('\n').split(sep="\t")
        today = cut[0]
        meter = cut[1]
        _hash = imagehash.hex_to_hash(cut[3])
        images.append([_hash, cut[2], meter, today])
    return images


_HASH_IMAGE_SIZE = (32, 20)


def remove_similar_images(path, image_filenames, meter, similarbits=2, hashfunc=imagehash.average_hash, saveduplicates=False):
    """Remove similar or duplicate images, persisting hash history across runs."""
    print(f"Find similar images now in {len(image_filenames)} images ...")

    today = date.today().strftime("%Y-%m-%d")
    images = []
    for img in sorted(image_filenames):
        try:
            img_hash = hashfunc(Image.open(img).convert('L').resize(_HASH_IMAGE_SIZE))
        except OSError as e:
            print(f'Problem: {e} with {img}')
            continue
        images.append([img_hash, img, meter, today])

    hash_file = os.path.join(path, target_hash_data)
    historic_hashes = load_hash_file(hash_file) if os.path.exists(hash_file) else []

    duplicates = set()
    for entry in images:
        img_hash, img_path = entry[0], entry[1]
        if img_path in duplicates:
            continue
        # Check against historic hashes first
        similar_historic = [h for h in historic_hashes if abs(h[0] - img_hash) < similarbits and h[1] != img_path]
        if similar_historic:
            duplicates.add(img_path)
        else:
            # Check against new images
            similar_new = [h for h in images if abs(h[0] - img_hash) < similarbits and h[1] != img_path]
            if similar_new:
                duplicates |= {row[1] for row in similar_new}

    # Persist unique images into historic hash data
    for entry in images:
        if entry[1] not in duplicates:
            historic_hashes.append(entry)

    # Retention policy: keep only entries from the last 30 days
    cutoff = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    historic_hashes = [h for h in historic_hashes if h[3] >= cutoff]

    save_hash_file(historic_hashes, hash_file)

    # Remove or relocate duplicates
    if saveduplicates:
        duplicates_dir = os.path.join(path, target_store_duplicates)
        os.makedirs(duplicates_dir, exist_ok=True)
        for image in duplicates:
            os.replace(image, os.path.join(duplicates_dir, os.path.basename(image)))
        print(f"{len(duplicates)} duplicates will moved to .../raw_images/duplicates.")
    else:
        for image in duplicates:
            os.remove(image)
        print(f"{len(duplicates)} duplicates will be removed.")


def move_to_label(path, keepolddata, files):
    
    label_dir = os.path.join(path, target_label_path)
    os.makedirs(label_dir, exist_ok=True)
    if keepolddata:
        print("Copy files to folder 'labeled', keep source folder 'raw_images'")
        for file in files:
            shutil.copy(file, os.path.join(label_dir, os.path.basename(file)))
    else:
        print("Move files to folder 'labeled' and cleanup source folder 'raw_images'")
        for file in files:
            os.replace(file, os.path.join(label_dir, os.path.basename(file)))

        shutil.rmtree(os.path.join(path, target_raw_path))


def collect(meter, path, days, keepolddata=False, download=True, startlabel=0, saveduplicates=False, ticksteps=1, similarbits=2):
    # ensure the target path exists
    os.makedirs(os.path.join(path, target_raw_path), exist_ok=True)

    # read all images from meters
    if download:
        print("Download images")
        readimages(meter, os.path.join(path, target_raw_path), days)
    
    meter_raw_path = os.path.join(path, target_raw_path, meter)

    # remove all same or similar images and remove the empty folders
    remove_similar_images(path, ziffer_data_files(meter_raw_path),
                          meter, saveduplicates=saveduplicates, similarbits=similarbits)

    # move or copy the files in one zip without directory structure and optional cleanup source
    move_to_label(path, keepolddata, ziffer_data_files(meter_raw_path))

    # label images
    label(os.path.join(path, target_label_path), startlabel=startlabel, ticksteps=ticksteps)
