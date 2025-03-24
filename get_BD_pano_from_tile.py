import math
import os
import time
import requests
import json
from io import BytesIO
from PIL import Image
import numpy as np

# Constants for coordinate conversion
x_pi = 3.14159265358979324 * 3000.0 / 180.0
pi = 3.1415926535897932384626
a = 6378245.0  # Semi-major axis
ee = 0.00669342162296594323  # Flattening

# Correction matrices for BD09 Mercator projection
LLBAND = [75, 60, 45, 30, 15, 0]
LL2MC = [
    [-0.0015702102444, 111320.7020616939, 1704480524535203, -10338987376042340, 26112667856603880, -35149669176653700,
     26595700718403920, -10725012454188240, 1800819912950474, 82.5],
    [0.0008277824516172526, 111320.7020463578, 647795574.6671607, -4082003173.641316, 10774905663.51142,
     -15171875531.51559, 12053065338.62167, -5124939663.577472, 913311935.9512032, 67.5],
    [0.00337398766765, 111320.7020202162, 4481351.045890365, -23393751.19931662, 79682215.47186455, -115964993.2797253,
     97236711.15602145, -43661946.33752821, 8477230.501135234, 52.5],
    [0.00220636496208, 111320.7020209128, 51751.86112841131, 3796837.749470245, 992013.7397791013, -1221952.21711287,
     1340652.697009075, -620943.6990984312, 144416.9293806241, 37.5],
    [-0.0003441963504368392, 111320.7020576856, 278.2353980772752, 2485758.690035394, 6070.750963243378,
     54821.18345352118, 9540.606633304236, -2710.55326746645, 1405.483844121726, 22.5],
    [-0.0003218135878613132, 111320.7020701615, 0.00369383431289, 823725.6402795718, 0.46104986909093,
     2351.343141331292, 1.58060784298199, 8.77738589078284, 0.37238884252424, 7.45]]
MCBAND = [12890594.86, 8362377.87, 5591021, 3481989.83, 1678043.12, 0]
MC2LL = [[1.410526172116255e-8, 0.00000898305509648872, -1.9939833816331, 200.9824383106796, -187.2403703815547,
          91.6087516669843, -23.38765649603339, 2.57121317296198, -0.03801003308653, 17337981.2],
         [-7.435856389565537e-9, 0.000008983055097726239, -0.78625201886289, 96.32687599759846, -1.85204757529826,
          -59.36935905485877, 47.40033549296737, -16.50741931063887, 2.28786674699375, 10260144.86],
         [-3.030883460898826e-8, 0.00000898305509983578, 0.30071316287616, 59.74293618442277, 7.357984074871,
          -25.38371002664745, 13.45380521110908, -3.29883767235584, 0.32710905363475, 6856817.37],
         [-1.981981304930552e-8, 0.000008983055099779535, 0.03278182852591, 40.31678527705744, 0.65659298677277,
          -4.44255534477492, 0.85341911805263, 0.12923347998204, -0.04625736007561, 4482777.06],
         [3.09191371068437e-9, 0.000008983055096812155, 0.00006995724062, 23.10934304144901, -0.00023663490511,
          -0.6321817810242, -0.00663494467273, 0.03430082397953, -0.00466043876332, 2555164.4],
         [2.890871144776878e-9, 0.000008983055095805407, -3.068298e-8, 7.47137025468032, -0.00000353937994,
          -0.02145144861037, -0.00001234426596, 0.00010322952773, -0.00000323890364, 826088.5]]


def gcj02tobd09(lng, lat):
    z = math.sqrt(lng * lng + lat * lat) + 0.00002 * math.sin(lat * x_pi)
    theta = math.atan2(lat, lng) + 0.000003 * math.cos(lng * x_pi)
    bd_lng = z * math.cos(theta) + 0.0065
    bd_lat = z * math.sin(theta) + 0.006
    return [bd_lng, bd_lat]

def bd09togcj02(bd_lon, bd_lat):
    x = bd_lon - 0.0065
    y = bd_lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * x_pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * x_pi)
    gg_lng = z * math.cos(theta)
    gg_lat = z * math.sin(theta)
    return [gg_lng, gg_lat]

def wgs84togcj02(lng, lat):
    if out_of_china(lng, lat):  # 判断是否在国内
        return lng, lat
    dlat = transformlat(lng - 105.0, lat - 35.0)
    dlng = transformlng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * pi)
    mglat = lat + dlat
    mglng = lng + dlng
    return [mglng, mglat]

def gcj02towgs84(lng, lat):
    if out_of_china(lng, lat):
        return lng, lat
    dlat = transformlat(lng - 105.0, lat - 35.0)
    dlng = transformlng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * pi)
    mglat = lat + dlat
    mglng = lng + dlng
    return [lng * 2 - mglng, lat * 2 - mglat]

def transformlat(lng, lat):
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 * math.sin(2.0 * lng * pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * pi) + 40.0 * math.sin(lat / 3.0 * pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * pi) + 320 *math.sin(lat * pi / 30.0)) * 2.0 / 3.0
    return ret

def transformlng(lng, lat):
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 * math.sin(2.0 * lng * pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * pi) + 40.0 * math.sin(lng / 3.0 * pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * pi) + 300.0 * math.sin(lng / 30.0 * pi)) * 2.0 / 3.0
    return ret

def out_of_china(lng, lat):
    if lng < 72.004 or lng > 137.8347:
        return True
    if lat < 0.8293 or lat > 55.8271:
        return True
    return False

def wgs84tomercator(lng, lat):
    x = lng * 20037508.34 / 180
    y = math.log(math.tan((90 + lat) * math.pi / 360)) / (math.pi / 180) * 20037508.34 / 180
    return x, y

def mercatortowgs84(x, y):
    lng = x / 20037508.34 * 180
    lat = 180 / math.pi * (2 * math.atan(math.exp(y / 20037508.34 * 180 * math.pi / 180)) - math.pi / 2)
    return lng, lat

def getRange(cC, cB, T):
    if cB is not None:
        cC = max(cC, cB)
    if T is not None:
        cC = min(cC, T)
    return cC

def getLoop(cC, cB, T):
    while cC > T:
        cC -= T - cB
    while cC < cB:
        cC += T - cB
    return cC

def convertor(cC, cD):
    if (cC == None or cD == None):
        print('null')
        return None
    T = cD[0] + cD[1] * abs(cC.x)
    cB = abs(cC.y) / cD[9]
    cE = cD[2] + cD[3] * cB + cD[4] * cB * cB + cD[5] * cB * cB * cB + cD[6] * cB * cB * cB * cB + cD[
        7] * cB * cB * cB * cB * cB + cD[8] * cB * cB * cB * cB * cB * cB
    if (cC.x < 0):
        T = T * -1
    else:
        T = T
    if (cC.y < 0):
        cE = cE * -1
    else:
        cE = cE
    return [T, cE]

def convertLL2MC(T):
    cD = None
    T.x = getLoop(T.x, -180, 180)
    T.y = getRange(T.y, -74, 74)
    cB = T
    for cC in range(0, len(LLBAND), 1):
        if (cB.y >= LLBAND[cC]):
            cD = LL2MC[cC]
            break
    if (cD != None):
        for cC in range(len(LLBAND) - 1, -1, -1):
            if (cB.y <= -LLBAND[cC]):
                cD = LL2MC[cC]
                break
    cE = convertor(T, cD)
    return cE

def convertMC2LL(cB):
    cC = LLT(abs(cB.x), abs(cB.y))
    cE = None
    for cD in range(0, len(MCBAND), 1):
        if (cC.y >= MCBAND[cD]):
            cE = MC2LL[cD]
            break
    T = convertor(cB, cE)
    return T

def bd09tomercator(lng, lat):
    return convertLL2MC(LLT(lng, lat))

def mercatortobd09(x, y):
    return convertMC2LL(LLT(x, y))

class LLT:
    def __init__(self, x, y):
        self.x = x
        self.y = y

def getResolution(level):
    return 2 ** (level - 18)

def getResolutionLat(lat, level):
    return 2 ** (18 - level) * math.cos(lat)

def lngToTileX(lng, level):
    return math.floor(bd09tomercator(lng, 0)[0] * getResolution(level) / 256)

def latToTileY(lat, level):
    return math.floor(bd09tomercator(0, lat)[1] * getResolution(level) / 256)

def lnglatToTile(lng, lat, level):
    return lngToTileX(lng, level), latToTileY(lat, level)

def lngToPixelX(lng, level):
    tileX = lngToTileX(lng, level)
    return math.floor(bd09tomercator(lng, 0)[0] * getResolution(level) - tileX * 256)

def latToPixelY(lat, level):
    tileY = latToTileY(lat, level)
    return math.floor(bd09tomercator(0, lat)[1] * getResolution(level) - tileY * 256)

def lnglatToPixel(lng, lat, level):
    return lngToPixelX(lng, level), latToPixelY(lat, level)

def pixelXToLng(pixelX, tileX, level):
    return mercatortobd09((tileX * 256 + pixelX) / getResolution(level), 0)[0]

def pixelYToLat(pixelY, tileY, level):
    return mercatortobd09(0, (tileY * 256 + pixelY) / getResolution(level))[1]

def pixelToLnglat(pixelX, pixelY, tileX, tileY, level):
    return mercatortobd09((tileX * 256 + pixelX) / getResolution(level), (tileY * 256 + pixelY) / getResolution(level))

def wgs2bd09mc(wgs_x, wgs_y, ak):
    url = f'http://api.map.baidu.com/geoconv/v1/?coords={wgs_x},{wgs_y}&from=1&to=6&output=json&ak={ak}'
    response = requests.get(url)
    temp = json.loads(response.text)
    if temp['status'] == 0:
        return temp['result'][0]['x'], temp['result'][0]['y']

def get_baidu_sid(lng, lat):
    url = f"https://mapsv0.bdimg.com/?qt=qsdata&x={lng}&y={lat}&time=201709&mode=day"
    response = requests.get(url).content.decode()
    try:
        sid = json.loads(response)["content"]["id"]
        return sid
    except:
        print("Failed to retrieve SID")
        return None

def get_baidu_pano(wgs_x, wgs_y, bd09mc_x, bd09mc_y):
    root = "Images_output"
    dir = "By_Tile"
    slices_dir = os.path.join(root, dir, "Slices") 
    rows_dir = os.path.join(root, dir, "Rows")   
    final_dir = os.path.join(root, dir, "Final")  

    os.makedirs(slices_dir, exist_ok=True)
    os.makedirs(rows_dir, exist_ok=True)
    os.makedirs(final_dir, exist_ok=True)

    sid = get_baidu_sid(bd09mc_x, bd09mc_y)
    if sid == None:
        return None
    if check_SID(sid) == 0:
        print("    Already fetched! Continue......")
        return None

    row1_paths = [] 
    row2_paths = []  
    for row in [1, 2]:
        for col in range(0, 8): 
            url = f"https://mapsv0.bdimg.com/?qt=pdata&sid={sid}&pos={row}_{col}&z=4"
            img_data = grab_img_baidu(url)

            if img_data:
                img_byte_arr = BytesIO()
                img_data.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()

                save_path = os.path.join(slices_dir, f"{wgs_x}_{wgs_y}_{sid}_{row}_{col}.png")
                with open(save_path, "wb") as f:
                    f.write(img_byte_arr) 

                print(f"    Image saved: {save_path}")

                if row == 1:
                    row1_paths.append(save_path)
                else:
                    row2_paths.append(save_path)

    if len(row1_paths) == 8 and len(row2_paths) == 8:
        row1_merged = os.path.join(rows_dir, f"{wgs_x}_{wgs_y}_{sid}_row1.png")
        row2_merged = os.path.join(rows_dir, f"{wgs_x}_{wgs_y}_{sid}_row2.png")

        merge_images_horizontally(row1_paths, row1_merged)
        merge_images_horizontally(row2_paths, row2_merged)

        final_image_path = os.path.join(final_dir, f"{wgs_x}_{wgs_y}_{sid}_final.png")
        merge_images_vertically(row1_merged, row2_merged, final_image_path)

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
    print(f"    Row merged: {save_path}")
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
    print(f"    Final image merged: {final_save_path}")

def grab_img_baidu(url):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        img = Image.open(BytesIO(response.content)) 
        return img
    else:
        print("     Error in Downloading Baidu images")
        return None

def convert_to_tiff(img, tileX, tileY, scale, output_dir="Tiles_output"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    tiff_filename = f"{tileX}_{tileY}_{scale}.tiff"
    tiff_path = os.path.join(output_dir, tiff_filename)

    img = img.convert("RGB")
    img.save(tiff_path, format="TIFF")
    print(f"    Tile saved at: {tiff_path}")    
    return tiff_path


def load_existing_panoids(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return set(file.read().splitlines()) 
    return set()

def save_panoid(file_path, panoid):
    with open(file_path, 'a') as file:
        file.write(f"{panoid}\n")

def find_blue_pixels(img):
    img = img.convert("RGB")
    img_array = np.array(img) 

    blue_channel = img_array[:, :, 2]

    blue_pixels = np.argwhere(blue_channel > 100)

    return blue_pixels

def calculate_distance(p1, p2):
    return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

def filter_close_points(blue_pixels, min_distance=10):
    filtered_pixels = []
    for pixel in blue_pixels:
        if all(calculate_distance(pixel, p) > min_distance for p in filtered_pixels):
            filtered_pixels.append(pixel)
    return filtered_pixels

def check_SID(sid):
    panoid_file = "panoids.txt"
    existing_panoids = load_existing_panoids(panoid_file)

    new_panoid = sid
    if new_panoid not in existing_panoids:
        save_panoid(panoid_file, new_panoid)
        return 1
    else:
        return 0

def get_pano_by_tiles(tileX, tileY, scale, ak):  
    url = f"https://mapsv0.bdimg.com/tile/?udt=20200825&qt=tile&styles=pl&x={tileX}&y={tileY}&z={scale}"

    img = grab_img_baidu(url)
    if img is None:
        return
    tiff_path = convert_to_tiff(img, tileX, tileY, scale)

    blue_pixel_coords = find_blue_pixels(img)
    if len(blue_pixel_coords) <= 0 :
        return
    print(f"    Detected {len(blue_pixel_coords)} blue pixels.")

    filtered_coords = filter_close_points(blue_pixel_coords, min_distance=getResolution(scale)*35)
    if len(filtered_coords) <= 0 :
        return
    print(f"    After filtering, {len(filtered_coords)} blue pixels remained.")

    for i, (pixelY, pixelX) in enumerate(filtered_coords):
            wgs_lng, wgs_lat = pixelToLnglat(pixelX, pixelY, tileX, tileY, scale)
            bd09mc_lng, bd09mc_lat = wgs2bd09mc(wgs_lng, wgs_lat, ak)
            print(f"    Blue pixel No. {i + 1}:  pixel position: (x={pixelX}, y={pixelY}) -> WGS84: (lng={wgs_lng}, lat={wgs_lat})")
            get_baidu_pano(wgs_lng, wgs_lat, bd09mc_lng, bd09mc_lat)
            time.sleep(3)

def get_tile_range(first_lng, first_lat, end_lng, end_lat, level):
    tileX1, tileY1 = lnglatToTile(first_lng, first_lat, level)
    tileX2, tileY2 = lnglatToTile(end_lng, end_lat, level)

    x_range = range(min(tileX1, tileX2), max(tileX1, tileX2) + 1)
    y_range = range(min(tileY1, tileY2), max(tileY1, tileY2) + 1)

    tile_coordinates = [(x, y) for x in x_range for y in y_range]
    return tile_coordinates

if __name__ == "__main__":
    ak = "Your Baidu AK"  # Your API Key
    first_lng, first_lat = 120.63036,31.384998    # Top-left corner coordinates
    end_lng, end_lat = 120.644374,31.379819      # Bottom-right corner coordinates
    level = 19
    tiles = get_tile_range(first_lng, first_lat, end_lng, end_lat, level)
    print("Tile numbers: " + str(len(tiles)))
    j = len(tiles)
    i = 0
    for tile in tiles:
        i += 1
        j -= 1
        get_pano_by_tiles(tile[0], tile[1], level, ak)
        print(f"    Processing Tile No. {i}，{j} remaining")

