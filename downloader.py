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

def create_directory(download_location, study_id):
    try:
        if (download_location == '' or download_location is None) or os.path.exists(download_location) == False:
            print("Download location not provided, using default location")
            download_location = pathlib.Path(__file__).parent.resolve()
            download_location = os.path.join(download_location, "data")
        path = os.path.join(download_location, study_id)
        os.makedirs(path, exist_ok=True)
        return path
    except:
        return False

def download_process(filename, url, output_path):
    print(f"Downloading file {filename}")
    output_path = os.path.join(output_path, filename)
    wget.download(bar=None, url=url, out=output_path)

def downloader(download_list):
    # download data with multiprocessing
    cpus = multiprocessing.cpu_count()
    max_pool_size = 8
    pool = multiprocessing.Pool(cpus if cpus < max_pool_size else max_pool_size)
    for url, filename, path in download_list:
        try:
            os.makedirs(path, exist_ok=True)
        except:
            print(f"Directory {path} can not be created") 
            sys.exit(0)
        pool.apply_async(download_process, args=(filename, url, path))
    pool.close()
    pool.join()
    print("Download complete")

def get_experiment_files(mode, study_id, path, token=None):
    if mode == 'private':
        url = f"https://api.faang.org/private_portal/file/?size=10000&from_=0&search={study_id}"
        res = requests.get(url, headers={"Authorization": f"jwt {token}"})
    else:
        url = f"https://api.faang.org/data/file/_search/?size=10000&from_=0&search={study_id}"
        res = requests.get(url)
    if res.status_code == 200:
        data = json.loads(res.content)['hits']['hits']
        download_list = []
        for file in data:
            url = f"ftp://{file['_source']['url']}"
            filename = file['_source']['name']
            download_list.append([url, filename, path])
        if len(download_list):
            print(f"Downloading {len(download_list)} experiment files...\n")
            downloader(download_list)
        else:
            print(f"Study {study_id} has no experiment files")
    else:
        print(f"Study {study_id} has no experiment files")

def get_analysis_files(mode, study_id, path, token=None):
    if mode == 'private':
        url = f"https://api.faang.org/private_portal/analysis/?size=10000&from_=0&search={study_id}"
        res = requests.get(url, headers={"Authorization": f"jwt {token}"})
    else:
        url = f"https://api.faang.org/data/analysis/_search/?size=10000&from_=0&search={study_id}"
        res = requests.get(url)
    if res.status_code == 200:
        data = json.loads(res.content)['hits']['hits']
        download_list = []
        for analysis in data:
            if 'files' in analysis['_source']:
                analysis_id = analysis['_source']['accession']
                for file in analysis['_source']['files']: 
                    url = f"ftp://{file['url']}"
                    filename = file['name']
                    file_path = os.path.join(path, analysis_id)
                    download_list.append([url, filename, file_path])
        if len(download_list):
            print(f"Downloading {len(download_list)} analysis files...\n")
            downloader(download_list)
        else:
            print(f"Study {study_id} has no analysis files")
    else:
        print(f"Study {study_id} has no analysis files")

def main(mode, study_id, data_type, download_location):
    # get username and password if fetching private data
    if mode == 'private':
        user = input("Username: ")
        password = getpass.getpass()
        if not user or not password:
            print("Please provide the credentials")
            sys.exit(0)
        token = authorize(user, password)
        if not token:
            print("Invalid credentials!")
            sys.exit(0)
    # create directories
    path = create_directory(download_location, study_id)
    if not path:
        print(f"Directory for study {study_id} can not be created") 
        sys.exit(0)
    # download requested data
    if mode == 'public':
        token = None
    if data_type == 'file':
        get_experiment_files(mode, study_id, path, token)
    elif data_type == 'analysis':
        get_analysis_files(mode, study_id, path, token)
    else:
        get_experiment_files(mode, study_id, path, token)
        get_analysis_files(mode, study_id, path, token)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Welcome to the Downloader Utility")
    parser.add_argument("--mode",
                    default='public',
                    const='public',
                    nargs='?',
                    choices=('public', 'private'),
                    help='Fetch private or public data (default: %(default)s)')
    parser.add_argument("--study_id")
    parser.add_argument("--download_location")
    parser.add_argument("--data_type",
                    default='all',
                    const='all',
                    nargs='?',
                    choices=('file', 'analysis', 'all'),
                    help='Fetch experiment files, analysis objects, or both (default: %(default)s)')
    args = parser.parse_args()
    config = vars(args)
    warnings.filterwarnings(action='ignore')
    if config["study_id"] is None or config["study_id"] == '':
        print("Please provide study_id parameter")
        sys.exit(0)
    else:
        main(config["mode"], config["study_id"], config["data_type"], config["download_location"])
