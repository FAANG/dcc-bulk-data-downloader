import os
import sys
import json
import shutil
import pathlib
import getpass
import argparse
import requests
import urllib.request
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
        # study_id is used as a single directory name only; never let it escape
        path = safe_output_path(download_location, study_id)
        os.makedirs(path, exist_ok=True)
        return path
    except (OSError, ValueError):
        return False

def safe_output_path(base_dir, *parts):
    """Join untrusted path components onto base_dir, guaranteeing the result
    stays inside base_dir.

    Every component is reduced to its basename (stripping any directory
    separators or traversal sequences supplied by the remote API), rejected if
    empty/./.., and the fully resolved target is confirmed to live under the
    resolved base directory. Raises ValueError on any unsafe input.
    """
    base_real = os.path.realpath(base_dir)
    cleaned = []
    for part in parts:
        name = os.path.basename(str(part))
        if name in ('', '.', '..'):
            raise ValueError(f"unsafe path component: {part!r}")
        cleaned.append(name)
    target = os.path.realpath(os.path.join(base_real, *cleaned))
    if target != base_real and os.path.commonpath([target, base_real]) != base_real:
        raise ValueError(f"path escapes base directory: {target!r}")
    return target

def download_file(url, output_path):
    # urllib.request handles ftp:// and https:// and, unlike the abandoned
    # `wget` package, lets us write to a path we have already validated.
    # HTTPS certificates are verified by default.
    with urllib.request.urlopen(url) as response, open(output_path, 'wb') as out:
        shutil.copyfileobj(response, out)

def download_process(url, base_dir, parts):
    try:
        output_path = safe_output_path(base_dir, *parts)
    except ValueError as err:
        print(f"Skipping file with unsafe name from server: {err}")
        return
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    except OSError:
        print(f"Directory for {output_path} can not be created")
        return
    print(f"Downloading file {os.path.basename(output_path)}")
    try:
        download_file(url, output_path)
    except Exception as err:
        print(f"Failed to download {url}: {err}")

def downloader(download_list, processes):
    # download data with multiprocessing
    cpus = multiprocessing.cpu_count()
    pool = multiprocessing.Pool(cpus if cpus < processes else processes)
    for url, base_dir, parts in download_list:
        pool.apply_async(download_process, args=(url, base_dir, parts))
    pool.close()
    pool.join()
    print("Download complete")

def get_experiment_files(mode, study_id, path, token, processes):
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
            # filename is untrusted (from the API); path containment is enforced
            # in safe_output_path() at download time.
            download_list.append([url, path, [filename]])
        if len(download_list):
            print(f"Downloading {len(download_list)} experiment files...\n")
            downloader(download_list, processes)
        else:
            print(f"Study {study_id} has no experiment files")
    else:
        print(f"Study {study_id} has no experiment files")

def get_analysis_files(mode, study_id, path, token, processes):
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
                    # both analysis_id and filename are untrusted; containment is
                    # enforced in safe_output_path() at download time.
                    download_list.append([url, path, [analysis_id, filename]])
        if len(download_list):
            print(f"Downloading {len(download_list)} analysis files...\n")
            downloader(download_list, processes)
        else:
            print(f"Study {study_id} has no analysis files")
    else:
        print(f"Study {study_id} has no analysis files")

def main(mode, study_id, data_type, download_location, processes):
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
        get_experiment_files(mode, study_id, path, token, processes)
    elif data_type == 'analysis':
        get_analysis_files(mode, study_id, path, token, processes)
    else:
        get_experiment_files(mode, study_id, path, token, processes)
        get_analysis_files(mode, study_id, path, token, processes)

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
    parser.add_argument("--processes", default=8)
    args = parser.parse_args()
    config = vars(args)
    if config["study_id"] is None or config["study_id"] == '':
        print("Please provide study_id parameter")
        sys.exit(0)
    else:
        try:
            processes = int(config['processes'])
        except (TypeError, ValueError):
            print("--processes must be an integer")
            sys.exit(0)
        if processes < 1:
            processes = 1
        main(config["mode"], config["study_id"], config["data_type"], config["download_location"], processes)
