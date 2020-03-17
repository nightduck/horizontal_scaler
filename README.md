# Horizontal scheduler for Apache server on Digitalocean

 This service is intended to be run on an Nginx droplet. Installation turns that droplet into a load balancer pointing
 at your web servers on digitalocean. The quintessential server.py script will automatically provision more droplets for
 that load balancer, as traffic scales up and down.
 
 The end goal is a cheaper load balancer that can be run on a $5 droplet (digitalocean offers loadbalancers for $10/mo).
 With the use of floating IPs, the load balancer droplet can be turned off completely, and a single web server droplet
 can host your site during down periods. This is ideal for [low-traffic blogs with occasionally viral
 content](orenbell.com).
 
 Currently, my own website is being run on a single $10 droplet. Whenever I link to anything on reddit, I'll spin up
 a $5 droplet running this scaler, and move my floating IP address over. If traffic ever picks up, this scaler
 automatically clones my web server as many times as needed. The cost savings are significant.
 
 ## Setup
 
 1) The scaler needs all web servers under it's stewardship to report their current load at example.com/load.php. Copy
 load.php to the root directory of your website to handle that.
 2) The load balancer is set to redirect to any droplet with the tag "website", so add that tag to your web server
 droplet
 3) Create a new droplet, the $5 one works, with Nginx installed on it.
 4) Install the digitalocean python bindings with `sudo pip install -U python-digitalocean`. This package needs to be
 visible to the root user. 
 5) Clone this repository onto the scaler droplet in step 3 and run the install.sh script.
 You will find the files installed in /usr/bin/horizontal_scaler, including config.json. That's important.
 6) Run `sudo systemctl horizontal_scaler.service start` to run the service
 7) Your digitalocean API token is required in order to automatically provision new droplets. You can create an API key
 on the digitalocean dashboard (be sure to make one with write privileges). Add this token to config.json, as the value
 for "token".
 
 ## Configuration
 
Multiple attributes can be added to config.json, most are optional and have preprogrammed defaults. All are listed below

#### max_droplets

As a guard against DDoS attacks driving up your usage bill, you can set an upper cap to the number of droplets your
scaler is allowed to provision. Default is 100

#### poll_period

This changes how often the poll loops, and is expressed in seconds. A slow loop may be unresponsive to load changes. The
default is 30

#### token

The API key for your digitalocean account. Required

#### image_name

The ID of the snapshot to clone whenever provisioning new droplets. Be sure to update it everytime you take a new
snapshot of your website. If not specified, the scaler will use the most recently created image. Must be an 8 digit
number (as of March 2020).

#### base_name

Designates what to name the provisioned droplets. They will all share this name. Default is wp-clone

#### email

What email to use when the server needs to notify you of anything. This has always been flakey, so don't get your hopes
up. Digitalocean sends you emails after droplet creation anyways.

#### load_per_droplet

Designates the upper limit each web server droplet is allowed to carry. Once their load exceeds this value, another
droplet is provisioned. It should typically be equal to the number of cores on that droplet. Default is 1, personally
I use 2.
 