#!/usr/bin/python3

"""
Copyright (c) N. A. Inc.  2022
This program is free software per V3, or later version, of the GNU General Public License.
It is distributed AS-IS, WITHOUT ANY WARRANTY, or implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.
"""

# Version 1.0
# This program performs initialization operations for the DPM application via
# the DPM.sh general Housekeeping and start/restart shell script.
# In the absence of a working Internet connection, this program gets date and time
# from a cellular modem (as supplied by NITZ, GPS, NTP or similar) to prevent the
# Ras Pi's system clock from being incorrect, post reboot.
# If the ModemSoftReboot option in the configuration file (DPM.ini) is "True",
# the modem will be soft-rebooted by this program.  This is useful when the
# Ras Pi Hat is NOT powered from a USB port on the Ras Pi itself and hence when
# the Ras Pi is rebooted (via crontab or physical power-cycle), the Hat and modem
# are consequently NOT power-cycled.  Similarly, the EVL4 module can be soft-rebooted.

import sys
import subprocess                                   # used to reset system clock and EVL4 reboot
import logging
from config import Configuration                    # class to handle configuration (.ini) file
from pingone import PingOne                         # class to help test for a live internet connection
from mymodem import MyModem                         # class for wireless modem operations
from telnetEVL4 import TelnetEVL4                   # class to handle communication with EVL4
from stupefy import Stupefy                         # to obtain cleartext password to EVL4

def main () :

    if(len(sys.argv) == 2) :
        overridelog = sys.argv[1]
    else : overridelog = 'SUP-HK-startup.log'

    cnf1 = Configuration(overridelog)               # create Configuration object (with logging)
    png1 = PingOne()                                # create PingOne object
    pingCmd = cnf1.getPingCommand()                 # used to test for working Internet connection
    mcomms = cnf1.getModemCommsDevice()             # Modem communications device name
    mboot = cnf1.getModemRebootDevice()             # modem device for AT#REBOOT command
    mbaud = cnf1.getModemBaud()                     # modem baud rate
    mtimeout = cnf1.getModemTimeOut()               # Modem connection timeout (seconds)
    mretry = cnf1.getModemRetries()                 # re-connection maxium retries

    tpwd = cnf1.getTelEVL4Password()                # get telnet password for EVL4
    # stupefied passwords start and end with either single or double quotation marks
    if ( ( (tpwd.startswith("'")) and (tpwd.endswith("'")) ) or ( (tpwd.startswith('"')) and (tpwd.endswith('"')) ) ) :
        stu1=Stupefy()                              # create Stupify object for EVL4's password
        tpwd = stu1.undoStupefy(tpwd)               # derive the requisite EVL4 password
    treboot = cnf1.getTelEVL4RebootURL()            # get EVL4 Reboot URL
    thost = cnf1.getTelEVL4Host()                   # get telnet host (IPv4 address)
    tport = cnf1.getTelEVL4Port()                   # get telnet port
    timeout = cnf1.getTelEVL4TimeOut()              # Telnet socket timeout (seconds)
    tretry = cnf1.getTelEVL4Retries()               # re-connection maxium retries
    tel1 = TelnetEVL4(treboot, thost, tport, tpwd, timeout, tretry, True) # create reboot-only TelnetEVL4 object

    doRPiReboots = cnf1.doRasPiReboot()             # are Ras Pi reboots allowed? (True/False)
    RPiRebootRetries = cnf1.getRasPiRebootRetries() # max allowed Ras Pi reboot attempts
    RPiReboots = cnf1.getCountRasPiReboots()        # count of attempted RasPi reboots this cycle


    if png1.isInternetAlive(pingCmd) :
        logging.info('SUP-001I Internet connection OK; no Ras Pi clock adjustment will be made')
        if cnf1.doModemSoftReboot() :               # are we doing modem soft-reboots?
            # create MyModem object using Fast Path initialization (True)
            mdm1 = MyModem(cnf1, mboot, mcomms, mbaud, mtimeout, mretry, True)
            if (mdm1.checkConnection() is None) :   # there's a modem connection issue
                if doRPiReboots :                   # are we doing RasPi triage?
                    rebootRasPi(cnf1, RPiRebootRetries, RPiReboots)
                else :
                    logging.error('SUP-001E Connectivity problem with modem.  Terminating application')
                    sys.exit(16)                    # goodbye cruel world
            else :                                  # modem connection is good
                if (0 != RPiReboots) :
                    cnf1.resetRasPiReboots()        # reset the reboot count to zero
                else : pass
                mdm1.doReboot()                     # soft-reboot modem (AT#REBOOT)
        else : pass

    else :
        logging.info('SUP-002I NO Internet connection ...')
        # create MyModem object using Fast Path initialization (True)
        mdm1 = MyModem(cnf1, mboot, mcomms, mbaud, mtimeout, mretry, True)
        if (mdm1.checkConnection() is None) :       # there's a modem connection issue
            if doRPiReboots :                       # are we doing RasPi triage?
                rebootRasPi(cnf1, RPiRebootRetries, RPiReboots)
            else :
                logging.error('SUP-002E Connectivity problem with modem.  Terminating application')
                sys.exit(16)                        # goodbye cruel world
        else :
            if (0 != RPiReboots) :
                cnf1.resetRasPiReboots()            # reset the reboot count to zero
            else : pass

        datetime = mdm1.getDateTime()
        if datetime is None :
            logging.error('SUP-003E Failed to get date and time from modem')
        else :
            cmd = ['sudo', 'date', '+"%y%m%d %T"']
            tmpstr = '-s ' + datetime[0] + ' ' + datetime[1]
            cmd.append(tmpstr)
            rc = subprocess.run(args=cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
            if rc == 0 :
                logging.info('SUP-003I Adjusted Ras Pi system date and time: %s', cmd)
            else :
                logging.error('SUP-004E Failed to adjust Ras Pi system date and time')

        if cnf1.doModemSoftReboot() :
            mdm1.doReboot()                         # soft-reboot modem (AT#REBOOT)
        else : pass

    # end of else clause for "NO Internet" logic

    if cnf1.doTelEVL4SoftReboot() :
        tel1.doReboot()                             # soft-reboot EVL4 Module via URL
    else : pass


def rebootRasPi(cnf1, RPiRebootRetries, RPiReboots) :
    # On rare occasions, a Ras Pi may not boot perfectly and may adversely affect
    # connectivity to the modem, EVL4 or network. If so, then optionally, we'll try
    # to reboot the Ras Pi and hope we have better luck next time around, assuming
    # the original root cause was not the modem, EVL4, or network hardware itself.

    if (RPiReboots < RPiRebootRetries) :
        logging.error('SUP-005E Connectivity problem with modem or EVL4 -- will reboot Ras Pi')
        cnf1.updateRasPiReboots()           # increment count of attempted reboots
        cmd = ['sudo', 'reboot', 'now']     # reboot the Raspberry Pi
        rc = subprocess.run(args=cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    else :
        logging.error('SUP-006E Connectivity problem with modem or EVL4. Unable to resolve ; Terminating')
        sys.exit(8)                         # goodbye cruel world ... we tried our best




if __name__ == "__main__":
    main()
