# Private data downloader

Bulk download private portal files

There are 2 ways to bulk download private data

## 1. Using Python Script

### Requirements

1. Python3 should be installed.

2. Run requirements.txt using below command to install the required python libraries.

```
pip install -r requirements.txt
```

### Steps

1. Run the python script using below command, with appropriate parameter values.
  
```
python downloader.py --user "admin" --study_id "PRJEB43235" --download_location "/home/user"
```

* `--user` (Required) Username for private portal (`eg : "admin"`)
* `--study_id` (Required) Accession of the study for which you wish to download files (`eg : "PRJEB43235"`)
* `--download_location` (Optional) The local path where you want to download the files (`eg: "/home/user"`). The files will be downloaded within a directory having the same name as the study_id.

2. You will be prompted for a password. Please enter the password corresponding to the `user` in the previous command to begin the download.

## 2. Using Docker Container

### Requirements

1. Docker should be installed.

2. Build docker image using below command

```
docker build -t bulk-downloader:latest .
```

3. Run the docker image using below command, with appropriate parameter values. Files will be downloaded by default in your current working directory.

```
docker run -it --rm -v "$PWD:/code/data" bulk-downloader:latest --user "admin" --study_id "PRJEB43235"
```

* `--user` (Required) Username for private portal (`eg : "admin"`)
* `--study_id` (Required) Accession of the study for which you wish to download files (`eg : "PRJEB43235"`)

4. You will be prompted for a password. Please enter the password corresponding to the `user` in the previous command to begin the download.






