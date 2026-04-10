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
If the user is logged is an admin, it forces the backed to update its containers data (async)

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### organize_containers
#### /organize_containers
##### GET
If the user is logged is an admin, it shows the interface for organizing containers (docker and kubernetes)

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### add_container
#### /add_container
##### POST
##### requires the following in the form data: 'id', 'category', 'contacts', 'namespace', 'kind', 'severity', 'kind'
If the user is logged is an admin, it adds to the database a new container to be supervised

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### edit_container
#### /edit_container
##### POST
##### requires the following in the form data: 'id', 'category', 'contacts', 'namespace', 'kind', 'severity', 'kind'
If the user is logged is an admin, it edits the database to change a container to be supervised

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### delete_container
#### /delete_container
##### POST, DELETE (should be only DELETE in the future)
##### requires the following in the form data: 'psw', 'id'
If the user is logged is an admin, it deletes a container to be supervised from the database

If the user is not an admin, it's forbidden from doing the above

Wants the password of the user as a double security

Goes to login if user is not in session

---
### restart_logic_cronjob
#### /restart_logic_cronjob
##### POST
##### requires the following in the form data: 'cronjob_id'

If the user is logged is an admin, takes the related restart command for a cronjob identified by `cronjob_id` and runs it, possibly delegating it to a slave by calling its `/restart_logic_cronjob_slave` when applicable

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

If the user is logged is an admin, it performs the indicated cronjob now to get immediate results

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

If the user is logged is an admin, it shows the interface for organizing cronjobs

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

If the user is logged is an admin, it adds to the database a new cronjob to be performed periodically

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### edit_cronjob_new
#### /edit_cronjob_new
##### POST
##### requires the following in the form data: 'name', 'command', 'category', 'where_to_run' (optional), "disabled", 'restart', 'description', 'Timeout_timeAdd', 'RetriesAdd', 'Retries_waitAdd', 'IPAdd', 'TargetAdd', 'contacts', 'severity', 'id'

If the user is logged is an admin, it edits the database entry of a cronjob with the given `id`

If the user is not an admin, it's forbidden from doing the above

Goes to login if user is not in session

---
### delete_cronjob
#### /delete_cronjob
##### POST, DELETE (should be only DELETE in the future)
##### requires the following in the form data: 'psw', 'id'

If the user is logged is an admin, it deletes a cronjob from the database

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
##### POST (should be DELETE in the future, if it wasn't to be discontinued)

Discontinued due to cronjobs

---
### organize_tests
#### /organize_tests
##### GET

If the user is logged is an admin, it shows the interface for organizing tests (of containers)

If the user is not an admin, it's forbidden from doing the above

Returns 500 if the user is not in session

---
### add_test
#### /add_test
##### @app.route("/add_test", methods=["POST"])
---
### edit_test
#### /edit_test
##### @app.route("/edit_test", methods=["POST"])
---
### delete_test
#### /delete_test
##### @app.route("/delete_test", methods=["POST"])
---
### organize_complex_tests
#### /organize_complex_tests
##### @app.route("/organize_complex_tests", methods=["GET"])
---
### add_complex_test
#### /add_complex_test
##### @app.route("/add_complex_test", methods=["POST"])
---
### edit_complex_test
#### /edit_complex_test
##### @app.route("/edit_complex_test", methods=["POST"])
---
### delete_complex_test
#### /delete_complex_test
##### @app.route("/delete_complex_test", methods=["POST"])
---
### organize_categories
#### /organize_categories
##### @app.route("/organize_categories", methods=["GET"])
---
### add_category
#### /add_category
##### @app.route("/add_category", methods=["POST"])
---
### edit_category
#### /edit_category
##### @app.route("/edit_category", methods=["POST"])
---
### delete_category
#### /delete_category
##### @app.route("/delete_category", methods=["POST"])
---
### login
#### /login
##### @app.route("/login", methods=['GET', 'POST'])
---
### login_2
#### /login_2
##### @app.route("/login_2", methods=['GET', 'POST'])
---
### get_data_from_source
#### /get_data_from_source
##### @app.route("/get_data_from_source", methods=["GET"])
---
### get_complex_test_buttons
#### /get_complex_test_buttons
##### @app.route("/get_complex_test_buttons")
---
### container_is_okay
#### /container_is_okay
##### @app.route("/container_is_okay", methods=['POST'])
---
### read_containers
#### /read_containers
##### @app.route("/read_containers", methods=['POST'])
---
### read_containers_db
#### /read_containers_db
##### @app.route("/read_containers_db", methods=['GET'])
---
### run_test
#### /run_test
##### @app.route("/run_test", methods=['POST'])
---
### run_test_complex
#### /run_test_complex
##### @app.route("/run_test_complex", methods=['POST'])
---
### test_all_ports
#### /test_all_ports
##### @app.route("/test_all_ports", methods=['GET'])
---
### deauthenticate
#### /deauthenticate
##### @app.route("/deauthenticate", methods=['POST','GET'])
---
### reboot_container
#### /reboot_container
##### @app.route("/reboot_container", methods=['POST'])
---
### get_muted_components
#### /get_muted_components
##### @app.route("/get_muted_components", methods=['GET'])
---
### mute_component_by_hours
#### /mute_component_by_hours
##### @app.route("/mute_component_by_hours", methods=['POST'])
---
### cronjobs
#### /cronjobs
##### @app.route("/cronjobs", methods=['POST', 'GET'])
---
### tests_results
#### /tests_results
##### @app.route("/tests_results", methods=['POST'])
---
### get_complex_tests
#### /get_complex_tests
##### @app.route("/get_complex_tests", methods=["GET"])
---
### container/<podname>
#### /container/<podname>
##### @app.route("/container/<podname>", methods=['POST'])
---
### cronjobs_logs
#### /cronjobs_logs
##### @app.route("/cronjobs_logs", methods=["POST", "GET"])
---
### advanced-container/<container_name>
#### /advanced-container/<container_name>
##### @app.route("/advanced-container/<container_name>")
---
### get_summary_status
#### /get_summary_status
##### @app.route("/get_summary_status")
---
### generate_pdf
#### /generate_pdf
##### @app.route("/generate_pdf", methods=['GET'])
---
### download
#### /download
##### @app.route("/download")
---
### downloads/
#### /downloads/
##### @app.route("/downloads/")
---
### downloads/<path:subpath>
#### /downloads/<path:subpath>
##### @app.route("/downloads/<path:subpath>")
---
### certification
#### /certification
##### @app.route("/certification", methods=['GET'])
---
### clustered_certification
#### /clustered_certification
##### @app.route("/clustered_certification", methods=['GET'])
---
### certification_mk3
#### /certification_mk3
##### @app.route("/certification_mk3", methods=['GET'])
---
### snmp_info
#### /snmp_info
##### @app.route("/snmp_info", methods=["GET"])
---
### organize_configuration_retrieval
#### /organize_configuration_retrieval
##### @app.route("/organize_configuration_retrieval", methods=["GET"])
---
### add_configuration_retrieval
#### /add_configuration_retrieval
##### @app.route("/add_configuration_retrieval", methods=["POST"])
---
### edit_configuration_retrieval
#### /edit_configuration_retrieval
##### @app.route("/edit_configuration_retrieval", methods=["POST"])
---
### delete_configuration_retrieval
#### /delete_configuration_retrieval
##### @app.route("/delete_configuration_retrieval", methods=["POST"])
---
