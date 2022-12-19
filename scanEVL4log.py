#!/usr/bin/python3
"""
Copyright (c) N. A. Inc.  2022
This program is free software per V3, or later version, of the GNU General Public License.
It is distributed AS-IS, WITHOUT ANY WARRANTY, or implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.
"""

from datetime import datetime
import time
import re                               # used for Regular Expressions
import logging
from pygtail import Pygtail             # tail log file written by EVL4 syslog client

class ScanEVL4Log:

# Version 1.1
# A Python class to scan the EVL4 log file written to by an EVL4
# syslog client

# TO DO: Ideally, should enforce a Singleton, since multiple instances
# for just one EVL4 is illogical, but this works fine for now.

# The EVL4 syslog client (firmware 1.1.108 or later ) can be configured to log to syslog's
# Facility 16 (i.e. local0) through Facility 23 (i.e. local7). A rule in rsyslog.conf
# (or related config file, depending on the OS) can send messages to a dedicated log file,
# for example:    local0.*      /var/log/EVL4.log

# Example of messages written (in chronological order) by EVL4 syslog client.
# For brevity, "..." represents the preamble shown by generalized example below.
#   MMM dd hh:mm:ss 192.168.nnn.nnn ENVISALINK[MAC Address]:

# VISTA20-P System is disarmed, then zone 3 faulted and subsequently resolved:
# ... Zone Open: 3
# ... Zone Closed: 3             <-- reported 1 minute later

# First, the VISTA20-P Security System is armed and then zone 3 is faulted:
# ... CID Event: 3441010010      <-- Armed Night Stay
# ... Zone Open: 3
# ... CID Event: 1131010030      <-- Burglar Alarm reported
# ... Alarm Zone: 003            <-- this zone was tripped
# ... CID Event: 1441010010      <-- System disarmed
# ... Zone Closed: 3
# ... CID Event: 3131010030      <-- Burglar Alarm resolved


    # class constructor.
    def __init__(self, scanlog, offset) :
        self.scanlog = scanlog
        self.offset = offset
        logging.info('SCN-001I ScanEVL4Log object created')

        self.MAX_HISTORY = 2    # Do NOT change this value, else the behavior of DPM.py will be unpredictable.

        self.CIDevents = {
            'CIDs'      : {},
            'CIDflags'  : {}
        } # end of CIDevents


    # get syslog records that contain CID (Contact ID) events
    def getLogRecsWithCID(self) :

        try :
            for line in Pygtail(self.scanlog, paranoid=True, offset_file=self.offset) :
                line = line.strip()                     # a prerequisite for hit3 search

                # example:  MMM dd hh:mm:ss 192.168.nnn.nnn ENVISALINK[MAC Address]:  CID Event: 1604010010
                hit1 = re.search("[A-Z,a-z]{3}\s*[0-9]{1,2}\s*[0-9]{2}\:[0-9]{2}\:[0-9]{2}", line)
                if hit1 is not None :
                    date1 = hit1.group(0)               # extract date string
                    now = datetime.now()                # need current year
                    dtstr = now.strftime("%Y")          # grab current year
                    dtstr = dtstr + ' ' + date1         # synthesize full date
                    tmp1 = datetime.strptime(dtstr,"%Y %b %d %H:%M:%S")
                    ts1 = datetime.timestamp(tmp1)

                # look for Contact ID (CID) codes
                hit2 = re.search("CID Event:\s*[0-9]{10}", line, re.I)
                if hit2 is not None:
                    hit3 = re.search("[0-9]{10}$", hit2.string)
                    if hit3 is not None:
                        thisCID = hit3.group(0)         # extract 10 digit CID code captured by EVL4
                        # add to dictionary of CID events
                        self.CIDevents['CIDs'][ts1] = thisCID
                        # signal ("0") event has yet to be reported
                        self.CIDevents['CIDflags'][ts1] = '0'
                    else: pass
                else : pass

        except Exception as ex :
            logging.error('SCN-001E Error while scanning syslog file: %s', str(ex))

        self.doPruning()                                # remove the dead wood
        candidateCIDs = {}
        for key in self.CIDevents['CIDs'] :
            if self.CIDevents['CIDflags'][key] == '0' : # status is UNreported
                candidateCIDs[key] = self.CIDevents['CIDs'][key]
        # end of for loop
        return candidateCIDs


    # flag CID event as now reported upon (set value of  '1')
    def flagAsReportedCID(self, tskey) :
        self.CIDevents['CIDflags'][tskey] = '1' # set status to reported
        logging.debug('SCN-003I Syslog CID is now \"Reported\" (flag=\'%s\') key=%s CID=%s', self.CIDevents['CIDflags'][tskey], tskey, self.CIDevents['CIDs'][tskey])
        return


    # retrieve recent, reported (isReptd is True) or unreported (isReptd is False) CIDs
    def getRecentCIDs(self, RECENT_SECS, isReptd) :
        recentCIDs = {}
        now = datetime.now()
        nowts = int(datetime.timestamp(now))
        (flag := '1') if isReptd else (flag := '0')

        for key in self.CIDevents['CIDs'] :
            tmpkey = int(key)
            diff = abs(nowts - tmpkey)
            # save if recent and has/has not been reported upon
            if ( (diff <= RECENT_SECS) and (self.CIDevents['CIDflags'][key] == flag) ) :
                recentCIDs[key] = self.CIDevents['CIDs'][key]
            else : pass
        # end of for loop

        return recentCIDs


    # Method to prune surplus historical CIDs scraped from EVL4's syslog.
    # "self.CIDevents" is NOT re-initialized before each scan because we need
    # some history to drive the logic for getRecentCIDs(). The pygtail
    # offset file prevents large accretion, but some pruning is still required.
    def doPruning(self) :
        keys = sorted(self.CIDevents['CIDs'].keys())
        popLim = 0
        length = len(keys)
        if length > self.MAX_HISTORY : popLim = (length - self.MAX_HISTORY)
        for x in range(0, popLim) :
            k = keys[x]
            self.CIDevents['CIDs'].pop(k)
            self.CIDevents['CIDflags'].pop(k)
        return


# end of ScanEVL4Log class
