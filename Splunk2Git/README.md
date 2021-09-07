# Splunk2Git

## What is Splunk2Git?

This script currently has functionality to export shared Splunk assets from any Splunk app and user combination to your local git repository on your machine.

## What is git?

If you don't know what git is, you can learn more about what git is [here](https://www.git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F). Git is a distributed revision control and source code management system. This script requires you to already have git installed and properly configured to function with your repository.

## Requirements

The scripts in this repo require git installed and set up on the machine executing the script as mentioned above and the below Python libraries installed in your Python environment:

* requests
* gitpython

If your Python environment does not have these installed you can run the below commands to install them:

```
python3 -m pip install requests
python3 -m pip install gitpython
```

Additionally this script is not backwards compatible with python 2.

## How to run

To get help just run `python3 Splunk2Git.py -h` and the below output will explain the different arguments that are required:

```
usage: Splunk2Git.py [-h] -splunk_host SPLUNK_HOST -user USER [-pw PW] -splunk_app SPLUNK_APP -repo_location REPO_LOCATION
                             -owners OWNERS -cert_location CERT_LOCATION -git_branch GIT_BRANCH [-checkout_branch {Y,N}]
                             [-commit_message COMMIT_MESSAGE] [-days_filter DAYS_FILTER]

Script to pull down splunk objects and push them to a bitbucket/git repository. This only retrieves objects that are visible to
other users.

optional arguments:
  -h, --help            show this help message and exit
  -splunk_host SPLUNK_HOST
                        Splunk search head to retrieve objects from. If more than one, separate by commas.
  -user USER            User name to interact with splunk.
  -pw PW                Password for user. If not provided script will prompt for it.
  -splunk_app SPLUNK_APP
                        Splunk app that you want to pull down objects for. If more than one separate by commas.
  -repo_location REPO_LOCATION
                        BitBucket repo location on machine executing the script. Must contain a .git folder.
  -owners OWNERS        Enter one or more object owners in a comma separated list to limit what objects you retrieve. You can
                        enter an asterisk to pull all users in the chosen apps.
  -cert_location CERT_LOCATION
                        Provide directory to certificate location. Set to False if you want to send unsecured.
  -git_branch GIT_BRANCH
                        Provide git branch you want to push the data to.
  -checkout_branch {Y,N}
                        If currently checked out branch is not the provided branch and you want the script to check out the input
                        branch put "Y" here. Defaults to N if not provided. This is NOT recommended to use with "Y" unless you are
                        sure you have no pending commits.
  -commit_message COMMIT_MESSAGE
                        Provide message you want with the commit. Defaults to "Splunk to Bitbucket python script" if not provided.
  -days_filter DAYS_FILTER
                        Filter objects that have only been updated in the last number of days you input here. Defaults to last
                        7 days if not here. Inputting "all time" will pull everything. Input only accepts whole numbers or "all
                        time"
```

## How does this work?

This script queries the Splunk API endpoints to retrieve the assets that correspond to the users and apps selected when executed. It then parses through the results of that call, pulls out the data from the required fields, and then writes that data to files. Each object will have at least two files written. For most endpoints it will be a `.conf` file that has the actual configurations for that asset and a `.acl` file that has the permissions associated to that asset. For some endpoints that are in the UI directory, the data is in an xml format and the file is saved as a `.xml` file then. Examples of this are Splunk dashboards and app UI menus.

The directory structure will mirror the API endpoints. Below is a chart that shows the name that corresponds to the directory:

Asset Type | Folder directory
:---------- | :----------------
dashboards | /ui/views
calculated fields | /props/calcfields
field aliases | /props/fieldaliases
field transformations | /transforms/extractions
field extractions | /props/extractions
sourcetype renaming | /props/sourcetype-rename
workflow actions | /ui/workflow-actions
time ranges | /ui/times
saved searches/alerts/reports | /saved/searches
data models | /data/models
event types | /saved/eventtypes
list by field value pair | /saved/fvtags
list by tag name | /saved/ntags
tags | /admin/tags
lookup definitions | /transforms/lookups
automatic lookups | /props/lookups
app UI menus | /ui/nav
pre-built panels | /ui/panels
search macros | /admin/macros


Once the data has been laid down in your local repo's directory, the gitpython library will add each file that is written individually to git. It will then run a commit with the comment you input in that argument when you execute the script. If no argument is provided the commit will be "Splunk to git python script." Once the commit completes it pushes the commit to the selected branch you input when executing the script.
