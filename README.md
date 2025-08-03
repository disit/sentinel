# Snap4Sentinel (kubernetes)

## Setting up

### Users and passwords

The script `generate_passwords.py` will guide you while generating the accounts for Snap4Sentinel

These are then saved in `users.txt`, in the same folder as that this readme (and script)

There's an existing file which holds the account `admin:admin`

If you are using the kubernetes version, mount the file on `/app/users.txt`, otherwise the above mentioned file will be used instead

The `k8s.yaml` file already prepares the mounting, so just put the correct path in the persistent volume

### Setting up the yaml

Review the environment variables set in `k8s.yaml` before proceeding; for Snap4Sentinel they all have an explanation, for the database it's a normal mysql database

To setup the database on first start, mount `dump k8s.sql` into the database; as for the users, this is already prepared in `k8s.yaml`. Volumes are setup already, but you might want to edit the paths

If you are using the files found in git, they will have the Snap4City placeholders left unset; you should consider generating a distribution instead


Alternatively, you can do something like this:

```bash
#!/bin/bash

# From the position of this script
base_dir="."
# Read the placeholder file found here
tsv_file="/path/for/placeholder_used.tsv"

# Loop through the placeholders in placeholder_used.tsv
grep '^\$#' "$tsv_file" | while IFS=$'\t' read -r pattern replacement; do # some lines do not represent placeholders and we won't read them

    # Escape special characters for regex in sed
    escaped_pattern=$(printf '%s\n' "$pattern" | sed 's/[][\\/.*^$]/\\&/g')
    escaped_replacement=$(printf '%s\n' "$replacement" | sed 's/[&/\]/\\&/g')

    # Find all files (excluding placeholder_used.tsv if it is there) and run sed on them
    find "$base_dir" -type f ! -name "placeholder_used.tsv" -exec sed -i "s/$escaped_pattern/$escaped_replacement/g" {} +
done
```
This assumes the script is ran where the sentinel files are located, in the folder where you can find `flask_unified.py`; it will replace the placeholders with the intended values

### Services, Deployments and other Kubernetes resources

All resources are already created, _except_ for the namespace, which you must create yourself. `sentinel-namespace` is fine. As mentioned before, check for volume mounting and environment variables

## Starting Snap4Sentinel

### Apply the yaml

```bash
#!/bin/bash
kubectl apply -f k8s.yaml -n your-namespace
```

This will load the resources, and eventually get them working

### Accessing Snap4Sentinel

A service for each of the deployment is created, but a random port is assigned to them; to see it, for example, run:
```bash
#!/bin/bash
kubectl get svc -n your-namespace
```
Then look for sentinel-service as the service, and at the column Ports you'll see 9080:12345; Snap4Sentinel is reachable from port 12345 on the given host over http

## Using Snap4Sentinel

### Assigning a container/pod to a category

In the main web interface, go to Show Administrative Actions and select Manage Containers. In the newly opened page you'll see the currently managed containers; from there you can add and delete new containers. `*` in the name of the container will wildcard for each other characters following it (e.g. `iotapp-*` will match all iotapps, `dashboarddb-*` will catch kubernetes dashboarddb pods regardless of the randomly generated substring appended to the deployment name).

### Adding, editing or deleting a test (a isalive test), a complex test (anything specific to a category), a cronjob (anything specific to a category, which also repeats once each 5 minutes) or a new category

These actions can only be done by accessing the database manually or by enabling unsafe mode in the enviroment of Snap4Sentinel. For the administrator, the actions are available in Show Administrative Actions. As per date 01/08/2025, all but category related actions have been tested and found functioning. In-web examples and explanations are yet to be added.