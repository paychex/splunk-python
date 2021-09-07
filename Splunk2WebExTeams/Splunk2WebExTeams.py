# Copyright 2021 Paychex, Inc.
# Licensed pursuant to the terms of the Apache License, Version 2.0 (the "License");
# your use of the Work is subject to the terms and conditions of the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Disclaimer of Warranty. Unless required by applicable law or agreed to in writing, Licensor
# provides the Work (and each Contributor provides its Contributions) on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied, including,
# without limitation, any warranties or conditions of TITLE, NON-INFRINGEMENT,
# MERCHANTABILITY, OR FITNESS FOR A PARTICULAR PURPOSE. You are solely responsible
# for determining the appropriateness of using or redistributing the Work and assume 
# any risks associated with your exercise of permissions under this License.
import logging.handlers, json, sys, argparse, re, getpass
from datetime import datetime, timedelta


# Define logging
def set_logging():
    LOG_FILENAME = 'WebExBot.log'
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
    log_print('error', 'Add the requests repository to your PYTHONPATH to run the these commands:\n'
                       'python -m pip install requests')
    sys.exit()


def api(data):
    try:
        r = data
        if r.status_code >= 300:
            log_print('error', 'Request to ' + r.url + ' failed! Result: ' + str(r.status_code) + ' ' + str(r.reason) +
                      ' ' + str(r.text))
        else:
            response_body = json.loads(r.content.decode())
            return response_body
    except Exception as e:
        log_print('error', 'Call failed with error:\n' + str(e))


def main():
    # Set expected arguments
    parser = argparse.ArgumentParser(
        description='Script to poll splunk alerts to see if they triggered, and then push triggered alerts to WebEx Teams.')
    parser.add_argument('-splunk_host',
                        help='Splunk search head to poll for alerts.',
                        required=True)
    parser.add_argument('-user',
                        help='User name to interact with splunk.',
                        required=True)
    parser.add_argument('-pw',
                        help='Password for user. If not provided script will prompt for it.',
                        required=False)
    parser.add_argument('-splunk_app',
                        help='Splunk app that you want to poll alerts for. If more than one separate by commas.',
                        required=True)
    parser.add_argument('-owners',
                        help='Enter one or more alert owners in a comma separated list to limit the alerts that are '
                             'retrieved. You can enter an asterisk to pull all users in the chosen apps.',
                        required=True)
    parser.add_argument('-webex_token',
                        help='Enter the WebEx Bot bearer token associated to your WebEx Bot.',
                        required=True)
    parser.add_argument('-cert_location',
                        help='Provide directory to certificate location.  Set to False if you want to send unsecured.',
                        required=True)
    parser.add_argument('-custom_message',
                        help='Provide message you want with pushed alert.  Message always includes \"Alert {alertname} has triggered.'
                             ' Please click this link to see the results.\" at the beginning of the message. '
                             'Custom message appends after that. Field supports markdown.',
                        required=False)
    parser.add_argument('-freq_filter',
                        help='Filter results that have not triggered in the last X minutes that you define here. '
                             ' Defaults to last 5 minutes if not here. Input only accepts whole numbers.',
                        required=False)
    parser.add_argument('-search_name',
                        help='Name of search that you want to monitor for triggered alerts. If you have multiple alerts '
                             'separate them with commas. If a comma is in an alert name escape the comma with a backslash. '
                             'If any of the search names contain a space the whole list of searches should be wrapped '
                             'in double quotes. Example: "alert for errors,alert for warnings, alerts\, warnings\, '
                             'and fatal alerting"  That would produce a list of three alerts with names "alert for errors", '
                             '"alert for warnings", and "alerts, warnings, and fatal alerting".',
                        required=True)
    parser.add_argument('-room_list',
                        help='Provide comma separated list of room names you want to send alerts to. If a comma is in '
                             'the room name, escape the comma with a backslash. If you want to send to all rooms the '
                             'user is currently in just enter an asterisk. This will only send to rooms the bot user '
                             'is currently in.  Script will fail if the room(s) you provide is/are not found on'
                             ' the user\'s authorization token provided. Example: "My test bot room, General discussion\,'
                             ' and other things" will produce a list of two rooms: "My test bot room" and "General '
                             'discussion, and other things" If you need to trouble shoot a room that is not showing up '
                             'go to https://developer.webex.com/docs/api/v1/rooms/list-rooms and test what rooms return '
                             'with the bearer token for your splunk bot.  This process is matching on the title field from'
                             ' that API response.',
                        required=True)

    args = parser.parse_args()

    splunk_host = [x.strip() for x in args.splunk_host.strip().split(',')]
    splunk_user = args.user.strip()
    if args.pw is None:
        splunk_pw = getpass.getpass('password: ')
    else:
        splunk_pw = str(args.pw)
    splunk_app = [x.strip() for x in args.splunk_app.strip().split(',')]
    owners = [x.strip() for x in args.owners.strip().split(',')]
    search_name = [re.sub('[\\\],', ',', x.strip()) for x in re.sub('([^\\\]),', '\g<1>█',
                                                                    args.search_name.strip()).split('█')]

    room_list = [re.sub('[\\\],', ',', x.strip().lower()) for x in re.sub('([^\\\]),', '\g<1>█',
                                                                          args.room_list.strip()).split('█')]
    webex_token = args.webex_token.strip()

    if args.custom_message is None:
        custom_message = ''
    else:
        custom_message = args.custom_message.strip()

    if args.cert_location.strip().lower() == 'false':
        cert_info = False
    else:
        cert_info = args.cert_location.strip()

    if args.freq_filter is None:
        freq_filter = 5
    else:
        try:
            freq_filter = int(args.freq_filter.strip())
        except Exception:
            log_print('error', 'Invalid value provided for freq_filter argument.  This only accepts integers.')
            sys.exit()

    # Lookup rooms associated to WebEx Bot and compare to list of rooms requested.

    room_comm_list = {}
    room_missing_list = []
    log_print('info', 'Looking up list of rooms associated to WebEx Bot.')
    room_check = api(requests.get('https://webexapis.com/v1/rooms?max=1000&type=group&sortBy=lastactivity',
                                  headers={'Authorization': 'Bearer ' + webex_token}, verify=cert_info))
    if room_check is None or len(room_check['items']) == 0:
        log_print('warn', 'No data retrieved from WebEx API. Please confirm you have the WebEx Bot in at least 1 group room.')
        sys.exit()
    log_print('info', 'List pulled successfully for WebEx Bot.')

    if args.room_list.strip() == '*':
        log_print('info', 'Asterisk entered for room list.  Sending to all rooms attached to the WebEx Bot.')
        for room in room_check['items']:
            room_comm_list[room['title']] = room['id']
    else:
        # Compare room list to provided list
        log_print('info', 'Comparing provided room names to room names pulled from WebEx API.')

        for room in room_check['items']:
            if room['title'].lower() in room_list:
                room_comm_list[room['title']] = room['id']
            if room['title'].lower() not in room_list:
                room_missing_list.append(room['title'])

        if len(room_list) == len(room_comm_list) and len(room_comm_list) > 0:
            log_print('info', 'All rooms provided were found.  Proceeding to pull list of searches')
        elif 0 < len(room_comm_list) != len(room_list):
            log_print('warn', 'Only some of the rooms provided were found.  Sending to rooms that were identified. The '
                              'following rooms could not be located: ' + ', '.join(room_missing_list))
        elif len(room_comm_list) == 0:
            log_print('error', 'None of the provided rooms were located.  Please double check that the full name of each '
                               'room is provided.')
            sys.exit()

    time_filter = int((datetime.now() - timedelta(minutes=freq_filter)).timestamp())

    # Poll splunk to see if the requested alerts have triggered
    log_print('info', 'Polling splunk to see if any alerts have triggered.')
    search = 'search index=_internal sourcetype=scheduler alert_actions!="" savedsearch_name IN ("' + '","'.join(search_name) + '") app IN ("' + '","'.join(splunk_app) + \
             '") user IN ("' + '","'.join(owners) + \
             '") | stats max(_time) as _time latest(sid) as sid latest(alert_actions) as alert_actions ' \
             'by app savedsearch_name user'
    alerts = {}
    for host in splunk_host:
        splunk = api(requests.post('https://' + host + ':8089/services/search/jobs',
                                   auth=HTTPBasicAuth(splunk_user, splunk_pw),
                                   data={'search': search,
                                         'output_mode': 'json',
                                         'adhoc_search_level': 'fast',
                                         'earliest_time': time_filter,
                                         'latest_time': 'now',
                                         'exec_mode': 'oneshot'}, verify=cert_info))

        if splunk is None:
            log_print('warn', 'Failed to pull data from splunk.')
            sys.exit()
        elif len(splunk['results']) == 0:
            log_print('info', f'None of the requested alerts have triggered in the past {str(freq_filter)} minutes.')
            sys.exit()
        else:
            log_print('info', f'Successfully retrieved {str(len(splunk["results"]))} alerts.')

        alerts[host] = {}

        for searches in splunk['results']:
            alerts[host][searches['savedsearch_name']] = searches['sid']

    # Create messages that will be sent for each alert that triggered.
    log_print('info', 'Creating messages and validating payload size is not too large.')
    messages = []

    for (key,value) in alerts.items():
        hosts = key
        for (key,value) in value.items():
            messages.append(f'Alert "{key}" has triggered. Please click this '
                            f'[link](https://{hosts}/en-US/app/search/search?sid={value}) to see the results. ' +
                            custom_message)

    if len('\n'.join(messages)) >= 1000:
        log_print('error', 'Too many alerts are were going to be sent.  Please limit the amount of alerts you select.')
        sys.exit()

    log_print('info', 'Message payload completed successfully.  Payload is not too large.')

    for (key,value) in room_comm_list.items():
        log_print('info', 'Attempting to send message to room ' + str(key) + ".")

        payload = {"markdown": '\n'.join(messages), "roomId": value}

        send_alert = api(requests.post('https://webexapis.com/v1/messages', data=payload,
                                       headers={'Authorization': 'Bearer ' + webex_token},
                                       verify=cert_info))
        if send_alert is None:
            log_print('warn', 'Attempt to send alert to room "' + str(key) + '" was unsuccessful.')
        else:
            log_print('info', 'Attempt was successful.')


if __name__ == '__main__':
    main()
