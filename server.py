import digitalocean
import requests
import math
import json

# Defaults, get overwritten with config file
MAX_DROPLETS = 100
POLL_PERIOD = 30
TOKEN = "supersecretkeyhere"
IMAGE_NAME = 50005064
BASE_NAME = "wp-clone-%d"
ONE_MIN = 0
FIVE_MIN = 1
TEN_MIN = 2


# Get the IP address, get the load, put the 1m, 5m, and 10m avg loads in a list and append it to the droplet object
def get_loads(droplet):
    r = requests.get("http://" + droplet.ip_address + "/load.php")
    droplet.loadavg = [float(l) for l in r.text.split(' ')[:3]]


# Request create of new droplets
def create_droplets(num, start_index):
    # Create list of names for new droplets
    names = ['wordpress-clone-%d' % i for i in range(num, num + start_index)]

    # TODO: Error handling
    digitalocean.Droplet.create_multiple(token=TOKEN, names=names, size="s-1vcpu-1gb", image=IMAGE_NAME, region="nyc3",
                                         backups=False, ipv6=True, private_networking=None, tags="website")


# Get info from all website droplets, return them sorted by ones running and ones being started.
# Running droplets will be polled for average load
def get_droplets(manager):
    droplets = manager.get_all_droplets(tag_name="website")

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

manager = digitalocean.Manager(token=TOKEN)

while True:
    # Get list of all web server droplets, both running and ones being provisioned. Get the average load of ones running
    active_droplets, inprogress_droplets = get_droplets(manager)

    # Sort out any non-responsive droplets
    unresponsive_droplets = list(filter(lambda d: not hasattr(d, 'loadavg'), active_droplets))
    active_droplets = list(filter(lambda d: hasattr(d, 'loadavg'), active_droplets))

    # TODO: Do some health check on unresponsive droplets. Maybe it's a fluke, maybe they crashed

    # Find the total load on the cluster from the last minute average
    total_load = sum([d.loadavg[ONE_MIN] for d in active_droplets])
    if total_load == 0:     # In case there's no active droplets, set the load > 1 to trick the provisioning algorithm below
        total_load = 0.01

    # Each droplet should have a load of no more than 1. If the total load exceeds the number of available droplets
    # (plus ones on the way), provision more
    num_usable_droplets = len(active_droplets) + len(inprogress_droplets)
    if total_load > num_usable_droplets:
        num_to_create = math.ceil(total_load) - num_usable_droplets

        # There shouldn't be more than MAX_DROPLETS provisioned
        total_droplets = num_usable_droplets + len(unresponsive_droplets)
        if num_to_create + total_droplets > MAX_DROPLETS:
            num_to_create = MAX_DROPLETS - total_droplets
            # TODO: Word the email differently if this is the case

        # TODO: Send an email that x droplets are being provisioned

        create_droplets(num_to_create, total_droplets)

    # TODO: If no nodes provisioned in a while, delete nodes based on 15-minute load averages
