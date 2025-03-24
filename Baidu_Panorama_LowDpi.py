import re, os
import json
import requests
import time, glob
import csv
import traceback


# read csv
def write_csv(filepath, data, head=None):
    if head:
        data = [head] + data
    with open(filepath, mode='w', encoding='UTF-8-sig', newline='') as f:
        writer = csv.writer(f)
        for i in data:
            writer.writerow(i)


# write csv
def read_csv(filepath):
    data = []
    if os.path.exists(filepath):
        with open(filepath, mode='r', encoding='utf-8') as f:
            lines = csv.reader(f) 
            for line in lines:
                data.append(line)
        return data
    else:
        print('filepath is wrong：{}'.format(filepath))
        return []



def grab_img_baidu(_url, _headers=None):
    if _headers == None:
        headers = {
            "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
            "Referer": "https://map.baidu.com/",
            "sec-ch-ua-mobile": "?0",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
        }
    else:
        headers = _headers
    response = requests.get(_url, headers=headers)

    if response.status_code == 200:
        print("SAVE!!")
        return response.content
    else:
        return None


def openUrl(_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
    }
    response = requests.get(_url, headers=headers)
    if response.status_code == 200:  
        return response.content
    else:
        return None


def getSId(_bdlng, _bdlat):
    # get svid of baidu streetview
    url = "https://mapsv0.bdimg.com/?qt=qsdata&x=%s&y=%s&time=201709&mode=day" % (
        str(_bdlng), str(_bdlat))
    res = openUrl(url).decode()
    temp = json.loads(res)
    try:
        temp = json.loads(res)
        sid = temp["content"]["id"]  
        #print(sid)
        return sid
    except (KeyError, json.JSONDecodeError):
        print("Error in getting svid")
        return None

def getPanoId(_sid):
    url = "https://mapsv0.bdimg.com/?qt=sdata&sid=%s&pc=1" % (
        str(_sid))
    res = openUrl(url).decode()
    temp = json.loads(res)
    
    try:
        temp = json.loads(res)
        roads = temp['content'][0]['Roads']
        #print(roads)
        pids = []
        for road in roads:
            if road.get('Panos'): 
                for pano in road['Panos']:
                    pids.append(pano['PID'])  
        #print(pids)
        return pids
    except (KeyError, json.JSONDecodeError):
        print("Error in getting panoID")
        return []


# Change wgs84 to baidu09
def wgs2bd09mc(wgs_x, wgs_y):
    # to:5/bd0911，6/BDMercator
    url = 'http://api.map.baidu.com/geoconv/v1/?coords={}+&from=1&to=6&output=json&ak={}'.format(
        wgs_x + ',' + wgs_y,
        'Your Baidu AK'     # Your Baidu AK
    )
    res = openUrl(url).decode()
    temp = json.loads(res)
    bd09mc_x = 0
    bd09mc_y = 0
    if temp['status'] == 0:
        bd09mc_x = temp['result'][0]['x']
        bd09mc_y = temp['result'][0]['y']
        #print("new coordinate: " + str(bd09mc_x) + "," + str(bd09mc_y))
    return bd09mc_x, bd09mc_y

if __name__ == "__main__":
    root = "Images_output"
    dir = "By_Low_Dpi"
    fn_dir = "Data"
    read_fn = r'converted_data.csv'     # Your File Name
    error_fn = r'error_converted_data.csv'
    filenames_exist = glob.glob1(os.path.join(root, dir), "*.png")

    data = read_csv(os.path.join(fn_dir, read_fn))
    header = data[0]
    data = data[1:]
    error_img = []
    pitchs = '0'

    count = 1
    # while count < 210:
    for i in range(len(data)):
        print('Processing No. {} point...'.format(i + 1))
        # gcj_x, gcj_y, wgs_x, wgs_y = data[i][0], data[i][1], data[i][2], data[i][3]
        wgs_x, wgs_y = data[i][15], data[i][16]
        #print("original coordinate:"+wgs_x+","+wgs_y)

        try:
            bd09mc_x, bd09mc_y = wgs2bd09mc(wgs_x, wgs_y)
        except Exception as e:
            print(str(e))
            continue
        flag = True
        flag = flag and "%s_%s_%s.png" % (wgs_x, wgs_y, pitchs) in filenames_exist

        # If file exists, skip
        if (flag):
            continue
        sid = getSId(bd09mc_x, bd09mc_y)
        pids = getPanoId(sid)
        for h in pids:
            save_fn = os.path.join(root, dir, '%s_%s_%s.png' % (wgs_x, wgs_y, pitchs))
            url = "https://mapsv0.bdimg.com/?qt=pdata&sid={}&pos=0_0&z=1&udt=20190619".format(h)
            print(url)
            img = grab_img_baidu(url)
            output_dir = os.path.join(root, dir) 

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            if img != None:
                image_path = os.path.join(output_dir, r'%s_%s_%s_%s.png' % (wgs_x, wgs_y, h, pitchs))
                with open(image_path, "wb") as f:
                    f.write(img)
                print(f"Image saved at: {image_path}")
            break

        time.sleep(6)
        count += 1
        
    if len(error_img) > 0:
        write_csv(os.path.join(root, error_fn), error_img, header)
