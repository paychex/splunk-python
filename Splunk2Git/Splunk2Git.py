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
import logging, re, sys, logging.handlers, argparse, getpass, urllib.parse, os, time


# Define logging
def set_logging():
    LOG_FILENAME = 'Splunk_Git_integration.log'
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    log_handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=(50 * 1024 * 1024), backupCount=5)
    log_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)


def log_print(log_type, message):
    if log_type.lower() == 'error':
        logging.error(message)
    elif log_type.lower() == 'info':
        logging.info(message)
    elif log_type.lower() == 'warn' or type == 'warning':
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

# import git error handling
try:
    import git
except ImportError:
    log_print('error', 'Add the gitpython repository to your PYTHONPATH to run this command:\n'
                       'python -m pip install gitpython')
    sys.exit()


# Define the functions used for api interactions
def post(url, auths, payload, cert_info):
    try:
        r = requests.post(url, data=payload, auth=auths, verify=cert_info)
        if r.status_code >= 300:
            log_print('error', 'Request to ' + url + ' failed with payload '
                      + re.sub("('password':)[^}]+", "\g<1> SECRET", str(payload))
                      + '! Result: ' + str(r.status_code) + ' ' + str(r.reason) + ' ' + str(r.text))
        else:
            response_body = r.json()
            return response_body
    except Exception as e:
        log_print('error', 'Call to ' + url + 'failed with error:\n' + str(e))


def get(url, auths, payload, cert_info):
    try:
        r = requests.get(url, data=payload, auth=auths, verify=cert_info)
        if r.status_code >= 300:
            log_print('error', 'Request to ' + url + ' failed with payload '
                      + re.sub("('password':)[^}]+", "\g<1> SECRET", str(payload))
                      + '! Result: ' + str(r.status_code) + ' ' + str(r.reason) + ' ' + str(r.text))
        else:
            response_body = r.json()
            return response_body
    except Exception as e:
        log_print('error', 'Call to ' + url + 'failed with error:\n' + str(e))


# Define main function that performs actual work
def main():
    set_logging()  # Turn on logging
    # Set expected arguments
    parser = argparse.ArgumentParser(
        description='Script to pull down splunk objects and push them to a bitbucket/git repository. This only retrieves '
                    'objects that are visible to other users.')
    parser.add_argument('-splunk_host',
                        help='Splunk search head to retrieve objects from. If more than one, separate by commas.',
                        required=True)
    parser.add_argument('-user',
                        help='User name to interact with splunk.',
                        required=True)
    parser.add_argument('-pw',
                        help='Password for user. If not provided script will prompt for it.',
                        required=False)
    parser.add_argument('-splunk_app',
                        help='Splunk app that you want to pull down objects for. If more than one separate by commas.',
                        required=True)
    parser.add_argument('-repo_location',
                        help='Git repo location on machine executing the script.  Must contain a .git folder.',
                        required=True)
    parser.add_argument('-owners',
                        help='Enter one or more object owners in a comma separated list to limit what objects you '
                             'retrieve.  You can enter an asterisk to pull all users in the chosen apps.',
                        required=True)
    parser.add_argument('-cert_location',
                        help='Provide directory to certificate location.  Set to False if you want to send unsecured.',
                        required=True)
    parser.add_argument('-git_branch',
                        help='Provide git branch you want to push the data to.',
                        required=True)
    parser.add_argument('-checkout_branch',
                        help='If currently checked out branch is not the provided branch and you want the script to'
                             ' check out the input branch put "Y" here.  Defaults to N if not provided. This is NOT '
                             'recommended to use with "Y" unless you are sure you have no pending commits.',
                        required=False, choices=['Y', 'N'])
    parser.add_argument('-commit_message',
                        help='Provide message you want with the commit.  Defaults to \"Splunk to git python '
                             'script\" if not provided.',
                        required=False)
    parser.add_argument('-days_filter',
                        help='Filter objects that have only been updated in the last number of days you input '
                             'here. Defaults to last 7 days if not here.  Inputting "all time" will pull everything. '
                             'Input only accepts whole numbers or "all time"',
                        required=False)

    args = parser.parse_args()

    # Begin argument parsing
    splunk_host = [x.strip() for x in args.splunk_host.strip().split(',')]

    admin_user = args.user.strip()

    if args.pw is None:
        admin_pw = getpass.getpass('password: ')
    else:
        admin_pw = str(args.pw)

    splunk_app = [x.strip() for x in args.splunk_app.strip().split(',')]

    owners = [x.strip() for x in args.owners.strip().split(',')]

    repo_location = re.sub('[\\\]', '/', args.repo_location.strip())

    git_branch = args.git_branch.strip()

    if args.checkout_branch is None:
        checkout_branch = 'N'
    else:
        checkout_branch = args.checkout_branch.strip()

    if args.commit_message is None:
        commit_message = 'Splunk to git python script.'
    else:
        commit_message = args.commit_message.strip()

    if args.cert_location.strip() == 'False':
        cert_location = False
    else:
        cert_location = args.cert_location.strip()

    if args.days_filter is None:
        time_limit = round(time.time() - (86400 * 7), 0)
    elif args.days_filter.strip().lower() == 'all time':
        time_limit = 0
    elif re.match('^\d+$', args.days_filter.strip()) is not None:
        time_limit = round(time.time() - (86400 * int(args.days_filter.strip())), 0)
    elif re.match('^\d+\.\d+$', args.days_filter.strip()) is not None:
        time_limit = round(time.time() - (86400 * float(args.days_filter.strip())), 0)
    else:
        log_print('error', 'Invalid argument supplied for days_filter.  Please only supply "all time" or an integer.')
        sys.exit()

    # Validating git repo
    try:
        repo = git.Repo(repo_location + '/.git')
    except Exception:
        log_print('error', 'No .git folder/config in provided repo location or git is not properly set up in this repo '
                           'location.  Please ensure your repo has been configured to function with git.')
        sys.exit()

    # Validating repo branch

    if str(repo.active_branch.name) == git_branch:
        log_print('info', 'Selected branch ' + git_branch + ' is already checked out.  Proceeding.')
    elif str(repo.active_branch.name) != git_branch and git_branch in repo.branches and checkout_branch == 'Y':
        log_print('info', 'Selected branch ' + git_branch + ' is not checked out. Currently ' +
                  str(repo.active_branch.name) + ' is checked out. Checking out requested branch due to '
                                                 'checkout_branch flag being set to "Y"')
        try:
            checkout = repo.git.checkout(git_branch)
        except Exception as e:
            log_print('error', 'Branch check out failed with error:\n' + str(e))
            sys.exit()

        log_print('info', 'Check out of branch ' + git_branch + ' successful.  Message: ' + str(checkout))
    elif str(repo.active_branch.name) != git_branch and git_branch in repo.branches and checkout_branch == 'N':
        log_print('info', 'Selected branch ' + git_branch + ' is not checked out. Currently ' +
                  str(repo.active_branch.name) + ' is checked out. Script exiting because checkout_branch is not '
                                                 'set to "Y"')
        sys.exit()
    elif git_branch not in repo.branches:
        log_print('error',
                  'Branch requested has not been set up in git yet.  Please add this branch to your repo first.')
        sys.exit()

    # Pulling from origin to ensure files are up to date.
    try:
        log_print('info', 'Attempting to pull down most current repo information.')
        pull = repo.remotes.origin.pull()
    except Exception as e:
        log_print('error', 'Attempt to pull data from origin failed. ' + str(e))
        sys.exit()

    log_print('info', 'Pull from origin complete.')

    # defining splunk api endpoints to retrieve objects from and fields from each object retrieved to store.
    splunk_api_endpoints = ['/servicesNS/-/-/data/ui/views',
                            '/servicesNS/-/-/data/props/calcfields',
                            '/servicesNS/-/-/data/props/fieldaliases',
                            '/servicesNS/-/-/data/transforms/extractions',
                            '/servicesNS/-/-/data/props/extractions',
                            '/servicesNS/-/-/data/props/sourcetype-rename',
                            '/servicesNS/-/-/data/ui/workflow-actions',
                            '/servicesNS/-/-/data/ui/times',
                            '/servicesNS/-/-/saved/eventtypes',
                            '/servicesNS/-/-/saved/fvtags',
                            '/servicesNS/-/-/saved/ntags',
                            '/servicesNS/-/-/admin/tags',
                            '/servicesNS/-/-/data/transforms/lookups',
                            '/servicesNS/-/-/data/props/lookups',
                            '/servicesNS/-/-/data/ui/nav',
                            '/servicesNS/-/-/data/ui/panels',
                            '/servicesNS/-/-/datamodel/model',
                            '/servicesNS/-/-/admin/macros',
                            '/servicesNS/-/-/saved/searches']

    special_rules_endpoints = ['/servicesNS/-/-/data/props/calcfields',
                               '/servicesNS/-/-/data/props/fieldaliases',
                               '/servicesNS/-/-/data/props/extractions',
                               '/servicesNS/-/-/admin/tags',
                               '/servicesNS/-/-/data/props/lookups']

    fieldarray = {'create/update': {'ui/views': ['name',
                                                 'eai:data'],
                                    'props/calcfields': ['name',
                                                         'stanza',
                                                         'value'],
                                    'props/fieldaliases': ['name',
                                                           'stanza',
                                                           'alias.'],
                                    'transforms/extractions': ['CAN_OPTIMIZE',
                                                               'CLEAN_KEYS',
                                                               'disabled',
                                                               'FORMAT',
                                                               'KEEP_EMPTY_VALS',
                                                               'MV_ADD',
                                                               'name',
                                                               'REGEX',
                                                               'SOURCE_KEY',
                                                               'DELIMS',
                                                               'FIELDS',
                                                               'REPEAT_MATCH'],
                                    'props/extractions': ['name',
                                                          'stanza',
                                                          'type',
                                                          'value'],
                                    'props/sourcetype-rename': ['name',
                                                                'value'],
                                    'ui/workflow-actions': ['display_location',
                                                            'eventtypes',
                                                            'fields',
                                                            'label',
                                                            'name',
                                                            'link.',
                                                            'search.',
                                                            'type'],
                                    'ui/times': ['earliest_time',
                                                 'header_label',
                                                 'is_sub_menu',
                                                 'label',
                                                 'latest_time',
                                                 'name',
                                                 'order',
                                                 'show_advanced',
                                                 'show_date_range',
                                                 'show_datetime_range',
                                                 'show_presets',
                                                 'show_realtime',
                                                 'show_relative'],
                                    'saved/searches': ['action.',
                                                       'actions',
                                                       'alert.',
                                                       'alert_comparator',
                                                       'alert_condition',
                                                       'alert_threshold',
                                                       'alert_type',
                                                       'allow_skew',
                                                       'args.',
                                                       'auto_summarize',
                                                       'auto_summarize.',
                                                       'cron_schedule',
                                                       'defer_scheduled_searchable_idxc',
                                                       'description',
                                                       'disabled',
                                                       'dispatch.',
                                                       'dispatchAs',
                                                       'display.',
                                                       'displayview',
                                                       'is_scheduled',
                                                       'is_visible',
                                                       'max_concurrent',
                                                       'name',
                                                       'qualifiedSearch',
                                                       'realtime_schedule',
                                                       'request.',
                                                       'restart_on_searchpeer_add',
                                                       'run_n_times',
                                                       'run_on_startup',
                                                       'schedule_window',
                                                       'search',
                                                       'vsid'],
                                    'datamodel/model': ['acceleration',
                                                        'description',
                                                        'name',
                                                        'eai:data'],
                                    'saved/eventtypes': ['color',
                                                         'description',
                                                         'disabled',
                                                         'name',
                                                         'priority',
                                                         'search',
                                                         'tags'],
                                    'saved/fvtags': ['name',
                                                     'tag.',
                                                     'tags'],
                                    'saved/ntags': ['name',
                                                    'tagged',
                                                    'tagged.'],
                                    'admin/tags': ['field_name',
                                                   'field_value',
                                                   'name',
                                                   'tag_name'],
                                    'transforms/lookups': ['batch_index_query',
                                                           'case_sensitive_match',
                                                           'collection',
                                                           'default_match',
                                                           'disabled',
                                                           'external_cmd',
                                                           'external_type',
                                                           'fields_list',
                                                           'filename',
                                                           'match_type',
                                                           'max_matches',
                                                           'max_offset_secs',
                                                           'min_matches',
                                                           'min_offset_secs',
                                                           'name',
                                                           'time_field',
                                                           'time_format',
                                                           'replicate_delta'],
                                    'props/lookups': ['lookup.',
                                                      'name',
                                                      'overwrite',
                                                      'stanza',
                                                      'transform'],
                                    'ui/nav': ['disabled',
                                               'eai:data',
                                               'name'],
                                    'ui/panels': ['disabled',
                                                  'eai:data',
                                                  'eai:digest',
                                                  'name',
                                                  'panel.'],
                                    'admin/macros': ['args',
                                                     'definition',
                                                     'description',
                                                     'disabled',
                                                     'errormsg',
                                                     'iseval',
                                                     'name',
                                                     'validation']},
                  'acl': ['sharing',
                          'perms.read',
                          'perms.write',
                          'owner']}

    # search string used to filter objects returned on each api call. Hard coded to filter only shared objects.
    search = urllib.parse.quote('(eai:acl.owner=' + ' OR eai:acl.owner='.join(owners) + ') (eai:acl.app=' +
                                ' OR eai:acl.app='.join(splunk_app) +
                                ') (eai:acl.sharing=app OR eai:acl.sharing=global)')

    # Begin for loop to iterate through each API end points. This process will write two to three files for each object.
    # A object file and a ACL file.  File format for UI api's will be in XML for the eai:data field, but the rest will
    # be written in a KEY = VALUE format that is similar to splunk conf files.  Line breaks will be escaped with a "\"
    # character just like in the splunk conf files.  This may change in the future if it's decided that there is a
    # better format to use.

    files_created = {'objects': [],
                     'acls': []}

    for host in splunk_host:
        for endpoint in splunk_api_endpoints:
            # Identify fields of interest for this endpoint
            fields = fieldarray['create/update'][re.sub('.+/([^/]+/[^/]+)$', '\g<1>', endpoint)]

            # Validating expected directory exists.  If it's missing it creates it
            for app in splunk_app:
                create_directory = str(repo_location + '/' + app + '/' + re.sub('.+/([^/]+/[^/]+)$', '\g<1>', endpoint))
                try:
                    if len(os.listdir(create_directory)) >= 0:
                        log_print('info', 'Directory ' + create_directory + ' detected.')
                except FileNotFoundError:
                    log_print('info', 'Directory ' + create_directory + ' not detected.  Creating directory.')
                    os.makedirs(create_directory)

            # Retrieving data for each end point.
            log_print('info', 'Retrieving data from API endpoint ' + endpoint + ' on host ' + host + '.')
            data = get('https://' + host + ':8089' + endpoint + '?count=0&search=' + search,
                       HTTPBasicAuth(admin_user, admin_pw), {'output_mode': 'json'}, cert_location)

            # Check if any results return.  If non return log it and move on.
            if len(data['entry']) == 0:
                log_print('info', 'API endpoint ' + endpoint + ' on host ' + host + ' did not have any objects.')
                continue
            else:
                log_print('info', 'API endpoint ' + endpoint + ' on host ' + host + ' retrieved ' +
                          str(len(data['entry'])) + ' objects.')
                # If results return then loop through them.
                for entry in data['entry']:
                    # Filtering entries that have not been updated since defined time
                    updated_epoch = time.mktime(time.strptime(re.sub(':(\d\d)$', '\g<1>', entry['updated']),
                                                              '%Y-%m-%dT%H:%M:%S%z'))

                    if updated_epoch < time_limit:
                        continue

                    log_print('info', 'Parsing data for object name ' + entry['name'] + ' from API endpoint ' +
                              endpoint + ' on host ' + host + ' for app ' + str(entry['acl']['app']))
                    # Creating dictionary of entry's fields of interests
                    try:
                        if endpoint in special_rules_endpoints:
                            object_data = special_handling_endpoints(endpoint, entry, fields)
                        else:
                            object_data = {}
                            for (key, value) in entry['content'].items():
                                if re.sub('(\.)[^$]+', '.', key) in fields and key != 'name':
                                    object_data[key] = value
                        name = re.sub('.+/([^/]+)', '\g<1>', entry['id'])
                        # Creating dictionary of entry's ACL's
                        acl_data = {}
                        for (key, value) in entry['acl'].items():
                            if key in fieldarray['acl']:
                                acl_data[key] = value
                        if entry['acl']['perms'] is None:
                            donothing = None
                        elif 'write' not in entry['acl']['perms'] and 'read' in entry['acl']['perms']:
                            acl_data['perms.read'] = entry['acl']['perms']['read']
                        elif 'read' not in entry['acl']['perms'] and 'write' in entry['acl']['perms']:
                            acl_data['perms.write'] = entry['acl']['perms']['write']
                        else:
                            acl_data['perms.read'] = entry['acl']['perms']['read']
                            acl_data['perms.write'] = entry['acl']['perms']['write']
                        acl_data['id'] = re.sub('(https?://)[^/]+', '', entry['id'])
                    except Exception as e:
                        log_print('error', 'Parsing data for object name ' + entry['name'] + ' from API endpoint ' +
                                  endpoint + ' on host ' + host + ' for app ' + str(entry['acl']['app']) +
                                  ' failed with error:\n' + str(e))
                        sys.exit()

                    log_print('info', 'Data successfully parsed for object name ' + name + ' from API endpoint ' +
                              endpoint + ' on host ' + host + ' for app ' + str(entry['acl']['app']))
                    # Writing results of object_data dictionary to the repo directory

                    directory = str(repo_location + '/' + str(entry['acl']['app']) + '/' +
                                    re.sub('.+/([^/]+/[^/]+)$', '\g<1>', endpoint))

                    # Removing any not allowed characters from filenames

                    name = re.sub('[/\\\:\*\?\"\<\>\|]', '_', name)
                    try:
                        if 'eai:data' in object_data and re.sub('.+/(ui)/.+', '\g<1>', endpoint) == 'ui':
                            file = directory + '/' + name + '.xml'
                            processed = process_file(object_data, file, name, endpoint)
                            if processed is True:
                                files_created['objects'].append(file)

                            if len(object_data) > 1:
                                file = directory + '/' + name + '.conf'
                                object_data_minus = {}
                                for (key,value) in object_data.items():
                                    if key != 'eai:data':
                                        object_data_minus[key] = value
                                processed = process_file(object_data_minus, file, name, endpoint)
                                if processed is True:
                                    files_created['objects'].append(file)

                        else:
                            file = directory + '/' + name + '.conf'
                            processed = process_file(object_data, file, name, endpoint)
                            if processed is True:
                                files_created['objects'].append(file)

                        # Writing results of acl_data dictionary to the repo directory
                        file = directory + '/' + name + '.acl'
                        processed = process_file(acl_data, file, name, endpoint)
                        if processed is True:
                            files_created['acls'].append(file)
                    except Exception as e:
                        log_print('error', 'Writing to disk for object name ' + name + ' from API endpoint ' +
                                  endpoint + ' on host ' + host + ' for app ' + str(entry['acl']['app']) +
                                  ' failed with error:\n' + str(e))
                        sys.exit()
    log_print('info', 'Completed processing all objects.  There were ' +
              str(len(files_created['objects']) + len(files_created['acls'])) + ' files created or updated in '
                                                                                'your repo.')

    # For loop that adds files to git and then commits them with provided commit message.
    failed_files = []
    for file in files_created['objects']:
        log_print('info', 'Adding ' + str(file) + ' to repo.')
        try:
            repo.index.add(os.path.abspath(file))
        except Exception as e:
            log_print('error', 'Attempt to add file ' + str(file) + ' to repo failed with error:\n' + str(e))
            failed_files.append(file)
            continue
    for file in files_created['acls']:
        log_print('info', 'Adding ' + str(file) + ' to repo.')
        try:
            repo.index.add(os.path.abspath(file))
        except Exception as e:
            log_print('error', 'Attempt to add file ' + str(file) + ' to repo failed with error:\n' + str(e))
            failed_files.append(file)
            continue
    if len(files_created['objects']) + len(files_created['acls']) > 0:
        log_print('info', 'Committing changes to repo with commit message "' + commit_message + '".')

        try:
            log_print('info', 'Commit command output: ' + str(repo.index.commit(commit_message)))
        except Exception as e:
            log_print('error',
                      'Commit attempt failed with the below error.  You will need to execute this commit on the '
                      'command line. No changes were pushed\n' + str(e))
            sys.exit()

        log_print('info', 'Pushing committed changes to repo.')

        try:
            log_print('info', 'Push command output: ' + str(repo.remotes.origin.push()))
        except Exception as e:
            log_print('error',
                      'Push attempt failed with the below error.  You will need to execute the push on the command'
                      'line after resolving any underlying issues in the error. No changes were pushed.\n' + str(e))
            sys.exit()
    else:
        log_print('info', 'No changes detected on any object.')

    if len(failed_files) > 0:
        log_print('info', 'Script has completed but the following files failed to load: ' + str(failed_files))
    else:
        log_print('info', 'Script has completed successfully with no errors.')


def special_handling_endpoints(endpoint, entry, fields):
    # Some endpoints require special rules for the data they return to be stored. Those endpoints are handled here.
    object_data = {}
    if endpoint == '/servicesNS/-/-/data/props/calcfields':
        for (key, value) in entry['content'].items():
            if re.sub('(\.)[^$]+', '.', key) in fields and key != 'name':
                object_data[key] = value
    elif endpoint == '/servicesNS/-/-/data/props/fieldaliases':
        for (key, value) in entry['content'].items():
            if re.sub('(\.)[^$]+', '.', key) in fields and key != 'name':
                object_data[key] = value
    elif endpoint == '/servicesNS/-/-/data/props/extractions':
        for (key, value) in entry['content'].items():
            if re.sub('(\.)[^$]+', '.', key) in fields and key != 'name' and key != 'type':
                object_data[key] = value
        object_data['type'] = re.sub('^(REPORT|EXTRACT)-[^$]+', '\g<1>', entry['content']['attribute'])
    elif endpoint == '/servicesNS/-/-/admin/tags':
        for (key, value) in entry['content'].items():
            if re.sub('(\.)[^$]+', '.', key) in fields and key != 'name':
                object_data[key] = value
        object_data['field_name'] = re.sub('^([^=]+)=[^$]+', '\g<1>', entry['content']['field_name_value'])
        object_data['field_value'] = re.sub('^[^=]+=([^$]+)', '\g<1>', entry['content']['field_name_value'])
    elif endpoint == '/servicesNS/-/-/data/props/lookups':
        for (key, value) in entry['content'].items():
            if re.sub('(\.)[^$]+', '.', key) in fields and key != 'name':
                object_data[key] = value
    elif object_data == {}:
        log_print('error', 'Special handling in code invoked but endpoint ' + str(endpoint) +
                  ' is not in the expected array to handle.')
        sys.exit()
    return object_data


def change_validation(object_data, file, endpoint):
    if file.endswith('.xml'):
        with open(file, 'r', encoding="utf-8") as read_file:
            data_import = read_file.read()
            read_file.close()
        if str(data_import) != str(object_data['eai:data']):
            return True
    elif file.endswith('.conf') or file.endswith('.acl'):
        with open(file, 'r', encoding="utf-8") as read_file:
            data_import = read_file.read()
            read_file.close()
        data_import = re.sub('([^\\\])\n', '\g<1>███', data_import).split("███")
        parsed_configs = {}
        for config in data_import:
            parsed_configs[str(re.sub('^(.+?) = .*', '\g<1>', config, flags=re.S))] = str(re.sub('^.+? = (.*)', '\g<1>', config, flags=re.S))
        parsed_config_no_empty = {}
        for (key, value) in parsed_configs.items():
            if key != '':
                parsed_config_no_empty[key] = re.sub('[\\\]\n', '\n', value)
        cleaned_object_data = {}
        for (key, value) in object_data.items():
            if key != 'eai:data' and re.sub('.+/(ui)/.+', '\g<1>', endpoint) == 'ui':
                cleaned_object_data[key] = value
            elif key != '':
                cleaned_object_data[key] = value
        common_keys = set(cleaned_object_data.keys()).intersection(set(parsed_config_no_empty.keys()))
        changes = {}
        for key in common_keys:
            if str(cleaned_object_data[key]) != str(parsed_config_no_empty[key]):
                changes[key] = {'api': cleaned_object_data[key], 'file': parsed_config_no_empty[key]}
        if len(cleaned_object_data) != len(parsed_config_no_empty) or len(changes) > 0:
            return True
    else:
        return False


def write_file(object_data, file):
    if file.endswith('.xml'):
        with open(file, 'w', encoding='utf-8') as datafile:
            datafile.write(str(object_data['eai:data']))
            datafile.close()
    elif file.endswith('.conf') or file.endswith('.acl'):
        with open(file, 'w', encoding='utf-8') as datafile:
            for (key, value) in object_data.items():
                if key != 'eai:data':
                    datafile.write(str(key) + ' = ' + re.sub('(\n)', '\\\\\g<1>', str(value)) + '\n')
            datafile.close()
    else:
        log_print('error', 'write_file function invoked with invalid parameters. File:' + str(file))
        sys.exit()


def process_file(object_data, file, name, endpoint):
    if os.path.exists(os.path.abspath(file)) is True:
        if change_validation(object_data, file, endpoint) is True:
            write_file(object_data, file)
            return True
        else:
            log_print('info', 'No change detected for object ' + name + ' in endpoint ' + endpoint)
            return False
    else:
        write_file(object_data, file)
        return True


if __name__ == '__main__':
    main()
