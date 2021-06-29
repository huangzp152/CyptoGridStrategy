import pandas as pd
import requests
from queue import Queue,Empty
from time import time,sleep
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread
from urllib import parse
import hmac
import hashlib
import os

data_path = "https://api.binance.com/sapi/v1/downloadLink"

key = "IFOhCu9dRcWVuu8qd3GqoZRiDAvsOjCNEyJzVJuUyG2RL4fzGvRbvitbrGkj5ZdT"
secret = "IFOhCu9dRcWVuu8qd3GqoZRiDAvsOjCNEyJzVJuUyG2RL4fzGvRbvitbrGkj5ZdT"

def sign(params:dict,secret:str):
    query = parse.urlencode(sorted(params.items()))
    secret = secret.encode()
    signature = hmac.new(secret, query.encode("utf-8"), hashlib.sha256).hexdigest()
    return signature

def query_path(path, params):
    timestamp = int(time()*1000)
    params["timestamp"] = timestamp
    query = parse.urlencode(sorted(params.items()))
    signature = sign(params, secret)
    query += "&signature={}".format(signature)
    query_path = path + '?' + query
    return query_path

def request_get(path, headers):
    response = requests.request('GET', path, headers=headers)
    return response

def get_download_url(link_id, data_path, headers):
    params = {
        'downloadId':str(link_id)
        }
    url = query_path(data_path, params)
    ret = request_get(url, headers=headers)
    link = ret.json()['link']
    if not link.startswith('https'):
        link = None
    return link

def download(item):
    filename, url = item
    data = requests.get(url)
    file_path = '/home/data/' + filename + '.tar.gz'   #下载的文件存放路径
    with open(file_path,'wb') as fp:
        fp.write(data.content)
    return f'{filename} download is finished.'

def get_exists_files():
    for _, _, files in os.walk('/home/data'):  #下载的文件存放路径文件夹
        pre_filenames = [os.path.splitext(os.path.splitext(filename)[0])[0] for filename in files]
        return pre_filenames



def master(csv_file, q_list, data_path, headers):
    count = 0
    used_ids = set()
    while True:
        pre_filenames = get_exists_files()
        pre_length = len(used_ids)
        df = pd.read_csv(csv_file)
        symbol_list = df['symbol'].values
        type_list = df['dataType'].values
        id_list = df['id'].values
        start_list = df['start'].values
        data_list = zip(symbol_list,type_list,id_list,start_list)
        for symbol,data_type, id_value, start_time in data_list:
            filename = symbol + '_' + data_type + '_' + start_time
            if filename not in pre_filenames:
                link = get_download_url(id_value, data_path, headers)
                if link is not None:
                    used_ids.add(id_value)
                    print('filename',filename)
                    q_list.put((filename, link))
        if len(used_ids) == pre_length:
            count += 1
        if count >= 5:
            q_list.put((None,None))
            break
        sleep(1800)

def worker(q_list):
    print('worker')
    links = []
    flag = True
    while flag:
        try:
            data_tuple = q_list.get(timeout=5)
            if data_tuple[1] is None:
                flag = False
                raise Empty
            else:
                links.append(data_tuple)
        except Empty:
            if links:
                with ThreadPoolExecutor(max_workers=3) as exector:
                    tasks = []
                    for item in links:
                        tasks.append(exector.submit(download, item))
                    for future in as_completed(tasks):
                        if future.exception() is not None:
                            print(future.exception())
                        else:
                            print(future.result())
                links = []

            else:
                sleep(1800)

if __name__ == "__main__":
    queue_list = Queue()
    if not os.path.exists('/Users/zipinghuang/Downloads/binance/'):
        os.mkdir('/Users/zipinghuang/Downloads/binance/')
    csv_file = '/Users/zipinghuang/Downloads/binance/result_id.csv'  # 上个文件指定的文件生成路径
    data_path = "https://api.binance.com/sapi/v1/downloadLink"
    headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "X-MBX-APIKEY": 'IFOhCu9dRcWVuu8qd3GqoZRiDAvsOjCNEyJzVJuUyG2RL4fzGvRbvitbrGkj5ZdT'
        }

    t1 = Thread(target=master,args=(csv_file,queue_list,data_path,headers))
    t2 = Thread(target=worker,args=(queue_list,))
    t1.start()
    t2.start()

    t1.join()
    t2.join()