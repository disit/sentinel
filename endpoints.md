# Endpoints Documentation: Sentinel

Welcome to the Sentinel Endpoints. Sentinel provides aggregated docker, kubernetes and other kind of processes data to ensure that everything is working as intended; when it doesn't it sends emails and telegram messages as notifications.

---

## Base URL
`http://sentinel:8080`, probably. It depends on your setup.

---

## Authentication
With session against masters, with jwt when masters communicate with slaves

---

## Endpoints

### Main page
#### /
##### GET
Redirects to login if no session found, shows main page for logged in users (slightly different between admins and users)

---
### get_local_top
#### /get_local_top
##### GET
Returns a top, which is different if the sentinel instance is running on docker or kubernetes, goes to login if user is not in session

---
### get_top
#### /get_top
##### GET
Deprecated, to be removed in future versions

---
### refresh_containers_database
#### /refresh_containers_database
##### GET
If the user logged is an admin, it forces the backed to update its containers data (async)

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### organize_containers
#### /organize_containers
##### GET
If the user logged is an admin, it shows the interface for organizing containers (docker and kubernetes)

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### add_container
#### /add_container
##### POST
##### requires the following in the form data: 'id', 'category', 'contacts', 'namespace', 'kind', 'severity', 'kind'
If the user logged is an admin, it adds to the database a new container to be supervised

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### edit_container
#### /edit_container
##### POST
##### requires the following in the form data: 'id', 'category', 'contacts', 'namespace', 'kind', 'severity', 'kind'
If the user logged is an admin, it edits the database to change a container to be supervised

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### delete_container
#### /delete_container
##### POST, DELETE (should be only DELETE in the future)
##### requires the following in the form data: 'psw', 'id'
If the user logged is an admin, it deletes a container to be supervised from the database

If the user is not an admin, it's forbidden from doing the above

Wants the password of the user as a double security

Goes to login if user is not in session

---
### restart_logic_cronjob
#### /restart_logic_cronjob
##### POST
##### requires the following in the form data: 'cronjob_id'

If the user logged is an admin, takes the related restart command for a cronjob identified by `cronjob_id` and runs it, possibly delegating it to a slave by calling its `/restart_logic_cronjob_slave` when applicable

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### restart_logic_cronjob_slave
#### /restart_logic_cronjob_slave
##### POST

Called by a master when a cronjob running on a slave must be restarted

---
### run_specific_cronjob
#### /run_specific_cronjob
##### POST
##### requires the following in the form data: 'cronjob_id'

If the user logged is an admin, it performs the indicated cronjob now to get immediate results

If the user is not an admin, it's forbidden from doing the above

Returns 500 if the user is not in session

---
### organize_cronjobs
#### /organize_cronjobs
##### GET
Deprecated

---
### organize_cronjobs_new
#### /organize_cronjobs_new
##### GET

If the user logged is an admin, it shows the interface for organizing cronjobs

If the user is not an admin, it's forbidden from doing the above

Returns 500 if the user is not in session

---
### add_cronjob
#### /add_cronjob
##### POST
Deprecated

---
### edit_cronjob
#### /edit_cronjob
##### POST
Deprecated

---
### add_cronjob_new
#### /add_cronjob_new
##### POST
##### requires the following in the form data: 'name', 'command', 'category', 'where_to_run' (optional), "disabled", 'restart', 'description', 'Timeout_timeAdd', 'RetriesAdd', 'Retries_waitAdd', 'IPAdd', 'TargetAdd', 'contacts', 'severity'

If the user logged is an admin, it adds to the database a new cronjob to be performed periodically

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### edit_cronjob_new
#### /edit_cronjob_new
##### POST
##### requires the following in the form data: 'name', 'command', 'category', 'where_to_run' (optional), "disabled", 'restart', 'description', 'Timeout_timeAdd', 'RetriesAdd', 'Retries_waitAdd', 'IPAdd', 'TargetAdd', 'contacts', 'severity', 'id'

If the user logged is an admin, it edits the database entry of a cronjob with the given `id`

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### delete_cronjob
#### /delete_cronjob
##### POST, DELETE (should be only DELETE in the future)
##### requires the following in the form data: 'psw', 'id'

If the user logged is an admin, it deletes a cronjob from the database

If the user is not an admin, it's forbidden from doing the above

Wants the password of the user as a double security

Goes to login if user is not in session

---
### organize_extra_resources
#### /organize_extra_resources
##### GET

Discontinued due to cronjobs

---
### add_extra_resource
#### /add_extra_resource
##### POST

Discontinued due to cronjobs

---
### edit_extra_resource
#### /edit_extra_resource
##### POST

Discontinued due to cronjobs

---
### delete_extra_resource
#### /delete_extra_resource
##### POST, DELETE (should be DELETE in the future, if it wasn't to be discontinued)

Discontinued due to cronjobs

---
### organize_tests
#### /organize_tests
##### GET

If the user logged is an admin, it shows the interface for organizing tests (of containers)

If the user is not an admin, it's forbidden from doing the above

Returns 500 if the user is not in session

---
### add_test
#### /add_test
##### POST
##### requires the following in form data: 'container_name', 'command', 'command_explained'

If the user logged is an admin, it adds to the database a new test (related to a container) to be performed periodically

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### edit_test
#### /edit_test
##### POST
##### requires the following in form data: 'container_name', 'command', 'command_explained', 'id'

If the user logged is an admin, it edits the database entry of a test with the given `id`

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### delete_test
#### /delete_test
##### POST, DELETE (should be only delete in the future)
##### requires the following in the form data: 'psw', 'id'

If the user logged is an admin, it deletes a test from the database

If the user is not an admin, it's forbidden from doing the above

Wants the password of the user as a double security

Goes to login if user is not in session

---
### organize_complex_tests
#### /organize_complex_tests
##### GET

If the user logged is an admin, it shows the interface for organizing complex tests (of categories)

If the user is not an admin, it's forbidden from doing the above

Returns 500 if the user is not in session

---
### add_complex_test
#### /add_complex_test
##### POST
##### requires the following in the form data: 'name', 'command', 'extra_parameters', 'button_color', 'explanation', 'category'

If the user logged is an admin, it adds to the database a new complex test (related to a category) to be performed on demand

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### edit_complex_test
#### /edit_complex_test
##### POST
##### requires the following in form data: 'name', 'command', 'extra_parameters', 'button_color', 'explanation', 'category', 'id'

If the user logged is an admin, it edits the database entry of a complex test with the given `id`

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### delete_complex_test
#### /delete_complex_test
##### POST, DELETE (should be only delete in the future)
##### requires the following in the form data: 'psw', 'id'

If the user logged is an admin, it deletes a complex test from the database

If the user is not an admin, it's forbidden from doing the above

Wants the password of the user as a double security

Goes to login if user is not in session

---
### organize_categories
#### /organize_categories
##### GET

If the user logged is an admin, it shows the interface for organizing categories

If the user is not an admin, it's forbidden from doing the above

Returns 500 if the user is not in session

---
### add_category
#### /add_category
##### POST
##### requires the following in the form data: 'category'

If the user logged is an admin, it adds to the database a new category

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### edit_category
#### /edit_category
##### POST
##### requires the following in the form data: 'category', 'id'

If the user logged is an admin, it edits the database entry of a category with the given `id`

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### delete_category
#### /delete_category
##### POST, DELETE (should be only delete in the future)
##### requires the following in the form data: 'password', 'id'

If the user logged is an admin, it deletes a category from the database

If the user is not an admin, it's forbidden from doing the above

Wants the password of the user as a double security

Goes to login if user is not in session

---
### login
#### /login
##### GET, POST
##### requires the following in the form data in POST: 'password', 'username'

The GET returns the login page, the POST attempts the login with username and password

---
### login_2
#### /login_2
##### GET, POST
##### requires the following in the form data in POST: 'password', 'username'

Not yet used, as above but prints errors to webpage, if any

---
### get_data_from_source
#### /get_data_from_source
##### GET
##### requires the following in the form data in GET: 'id'

Extra resource internal resolution, discontinued due to cronjobs

---
### get_complex_test_buttons
#### /get_complex_test_buttons
##### GET

Called by the main ui, get the buttons, still not mainly used

---
### container_is_okay
#### /container_is_okay
##### POST
##### requires the following in the form data in GET: 'container'

Actually never called

---
### read_containers
#### /read_containers
##### POST (should be a GET maybe?)

Gets real time container data

---
### read_containers_db
#### /read_containers_db
##### GET

Gets container data from db

---
### run_test
#### /run_test
##### POST
##### requires the following in the form data: 'container'

Runs the test of the given container, returns results (and saves them)

---
### run_test_complex
#### /run_test_complex
##### POST
##### requires the following in the form data: 'test_name'

As above, but a complex test instad of a test

---
### test_all_ports
#### /test_all_ports
##### GET

Runs all tests of containers

---
### deauthenticate
#### /deauthenticate
##### POST, GET (probably can be compressed to just one method)

Clears the session

---
### reboot_container
#### /reboot_container
##### POST
##### requires the following in the form data: 'psw', 'id'

Restarts a container (docker) or issues a rollout (kubernetes) with the given name. Will call itself across nodes of the sentinel cluster. 

---
### get_muted_components
#### /get_muted_components
##### GET

Unused functionality

---
### mute_component_by_hours
#### /mute_component_by_hours
##### POST

Unused functionality

---
### cronjobs
#### /cronjobs
##### POST, GET

Gets the lastest cronjob results, over 2 methods because main UI reasons

---
### tests_results
#### /tests_results
##### POST

As above, shoult be a GET but the UI demands otherwise, tests over cronjobs

---
### get_complex_tests
#### /get_complex_tests
##### GET

As above, complex tests over tests

---
### container/<podname\>
#### /container/<podname\>
##### POST

Gets the logs of the container/pod in path, shoult be a GET but the UI demands otherwise

---
### cronjobs_logs
#### /cronjobs_logs
##### POST, GET (should be only GET in the future)

As above, but for cronjobs executions

---
### get_summary_status
#### /get_summary_status
##### GET

Never called, it is retrieved someplace else

---
### generate_pdf
#### /generate_pdf
##### GET

Gets a lot of data from the envirnoment of containers, crnojobs, etc.. , puts it into a pdf, and returns it to the user

---
### download
#### /download
##### @app.route("/download")
### downloads/
#### /downloads/
##### @app.route("/downloads/")
### downloads/<path:subpath>
#### /downloads/<path:subpath>
##### @app.route("/downloads/<path:subpath>")

Endpoints to show stored filepaths and downloads files

---
### certification
#### /certification
##### GET

Deprecated

---
### clustered_certification
#### /clustered_certification
##### GET

Deprecated

---
### certification_mk3
#### /certification_mk3
##### GET

Generates then sends a certification

---
### hosts_control_panel
#### /hosts_control_panel
##### GET

If the user logged is an admin, it shows the interface for hosts (top view)

If the user is not an admin, it's forbidden from doing the above

Goes to login if the user is not in session

---
### connect_host
#### /connect_and_store
##### POST
##### requires the following in the form data: 'host', 'user', 'psw', 'description', 'cpu', 'mem'

If the user logged is an admin, it adds a new host to the database, but not before establishing a connection and storing the ssh keys

If the user is not an admin, it's forbidden from doing the above

Goes to login if the user is not in session

---
### run_command
#### /run_command_host
##### POST
##### requires the following in the form data: 'host'

Currently unused and is hardcoded to ignore relevant data

Would run a command to the given host with ssh

---

### delete_saved_host
#### /delete
##### POST, DELETE (should be only DELETE in the future)

If the user logged is an admin, it deletes the host from the db data and then deletes the keys

If the user is not an admin, it's forbidden from doing the above

Goes to login if the user is not in session

---
### get_containers_severity
#### /get_containers_severity
##### GET

Gets the severity of each container

Goes to login if the user is not in session

---
### get_host_tops
#### /get_tops
##### GET

For each host, gets the top, then add the top from itself (the container running sentinel), unless they are not the admin, in which case they are forbidden

Goes to login if the user is not in session

---
### sentinel_hosts_control_panel
#### /sentinel_hosts_control_panel
##### GET

If the user logged is an admin, it shows the interface for hosts (top view), mostly unused now that hosts can self register as slaves

If the user is not an admin, they are forbidden from doing so

Goes to login if the user is not in session

---
### add_sentinel_host
#### /add_sentinel_host
##### POST
##### requires the following in the form data: 'hostname', 'ip' (hostname should be something else, like hostpath)

If the user logged is an admin, it adds a new sentinel element to the cluster, mostly unused now that hosts can self register as slaves

If the user is not an admin, they are forbidden from doing so

Goes to login if the user is not in session

---
### delete_sentinel_host
#### /delete_sentinel_host
##### DELETE, POST (should probably only be DELETE)
##### requires the following in the form data: 'hostname' (hostname should be something else, like hostpath)

If the user logged is an admin, it deletes a sentinel element from the cluster

If the user is not an admin, they are forbidden from doing so

Goes to login if the user is not in session

---
### snmp_control_panel
#### /snmp_control_panel
##### GET

If the user logged is an admin, it shows the interface for hosts using snmp

If the user is not an admin, they are forbidden from doing so

Goes to login if the user is not in session

---
### add_snmp
#### /add_snmp
##### POST
##### requires the following in the form data: 'user', 'description', 'details', 'cpu', 'mem', 'protocol', 'host', 'PrivKey', 'AuthKey'

If the user logged is an admin, it adds a new snmp host to the cluster

If the user is not an admin, they are forbidden from doing so

Goes to login if the user is not in session

---
### delete_snmp_host
#### /delete_snmp_host
##### DELETE, POST (should probably only be DELETE)
##### requires the following in the form data: 'host' 

If the user logged is an admin, it deletes a snmp host

If the user is not an admin, they are forbidden from doing so

Goes to login if the user is not in session

---

### snmp_info
#### /snmp_info
##### GET
##### requires the following in the form data: 'host' 


If the user logged is an admin, it shows, disk, memory and cpu details with snmp from host

If the user is not an admin, they are forbidden from doing so

Goes to login if the user is not in session

---
### organize_configuration_retrieval
#### /organize_configuration_retrieval
##### GET

If the user logged is an admin, it shows the interface for organizing configuration retrievals

If the user is not an admin, they are forbidden from doing so

Goes to login if the user is not in session

---
### add_configuration_retrieval
#### /add_configuration_retrieval
##### POST
##### requires the following in the form data: 'host', 'path', 'what', 'options'

If the user logged is an admin, it adds a new retrieval for configurations

If the user is not an admin, they are forbidden from doing so

Goes to login if the user is not in session

---
### edit_configuration_retrieval
#### /edit_configuration_retrieval
##### POST
##### requires the following in the form data: 'password', 'id'

If the user logged is an admin, it edits a retrieval for configurations with the given id

If the user is not an admin, they are forbidden from doing so

Goes to login if the user is not in session

---
### delete_configuration_retrieval
#### /delete_configuration_retrieval
##### POST, DELETE (should only be DELETE in the future)

If the user logged is an admin, it deletes a retrieval for configurations with the given id

If the user is not an admin, they are forbidden from doing so

Goes to login if the user is not in session

---
