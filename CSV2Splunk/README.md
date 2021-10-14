# CSV2Splunk

## What is CSV2Splunk?

CSV2Splunk is a python script that allows you to upload a csv file to splunk via splunk's API. Splunk currently does not have a way to upload a CSV directly via the API, but using splunk's search API with a `makeresults` command, and then passing in the CSV contents to that search as a JSON payload, allows us to use splunk's native JSON parsing to parse it back into a table and then write that to a lookup file.

⚠️ **WARNING**: When sending data to a search head cluster, it works best if you use a specific search head in the cluster as your host instead of using a load balanced address.  This is because it is possible for you to be routed to a different search head when appending to the lookup file in batches which may or may not have the most up to date copy of the lookup file replicated to it. To avoid this problem use a specific search head in your request.

## Requirements

This script requires your python environment to have the requests library installed and a valid splunk login.  If you do not have requests library installed you can run the below commands to install it:

```
python3 -m pip install requests
```
## How to run

To get help just run `python3 CSV2Splunk.py -h` and the below output will explain the different arguments that are required:

```
usage: CSV2Splunk.py [-h] -splunk_host SPLUNK_HOST -splunk_user SPLUNK_USER [-splunk_pw SPLUNK_PW]
                            -splunk_csv_name SPLUNK_CSV_NAME -cert_location CERT_LOCATION -source_csv_file
                            SOURCE_CSV_FILE [-overwrite {Y,y,N,n}] [-batch_size BATCH_SIZE]

Push a csv file to splunk from a directory. This process converts a csv to json string, then passes that json into a
makeresults search in splunk. Splunk will then parse the json back into a csv in the search and do an output lookup to
the lookup filename you specify. WARNING! Extremely large files may fail due to your users defined limits in splunk's
configurations. Reduce the batch size if that is the case.

optional arguments:
  -h, --help            show this help message and exit
  -splunk_host SPLUNK_HOST
                        Host/Domain that csv will be pushed to. WARNING: When sending data to a search head cluster,
                        it works best if you use a specific search head in the cluster as your host instead of using a
                        load balanced address. This is because it is possible for you to be routed to a different
                        search head when appending to the lookup file in batches which may or may not have the most up
                        to date copy of the lookup file replicated to it. To avoid this problem use a specific search
                        head in your request.
  -splunk_user SPLUNK_USER
                        User that has splunk credentials.
  -splunk_pw SPLUNK_PW  User's password that has splunk credentials.
  -splunk_csv_name SPLUNK_CSV_NAME
                        Name of the file you want to push the csv into in splunk. ex: MyTempFile.csv
  -cert_location CERT_LOCATION
                        Provide directory to certificate location. Set to False if you want to send unsecured.
  -source_csv_file SOURCE_CSV_FILE
                        Absolute path to csv file. ex: /var/tmp/MyCsvFile.csv
  -overwrite {Y,y,N,n}  Set to "Y" if you want to overwrite the file with new data. Set to "N" or do not set to append
                        to the lookup file.
  -batch_size BATCH_SIZE
                        Size of batches that process will cycle through. Defaults to 10,000 per batch. Only accepts
                        integers.
```
