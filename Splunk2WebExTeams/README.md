# Splunk2WebExTeams

## What is Splunk2WebExTeams?

Splunk2WebExTeams is a python script that will make an API call to Splunk to search for triggered splunk alerts and then push a message to WebEx Teams if it detects the alerts being searched have triggered in the time frame being searched.  You can search for more than one alert and send to multiple rooms.  If more than one alert is detected, the message that is sent to each room will have a single messsage with a new line for each alert it detects.

### WARNING

If too many alerts are returned, it will not send a message to teams to prevent flooding a space with messages.

## How to use the script

Execute the script with `-h` to get a list of inputs and how they are intended to be used:


```
usage: Splunk2WebExTeams.py [-h] -splunk_host SPLUNK_HOST -user USER [-pw PW] -splunk_app SPLUNK_APP -owners OWNERS -webex_token WEBEX_TOKEN -cert_location CERT_LOCATION
                           [-custom_message CUSTOM_MESSAGE] [-freq_filter FREQ_FILTER] -search_name SEARCH_NAME -room_list ROOM_LIST

Script to poll splunk alerts to see if they triggered, and then push triggered alerts to WebEx Teams.

optional arguments:
  -h, --help            show this help message and exit
  -splunk_host SPLUNK_HOST
                        Splunk search head to poll for alerts.
  -user USER            User name to interact with splunk.
  -pw PW                Password for user. If not provided script will prompt for it.
  -splunk_app SPLUNK_APP
                        Splunk app that you want to poll alerts for. If more than one separate by commas.
  -owners OWNERS        Enter one or more alert owners in a comma separated list to limit the alerts that are retrieved. You can enter an asterisk to pull all users in
                        the chosen apps.
  -webex_token WEBEX_TOKEN
                        Enter the WebEx Bot bearer token associated to your WebEx Bot.
  -cert_location CERT_LOCATION
                        Provide directory to certificate location. Set to False if you want to send unsecured.
  -custom_message CUSTOM_MESSAGE
                        Provide message you want with pushed alert. Message always includes "Alert {alertname} has triggered. Please click this link to see the results."
                        at the beginning of the message. Custom message appends after that. Field supports markdown.
  -freq_filter FREQ_FILTER
                        Filter results that have not triggered in the last X minutes that you define here. Defaults to last 5 minutes if not here. Input only accepts
                        whole numbers.
  -search_name SEARCH_NAME
                        Name of search that you want to monitor for triggered alerts. If you have multiple alerts separate them with commas. If a comma is in an alert
                        name escape the comma with a backslash. If any of the search names contain a space the whole list of searches should be wrapped in double quotes.
                        Example: "alert for errors,alert for warnings, alerts\, warnings\, and fatal alerting" That would produce a list of three alerts with names "alert
                        for errors", "alert for warnings", and "alerts, warnings, and fatal alerting".
  -room_list ROOM_LIST  Provide comma separated list of room names you want to send alerts to. If a comma is in the room name, escape the comma with a backslash. If you
                        want to send to all rooms the user is currently in just enter an asterisk. This will only send to rooms the bot user is currently in. Script will
                        fail if the room(s) you provide is/are not found on the user's authorization token provided. Example: "My test bot room, General discussion\, and
                        other things" will produce a list of two rooms: "My test bot room" and "General discussion, and other things" If you need to trouble shoot a room
                        that is not showing up go to https://developer.webex.com/docs/api/v1/rooms/list-rooms and test what rooms return with the bearer token for your
                        splunk bot. This process is matching on the title field from that API response.
```