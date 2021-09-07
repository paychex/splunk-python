import csv, json, logging.handlers, sys, argparse, getpass


# Define logging
def set_logging():
    LOG_FILENAME = 'CSV2Splunk_batch_processor.log'
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    log_handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=(10 * 1024 * 1024), backupCount=5)
    log_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)


set_logging()


def log_print(log_type, message):
    if log_type.lower() == 'error':
        logging.error(message)
    elif log_type.lower() == 'info':
        logging.info(message)
    elif log_type.lower() == 'warn' or log_type == 'warning':
        logging.warning(message)
    elif log_type.lower() == 'debug':
        logging.debug(message)
    print(log_type.upper() + ': ' + message)


# import requests error handling
try:
    import requests
    from requests.auth import HTTPBasicAuth
except ImportError:
    log_print('error', 'Add the requests repository to your PYTHONPATH to run the this command:\n'
                       'python -m pip install requests')
    sys.exit()


def main():
    # user inputs
    parser = argparse.ArgumentParser(
        description='Push a csv file to splunk from a directory. This process converts a csv to json string, then ' +
                    'passes that json into a makeresults search in splunk.  Splunk will then parse the json back ' +
                    'into a csv in the search and do an output lookup to the lookup filename you specify.\n' +
                    'WARNING! Extremely large files may fail due to your users defined limits in splunk\'s' +
                    ' configurations.  Reduce the batch size if that is the case.')
    parser.add_argument('-splunk_host',
                        help='Host/Domain that csv will be pushed to. WARNING: When sending data to a search head cluster, it works best if you use a specific search head in the cluster as your host instead of using a load balanced address. This is because it is possible for you to be routed to a different search head when appending to the lookup file in batches which may or may not have the most up to date copy of the lookup file replicated to it. To avoid this problem use a specific search head in your request.',
                        required=True)
    parser.add_argument('-splunk_user',
                        help='User that has splunk credentials.',
                        required=True)
    parser.add_argument('-splunk_pw',
                        help='User\'s password that has splunk credentials.',
                        required=False)
    parser.add_argument('-splunk_csv_name',
                        help='Name of the file you want to push the csv into in splunk. ex: MyTempFile.csv',
                        required=True)
    parser.add_argument('-cert_location',
                        help='Provide directory to certificate location.  Set to False if you want to send unsecured.',
                        required=True)
    parser.add_argument('-source_csv_file',
                        help='Absolute path to csv file. ex: /var/tmp/MyCsvFile.csv',
                        required=True)
    parser.add_argument('-overwrite',
                        help='Set to "Y" if you want to overwrite the file with new data.  Set to "N" or do not set to '
                             'append to the lookup file.',
                        required=False, choices=['Y', 'y', 'N', 'n'])
    parser.add_argument('-batch_size',
                        help='Size of batches that process will cycle through.  Defaults to 10,000 per batch. '
                             'Only accepts integers.',
                        required=False)
    args = parser.parse_args()

    splunk_host = args.splunk_host.strip()

    splunk_user = args.splunk_user.strip()

    if args.overwrite is None:
        overwrite = 'N'
    else:
        overwrite = args.overwrite.strip().upper()

    if args.splunk_pw is None:
        splunk_pw = getpass.getpass('Password for splunk: ').strip()
    else:
        splunk_pw = args.splunk_pw.strip()

    if args.cert_location.strip().lower() == 'false':
        cert_info = False
    else:
        cert_info = args.cert_location.strip()

    csv_location = args.source_csv_file.strip()

    splunk_csv_name = args.splunk_csv_name.strip()

    if args.batch_size is None:
        batch_size = 10000
    else:
        try:
            batch_size = int(args.batch_size.strip().replace(',', ''))
        except Exception as e:
            log_print('error', 'Invalid input provided for batch_size. Only accepts integers. ' + str(e))
            sys.exit()

    # reading csv extracted and importing as an object
    try:
        logging.info('Reading CSV file.')
        print('Reading CSV file.')
        with open(csv_location, encoding='utf-8') as c:
            r = csv.DictReader(c)
            table = []
            for row in r:
                table.append(row)
            c.close()
    except Exception as e:
        log_print('error', 'CSV read failed with exception:\n' + str(e))
        sys.exit()

    log_print('info', 'CSV File read successfully.')

    if overwrite == 'Y':
        log_print('info', 'Overwrite set to "Y".  Running outputlookup on csv table to delete contents before running '
                          'batch upload.')

        query = '| outputlookup ' + splunk_csv_name

        spl_search_request = {'search': query,
                              'exec_mode': 'oneshot',
                              'output_mode': 'json',
                              'count': 0}

        spl_table_delete = request('https://' + splunk_host + ':8089/services/search/jobs',
                                   HTTPBasicAuth(splunk_user, splunk_pw),
                                   spl_search_request, cert_info)

        log_print('info', 'Successfully deleted contents of lookup ' + splunk_csv_name + '.')

    batch_count = 0

    log_print('info', 'Beginning batch processing of CSV data import to splunk.')
    for i in range(0, len(table), batch_size):
        batch_table = table[i:i + batch_size]
        batch_count += 1
        log_print('info', 'Processing batch count ' + str(batch_count) + ' which contains ' + str(len(batch_table))
                  + ' row(s).')
        batch_processor(batch_table, splunk_csv_name, splunk_host, splunk_user, splunk_pw, cert_info)

    log_print('info',
              'Batch processing of csv file is complete.  Please check splunk to confirm your file is accurately'
              ' uploaded.')


def batch_processor(table, splunk_csv_name, splunk_host, splunk_user, splunk_pw, cert_info):
    # creating splunk query that will convert the table to a json string for a search and then back into a csv.

    query = '| makeresults | fields - _time | eval data=' + json.dumps(json.dumps(table)) + \
            ' | eval data=spath(data, "{}") | mvexpand data | spath input=data ' \
            '| fields - data | foreach * [eval "<<FIELD>>"=if(\'<<FIELD>>\'="", null(), \'<<FIELD>>\')] ' \
            '| outputlookup append=true ' + splunk_csv_name

    # clearing memory
    table = None

    spl_search_request = {'search': query,
                          'exec_mode': 'oneshot',
                          'output_mode': 'json',
                          'count': 0}

    log_print('info', 'Sending CSV batch upload to Splunk.')

    spl_search_post = request('https://' + splunk_host + ':8089/services/search/jobs',
                              HTTPBasicAuth(splunk_user, splunk_pw),
                              spl_search_request, cert_info)

    log_print('info', 'CSV batch upload completed successfully.')


def request(url, auths, payload, cert_info):
    try:
        r = requests.post(url, data=payload, auth=auths, verify=cert_info)
        if r.status_code >= 300:
            log_print('error', 'POST Request to ' + url + ' failed! Result: ' + str(r.status_code)
                      + ' ' + str(r.reason) + ' ' + str(r.text))
            sys.exit()
        else:
            response_body = r.json()
            return response_body
    except Exception as e:
        log_print('error', str(e))
        sys.exit()


if __name__ == '__main__':
    main()
