#!/usr/bin/env python3

try:
    import time
    import datetime
    import digitalocean
    import requests
    import math
    import json
    import re
    import os
    import smtplib
    from email.mime.text import MIMEText
    import asdf
except ImportError as err:
    with open("server.log", "a") as log:
        log.write(err.msg + "\n")
    raise

# TODO: Install these imports (esp digitalocean) in the install

# Defaults, get overwritten with config file
MAX_DROPLETS = 100
POLL_PERIOD = 30
TOKEN = "supersecretkeyhere"
IMAGE_NAME = 0              # TODO: If this is not specified in the config file, make it the ID of the most recent wordpress snapshot
BASE_NAME = "wp-clone"
ONE_MIN = 0
FIVE_MIN = 1
TEN_MIN = 2
LOAD_PER_DROPLET = 1
EMAIL = "user@example.com"


# Get the IP address, get the load, put the 1m, 5m, and 10m avg loads in a list and append it to the droplet object
def get_loads(droplet):
    try:
        r = requests.get("http://" + droplet.ip_address + "/load.php")
        droplet.loadavg = [float(l) for l in r.text.split(' ')[:3]]
    except:
        # TODO: Somehow report this error
        pass


# Reads in the current list of IP addresses from
def get_load_balancer_IPs():
    ips = []
    with open("/etc/nginx/nginx.conf") as fin:
        for line in fin:
            if re.search(r"server [0-9]+(?:\.[0-9]+){3}", line):
                ips.append(re.search(r"[0-9]+(?:\.[0-9]+){3}", line)[0])

    return ips


# Sends an email to me
def send_email(msg):
    email = MIMEText("\n" + msg + "\n")
    email['Subject'] = "Text message"
    email['To'] = EMAIL
    email['From'] = "postmaster@%s" % os.uname().nodename
    s = smtplib.SMTP('localhost')
    s.ehlo()


# Updates the Nginx load balancer config file and restarts Nginx
def write_load_balancer_IPs(addresses):
    output = ""

    with open("/etc/nginx/nginx.conf", 'r') as fin:

        # Read in the old load balancer and copy all the lines before the IP addresses
        line = fin.readline()
        while not re.search(r"server [0-9]+(?:\.[0-9]+){3}", line):
            output += line
            line = fin.readline()

        # Write in the new addresses
        for ip in addresses:
            output += "\t\tserver " + ip + ":443;\n"

        # Skip the old ip addresses in the file
        while re.search(r"server [0-9]+(?:\.[0-9]+){3}", line):
            line = fin.readline()

        # Copy the rest of the lines
        while line:
            output += line
            line = fin.readline()

    # Update the conf file
    with open("/etc/nginx/nginx.conf", 'w') as fout:
        fout.write(output)

    # Restart the nginx server
    os.system("systemctl reload nginx.service")


# Request create of new droplets
def create_droplets(num):
    # Create list of names for new droplets
    names = [BASE_NAME] * num

    # TODO: Error handling
    digitalocean.Droplet.create_multiple(token=TOKEN, names=names, size="s-1vcpu-1gb", image=IMAGE_NAME, region="nyc3",
                                         backups=False, ipv6=True, private_networking=None, tags=["website"])


# Request deletion of droplets
def delete_droplets(num, droplets):
    droplets.sort(key=lambda d: d.created_at)

    # Delete the oldest clones (but never the prime droplet)
    i = 0
    for d in droplets[:num]:
        d.destroy()
        i += 1

    return i


# Get info from all website droplets, return them sorted by ones running and ones being started.
# Running droplets will be polled for average load
def get_droplets(manager):
    try:
        droplets = manager.get_all_droplets(tag_name="website")
    except Exception as err:
        with open("server.log", "a") as log:
            log.write(err)

    active_droplets = list(filter(lambda d: d.status == 'active', droplets))
    new_droplets = list(filter(lambda d: d.status == 'new', droplets))

    for d in active_droplets:
        get_loads(d)

    return active_droplets, new_droplets


# Program starts here
with open("config.json", 'r') as readin:
    data = json.load(readin)

    if "max_droplets" in data:
        MAX_DROPLETS = data["max_droplets"]
    if "poll_period" in data:
        POLL_PERIOD = data["poll_period"]
    if "token" in data:
        TOKEN = data["token"]
    if "image_name" in data:
        IMAGE_NAME = data["image_name"]
    if "base_name" in data:
        BASE_NAME = data["base_name"]
    if "email" in data:
        EMAIL = data["email"]
    if "load_per_droplet" in data:
        LOAD_PER_DROPLET = data["load_per_droplet"]

# Write to log file that server is starting
with open("server.log", "a") as log:
    log.write(str(datetime.datetime.now()) + ": Starting server\n")

manager = digitalocean.Manager(token=TOKEN)

if IMAGE_NAME == 0:
    # If image ID not specified, default is the most recent wordpress snapshot
    snapshots = list(filter(lambda w: w.name.find("wordpress") == 0, manager.get_all_snapshots()))
    IMAGE_NAME = int(max(snapshots, key=lambda s: s.created_at).id)

droplet_status = (0,0,0)
try:
    while True:
        # Get list of all web server droplets, both running and ones being provisioned. Get the average load of ones running
        active_droplets, inprogress_droplets = get_droplets(manager)

        # Sort out any non-responsive droplets
        unresponsive_droplets = list(filter(lambda d: not hasattr(d, 'loadavg'), active_droplets))
        active_droplets = list(filter(lambda d: hasattr(d, 'loadavg'), active_droplets))

        # Sort lists by creation date
        active_droplets.sort(key=lambda d : d.created_at)
        inprogress_droplets.sort(key=lambda d : d.created_at)
        unresponsive_droplets.sort(key=lambda d : d.created_at)

        # TODO: Do some health check on unresponsive droplets. Maybe it's a fluke, maybe they crashed

        # Write to log file what the status of droplets are (assuming the counts have changed
        if droplet_status != (len(inprogress_droplets), len(active_droplets), len(unresponsive_droplets)):
            droplet_status = (len(inprogress_droplets), len(active_droplets), len(unresponsive_droplets))
            with open("server.log", "a") as log:
                log.write(str(datetime.datetime.now())
                          + ": %d droplets winding up, %d droplets running, %d droplets unresponsive\n" % droplet_status)

        # Find the total load on the cluster from the last minute average
        recent_load = sum([d.loadavg[ONE_MIN] for d in active_droplets])
        if recent_load == 0:     # In case there's no active droplets, set the load > 1 to trick the provisioning algorithm
            recent_load = 0.01

        # Find the total load using the highest load (1min, 5min, 10min) from each droplet
        prolonged_load = sum([max(d.loadavg) for d in active_droplets])
        if recent_load == 0:     # If the prolonged_load is 0, the elif below might accidentally delete the prime droplet
            recent_load = 0.01

        # Each droplet should have a load of no more than 1. If the total load exceeds the number of available droplets
        # (plus ones on the way), provision more
        num_usable_droplets = len(active_droplets) + len(inprogress_droplets)
        total_droplets = num_usable_droplets + len(unresponsive_droplets)
        if recent_load > num_usable_droplets * LOAD_PER_DROPLET:
            num_to_create = math.ceil(recent_load) - num_usable_droplets * LOAD_PER_DROPLET

            # There shouldn't be more than MAX_DROPLETS provisioned
            if num_to_create + total_droplets > MAX_DROPLETS:
                num_to_create = MAX_DROPLETS - total_droplets
                # TODO: Word the email differently if this is the case

            # TODO: Send an email that x droplets are being provisioned

            # Write to log file that droplets are being created
            with open("server.log", "a") as log:
                log.write(str(datetime.datetime.now()) + ": %d droplets ordered for creation. Total 1m load: %.2f\n"
                          % (num_to_create, recent_load))

            create_droplets(num_to_create)

        elif prolonged_load < (len(active_droplets) - 1) * LOAD_PER_DROPLET:
            num_to_delete = len(active_droplets) * LOAD_PER_DROPLET - math.ceil(prolonged_load)

            # Write to log file that droplets are being deleted
            with open("server.log", "a") as log:
                log.write(str(datetime.datetime.now()) + ": %d droplets ordered for deletion. Total 1m load: %.2f\n"
                          % (num_to_delete, recent_load))

            # Delete droplets, starting with the unresponsive ones
            deleted = delete_droplets(num_to_delete, unresponsive_droplets)
            deleted = delete_droplets(num_to_delete - deleted, active_droplets[1:])
            active_droplets = [active_droplets[0]] + active_droplets[1:deleted+1]

        # Compare list of active droplets with list of IP addresses in nginx conf file.
        # Update conf file and restart if appropriate
        conf_ips = get_load_balancer_IPs()
        active_ips = [d.private_ip_address for d in active_droplets]
        conf_ips.sort()
        active_ips.sort()
        if conf_ips != active_ips and len(active_ips) > 0:  # If the lists mismatch and not because of unresponsive droplets
            write_load_balancer_IPs(active_ips)

            # Write to log file that Nginx conf file was updated
            with open("server.log", "a") as log:
                log.write(str(datetime.datetime.now()) + ": nginx.conf was updated\n")

        time.sleep(POLL_PERIOD)
except Exception as err:
    with open("server.log", "a") as log:
        log.write(err)