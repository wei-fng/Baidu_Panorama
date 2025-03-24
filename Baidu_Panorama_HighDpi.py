import os
import time
import glob
import json
import requests
import csv
from PIL import Image
from io import BytesIO

def read_csv(filepath):
    data = []
    if os.path.exists(filepath):
        with open(filepath, mode='r', encoding='utf-8') as f:
            lines = csv.reader(f)
            for line in lines:
                data.append(line)
        return data
    else:
        print(f'File path error: {filepath}')
        return []

def grab_img_baidu(url):
    headers = {
        "Referer": "https://map.baidu.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.content
    return None

def getSId(bd09mc_x, bd09mc_y):
    url = f"https://mapsv0.bdimg.com/?qt=qsdata&x={bd09mc_x}&y={bd09mc_y}&time=201709&mode=day"
    response = requests.get(url).content.decode()
    try:
        sid = json.loads(response)["content"]["id"]
        return sid
    except:
        print("Failed to retrieve SID")
        return None

# Convert WGS84 coordinates to BD09MC
def wgs2bd09mc(wgs_x, wgs_y, bd_AK):
    url = f"http://api.map.baidu.com/geoconv/v1/?coords={wgs_x},{wgs_y}&from=1&to=6&output=json&ak={bd_AK}"
    response = requests.get(url).content.decode()
    try:
        result = json.loads(response)
        if result['status'] == 0:
            return result['result'][0]['x'], result['result'][0]['y']
    except:
        print("Coordinate conversion failed")
        return None, None

def merge_images_horizontally(image_paths, save_path):
    images = [Image.open(img) for img in image_paths]
    widths, heights = zip(*(img.size for img in images))
    total_width = sum(widths)
    max_height = max(heights)

    merged_image = Image.new('RGB', (total_width, max_height))
    
    x_offset = 0
    for img in images:
        merged_image.paste(img, (x_offset, 0))
        x_offset += img.size[0]

    merged_image.save(save_path)
    print(f"Row merged: {save_path}")
    return save_path 

def merge_images_vertically(image1_path, image2_path, final_save_path):
    img1 = Image.open(image1_path)
    img2 = Image.open(image2_path)

    total_width = max(img1.width, img2.width)
    total_height = img1.height + img2.height

    merged_image = Image.new('RGB', (total_width, total_height))
    merged_image.paste(img1, (0, 0))
    merged_image.paste(img2, (0, img1.height))

    merged_image.save(final_save_path)
    print(f"Final image merged: {final_save_path}")

if __name__ == "__main__":
    root = "Images_output"
    dir = "By_High_Dpi"
    fn_dir = "Data"
    read_fn = r'converted_data.csv'     # Your File Name
    
    slices_dir = os.path.join(root, dir, "Slices") 
    rows_dir = os.path.join(root, dir, "Rows")   
    final_dir = os.path.join(root, dir, "Final")  

    os.makedirs(slices_dir, exist_ok=True)
    os.makedirs(rows_dir, exist_ok=True)
    os.makedirs(final_dir, exist_ok=True)

    filenames_exist = glob.glob1(slices_dir, "*.png")

    data = read_csv(os.path.join(fn_dir, read_fn))
    header = data[0]
    data = data[1:]

    processed_sids = set()

    for i, row in enumerate(data):
        print(f'Processing point {i + 1}...')
        wgs_x, wgs_y = row[15], row[16]             # Indexes of coordinates in csv
        bd_AK = "Your Baidu AK"          # Your Baidu AK
        bd09mc_x, bd09mc_y = wgs2bd09mc(wgs_x, wgs_y, bd_AK)
        if bd09mc_x is None or bd09mc_y is None:
            continue

        sid = getSId(bd09mc_x, bd09mc_y)
        if not sid or sid in processed_sids:
            continue

        processed_sids.add(sid)

        row1_paths = [] 
        row2_paths = []  
        for row in [1, 2]:
            for col in range(0, 8): 
                url = f"https://mapsv0.bdimg.com/?qt=pdata&sid={sid}&pos={row}_{col}&z=4"
                img_data = grab_img_baidu(url)

                if img_data:
                    save_path = os.path.join(slices_dir, f"{wgs_x}_{wgs_y}_{sid}_{row}_{col}.png")
                    with open(save_path, "wb") as f:
                        f.write(img_data)
                    print(f"Image saved: {save_path}")

                    if row == 1:
                        row1_paths.append(save_path)
                    else:
                        row2_paths.append(save_path)

        # Ensure all 4 images per row are downloaded before merging
        if len(row1_paths) == 8 and len(row2_paths) == 8:
            row1_merged = os.path.join(rows_dir, f"{wgs_x}_{wgs_y}_{sid}_row1.png")
            row2_merged = os.path.join(rows_dir, f"{wgs_x}_{wgs_y}_{sid}_row2.png")

            merge_images_horizontally(row1_paths, row1_merged)
            merge_images_horizontally(row2_paths, row2_merged)

            final_image_path = os.path.join(final_dir, f"{wgs_x}_{wgs_y}_{sid}_final.png")
            merge_images_vertically(row1_merged, row2_merged, final_image_path)

        time.sleep(6)
