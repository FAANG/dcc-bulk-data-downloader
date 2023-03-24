import os
import sys
import json
import wget
import pathlib
import getpass
import argparse
import requests
import warnings
import multiprocessing

def authorize(user, pwd):
    url = "https://api.faang.org/api-token-auth/"
    payload = {
        "username": user,
        "password": pwd
    }
    res = requests.post(url, json=payload)
    if res.status_code == 200:
        return json.loads(res.content.decode("utf-8"))["token"]
    return False

def fetch_study_files(study_id, token):
    url = f"https://api.faang.org/private_portal/file/?size=10000&from_=0&search={study_id}"
    res = requests.get(url, headers={"Authorization": f"jwt {token}"})
    if res.status_code == 200:
        data = json.loads(res.content)['hits']['hits']
        return data
    return False

def download_process(filename, url, output_path):
    print(f"\nDownloading file {filename}")
    wget.download(url, out=output_path)

def main(user, password, study_id, download_location):
    token = authorize(user, password)
    if token:
        if (download_location == '' or download_location is None) or os.path.exists(download_location) == False:
            print("Download location not provided, using default location")
            download_location = pathlib.Path(__file__).parent.resolve()
            download_location = os.path.join(download_location, "data")
        path = os.path.join(download_location, study_id)
        try:
            os.makedirs(path, exist_ok=True)
            data = fetch_study_files(study_id, token)
            if data:
                download_list = []
                for file in data:
                    url = f"ftp://{file['_source']['url']}"
                    filename = file['_source']['name']
                    file_path = os.path.join(path, filename)
                    download_list.append([url, filename, file_path])
                cpus = multiprocessing.cpu_count()
                max_pool_size = 8
                pool = multiprocessing.Pool(cpus if cpus < max_pool_size else max_pool_size)
                for url, filename, path in download_list:
                    pool.apply_async(download_process, args=(filename, url, path))
                pool.close()
                pool.join()
                print("Download complete")
            else:
                print(f"No files found for the study {study_id}")
                sys.exit(0)
        except:
            print(f"Directory {study_id} can not be created")
    else:
        print("Invalid credentials!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Welcome to the Downloader Utility")
    parser.add_argument("--user")
    parser.add_argument("--study_id")
    parser.add_argument("--download_location")
    args = parser.parse_args()
    password = getpass.getpass()
    config = vars(args)
    warnings.filterwarnings(action='ignore')
    if config["user"] is None or config["user"] == '':
        print("Please provide user parameter")
        sys.exit(0)
    elif not password:
        print("Please provide password parameter")
        sys.exit(0)
    elif config["study_id"] is None or config["study_id"] == '':
        print("Please provide study_id parameter")
        sys.exit(0)
    else:
        main(config["user"], password, config["study_id"], config["download_location"])
