import json
import datetime
import digitalocean

# Program starts here
with open("config.json", 'r') as readin:
    data = json.load(readin)

    if "token" in data:
        TOKEN = data["token"]

manager = digitalocean.Manager(token=TOKEN)

# If image ID not specified, default is the most recent wordpress snapshot
print(manager.get_all_snapshots())
