#!/usr/bin/bash

# Copyright (c) N. A. Inc. 2022
# This program is free software per V3, or later version, of the GNU General Public License.
# It is distributed AS-IS, WITHOUT ANY WARRANTY, or implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.

# Version 1.0
# DPM.sh is a housekeeping script for the Dual Path Monitoring application,
# (DPM.py) run on a Raspberry Pi model 2, 3, or 4, with Python V3.9 or later.
# A system reboot should be scheduled to run daily after midnight via  /etc/crontab
# DPM.sh should be run automatically, post re-boot, via  /etc/rc.local
# It assumes the syslog client of the EVL4 module is configured to write to a LOCAL
# facility (e.g. LOCAL0) and  /etc/rsyslog.conf  then directs it to the actual-path
# equivalent of $LOGDIR/EVL4.log  It also assumes that DPM.ini (config file) directs the
# runtime log for DPM.py to the actual-path equivalent of $LOGDIR/DPM-yyyymmddhhmmss.log

PATH="/home/pi/DPM-EVL4:$PATH" ; export PATH
APPDIR="/home/pi/DPM-EVL4"
LOGDIR="/home/pi/DPM-EVL4/logs"

# FIRST, check Ras Pi's clock and do any optional modem and EVL4 reboots
now="$(date '+%Y%m%d%H%M%S')"
STARTUPLOG="$LOGDIR/DPM-HK-startup-$now.log"
cd $APPDIR ; python $APPDIR/startup.py $STARTUPLOG 1>>$STARTUPLOG 2>&1

# Ras Pi system clock should now be correct, so let's go!
tstamp="$(date '+%Y%m%d%H%M%S')"
HKLOG="$LOGDIR/DPM-HK-$tstamp.log"
start="$(date '+%Y-%m-%d %T')"
echo $start " Start of DPM Housekeeping" > $HKLOG

# rename the prior EVL4 syslog and offset files.
var1="$(stat -c %x $LOGDIR/EVL4.log)"
var2="${var1%%'.'*}"
var3="${var2//[!0-9]/}"
mv $LOGDIR/EVL4.log  $LOGDIR/EVL4-$var3.log 1>>$HKLOG 2>&1
mv $LOGDIR/EVL4.offset  $LOGDIR/EVL4-$var3.offset 1>>$HKLOG 2>&1

# compress aged (> 2 days old) files
find $LOGDIR/DPM-*.log -type f -mtime +2 -exec gzip {} \; 1>>$HKLOG 2>&1
find $LOGDIR/EVL4-*.log -type f -mtime +2 -exec gzip {} \; 1>>$HKLOG 2>&1
find $LOGDIR/EVL4-*.offset -type f -mtime +2 -exec gzip {} \; 1>>$HKLOG 2>&1

# delete aged (> 5 days old), compressed files
find $LOGDIR/DPM-*.log.gz -type f -mtime +5 -exec rm -f {} \; 1>>$HKLOG 2>&1
find $LOGDIR/EVL4-*.log.gz -type f -mtime +5 -exec rm -f {} \; 1>>$HKLOG 2>&1
find $LOGDIR/EVL4-*.offset.gz -type f -mtime +5 -exec rm -f {} \; 1>>$HKLOG 2>&1

# create a new $LOGDIR/EVL4.log file with the requisite permissions
touch $LOGDIR/EVL4.log 1>>$HKLOG 2>&1
chmod 644 $LOGDIR/EVL4.log 1>>$HKLOG 2>&1
# restart rsyslog daemon to ensure it can write to the EVL4.log file
sudo systemctl restart rsyslog.service 1>>$HKLOG 2>&1

restart="$(date '+%Y-%m-%d %T')"
echo $restart " About to restart Dual Path Monitoring" >> $HKLOG
# invoke the Dual Path Monitoring python application
cd $APPDIR ;  nohup python $APPDIR/DPM.py 1>>$HKLOG 2>&1 &

end="$(date '+%Y-%m-%d %T')"
echo $end " End of DPM Housekeeping and restart" >> $HKLOG
