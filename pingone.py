#!/usr/bin/python3
"""
Copyright (c) N. A. Inc.  2022
This program is free software per V3, or later version, of the GNU General Public License.
It is distributed AS-IS, WITHOUT ANY WARRANTY, or implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.
"""

import sys
import subprocess                               # used to ping
import logging

class PingOne:

# Version 1.0
# A Python class to round-robin a collection of internet hosts known to respond
# to a ping.  Used for basic confirmation of a functional internet connection.

    # class constructor.
    def __init__(self) :
        logging.info('PNG-001I PingOne object created')

        self.pingerID = 0        # instance variable for round-robin of pingers
        # Used to check if there is a functional internet connection.
        # Can be overridden via setPingers() method
        self.pingers = {1: 'google.com', 2: 'amazon.com',  3: 'yahoo.com', 4: 'facebook.com', 5: 'youtube.com', 6: 'reddit.com'}


    # replace default pingers with a custom set
    def setPingers(self, myPingers) :
        if myPingers != None :
            self.pingers = eval(myPingers)


    # return number of hostnames in the pingers dictionary
    def getCountHostnames(self) :
        return len(self.pingers)


    # get the next hostname from the collection of pingers
    def getNextHostname(self) :
        len1 = len(self.pingers)
        if self.pingerID >= len1 : self.pingerID = 1
        else : self.pingerID += 1
        return self.pingers[self.pingerID]


    # check for a working Internet connection
    def isInternetAlive(self, pingCmd) :
        hostname = self.getNextHostname()
        command = pingCmd + [hostname]
        logging.trace('PNG-002I The ping command was: %s',command)
        pingRC = subprocess.run(args=command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        if pingRC != 0 : # we'll do one re-try, just in case
            logging.trace('PNG-001E The ping failed ... retrying one more time:')
            hostname = self.getNextHostname()
            command = pingCmd + [hostname]
            logging.trace('PNG-003I The ping command was: %s',command)
            pingRC = subprocess.run(args=command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
            if pingRC == 0 : return True
            else : return False
        else : return True


  # end of PingOne class
