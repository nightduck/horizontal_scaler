<?php
$uptime = file_get_contents("/proc/uptime");
$load = file_get_contents("/proc/loadavg");
echo $uptime . $load;
?>
