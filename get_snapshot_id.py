import json
import datetime
import digitalocean

# Program starts here
with open("config.json", 'r') as readin:
    data = json.load(readin)

    if "token" in data:
        TOKEN = data["token"]

# Write to log file that server is starting
with open("server.log", "a") as log:
    log.write(str(datetime.datetime.now()) + ": Starting server\n")

manager = digitalocean.Manager(token=TOKEN)

# If image ID not specified, default is the most recent wordpress snapshot
snapshots = list(filter(lambda w: w.name.find("wordpress") == 0, manager.get_all_snapshots()))
print(snapshots)