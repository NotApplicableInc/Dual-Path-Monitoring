#!/usr/bin/python3
"""
Copyright (c) N. A. Inc.  2022
This program is free software per V3, or later version, of the GNU General Public License.
It is distributed AS-IS, WITHOUT ANY WARRANTY, or implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.
"""

"""
Version 1.0 (requires Python 3.9 or a more current release)
DPM.py implements Dual Path Monitoring ("DPM") for a Honeywell ("Resideo") Vista home
security system equipped with an EyezOn Envisalink EVL4 IP Security Interface Module.

It is designed to run on a Raspberry Pi (model 2, 3 or 4 running Pi OS) capped with a
4G/5G wireless modem hat (ideally with a mini PCIe socket, to facilitate future upgrades).

To witness events on the Honeywell Vista system, it talks to the EVL4's IP socket interface
(port 4025) using Python's telnet library and optionally, can also scan the EVL4's syslog.

If there is NO regular, working Internet connection, it sends SMS messages to one or more
cell phones.  It is assumed that EyezOn's Monitoring Application (for Android or iOS) is used
to surveil the Honeywell system when an Internet connection IS available.
"""

import sys
MIN_PYTHON = (3, 9)                             # Need at least Python V3.9
if sys.version_info < MIN_PYTHON :
    sys.exit("DPM-001E Cannot continue -- Python %s.%s or later is required.\n" % MIN_PYTHON)
import subprocess
import time
from time import sleep
from datetime import datetime
import logging                                      # python logging function
from config import Configuration                    # class to handle configuration (.ini) files
from cid import DecodeCID                           # class to decode numeric CID into English text
from pingone import PingOne                         # class to test for a live internet connection
from mymodem import MyModem                         # class for wireless modem operations
from telnetEVL4 import TelnetEVL4                   # class to handle communication with EVL4
from scanEVL4log import ScanEVL4Log                 # class to scan EVL4's syslog records
from stupefy import Stupefy                         # to obtain cleartext password to EVL4


def main():

    cnf1 = Configuration(None)                      # create Configuration and Logging object
    if cnf1.doScanSyslog() :                        # global flag to enable/disable syslog scanning
        scanlog = cnf1.getEVL4Log()                 # EVL4's syslog file
        offset = cnf1.getEVL4Offset()               # Pygtail's offset file for EVL's log
        slg1=ScanEVL4Log(scanlog, offset)           # create ScanEVL4Log object

    png1 = PingOne()                                # create PingOne object

    cid1 = DecodeCID('NORMAL')                      # create normally verbose DecodeCID object
    myUsers = cnf1.getUsers()                       # get user details fron config file
    if myUsers is not None : cid1.setUsers(myUsers) # customize User IDs and names
    myZones = cnf1.getZones()                       # get zone details from config file
    if myZones is not None : cid1.setZones(myZones) # customize Zone IDs and descriptions

    mcomms = cnf1.getModemCommsDevice()             # modem device name for normal AT commands
    mboot = cnf1.getModemRebootDevice()             # modem device for AT#REBOOT command only
    mbaud = cnf1.getModemBaud()                     # modem baud rate
    mtimeout = cnf1.getModemTimeOut()               # modem connection timeout (seconds)
    mretry = cnf1.getModemRetries()                 # re-connection maxium retries
    mdmkeepalive = cnf1.getModemCheckIn()           # AT 'ping' interval (seconds)
    mdm1 = MyModem(cnf1, mboot, mcomms, mbaud, mtimeout, mretry, False)   # create Mymodem object

    treboot = cnf1.getTelEVL4RebootURL()            # get EVL4 Reboot URL
    thost = cnf1.getTelEVL4Host()                   # get telnet host (IPv4 address)
    tport = cnf1.getTelEVL4Port()                   # get telnet port
    tpwd = cnf1.getTelEVL4Password()                # get telnet password for EVL4
    # stupefied passwords start and end with either single or double quotation marks
    if ( ( (tpwd.startswith("'")) and (tpwd.endswith("'")) ) or ( (tpwd.startswith('"')) and (tpwd.endswith('"')) ) ) :
        stu1=Stupefy()                              # create Stupify object for EVL4's password
        tpwd = stu1.undoStupefy(tpwd)               # derive the requisite EVL4 password
    timeout = cnf1.getTelEVL4TimeOut()              # Telnet socket timeout (seconds)
    tretry = cnf1.getTelEVL4Retries()               # re-connection maxium retries
    tel1 = TelnetEVL4(treboot, thost, tport, tpwd, timeout, tretry, False) # create TelnetEVL4 object
    tpollmins = cnf1.getTelEVL4Polling()            # get polling interval (minutes)
    telkeepalive = cnf1.getTelEVL4StayAwake()       # get EVL4 'ping' interval (seconds)

    doRPiReboots = cnf1.doRasPiReboot()             # are Ras Pi reboots allowed? (True/False)
    RPiRebootRetries = cnf1.getRasPiRebootRetries() # max allowed Ras Pi reboot attempts
    RPiReboots = cnf1.getCountRasPiReboots()        # count of attempted RasPi reboots this cycle

    # On rare occasions, a Ras Pi may not boot perfectly and may adversely affect
    # connectivity to the modem, EVL4 or network. If so, then optionally, we'll try
    # to reboot the Ras Pi and hope we have better luck next time around, assuming
    # the original root cause was not the modem, EVL4, or network hardware itself.
    if ( (mdm1.checkConnection() is None)  or (tel1.checkConnection() is None)  ) :
        logging.error('DPM-002E Connectivity problem with modem or EVL4 ... will attempt to resolve')
        if doRPiReboots :
            if (RPiReboots < RPiRebootRetries) :
                cnf1.updateRasPiReboots()           # increment count of attempted reboots
                cmd = ['sudo', 'reboot', 'now']     # reboot the Raspberry Pi
                rc = subprocess.run(args=cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
            else :
                logging.error('DPM-003E Connectivity problem with modem or EVL4. Unable to resolve ; Terminating')
                sys.exit(8)                         # goodbye cruel world ... we tried our best
        else :
            logging.error('DPM-004E Connectivity problem with modem or EVL4.  Terminating application')
            sys.exit(16)                            # goodbye cruel world, there were no second chances
    else :
        if ( 0 != RPiReboots ) : cnf1.resetRasPiReboots()   # conditionally, reset the reboot count to zero
        logging.info('DPM-001I Dual Path Monitoring activated ... ')
        callCellPhones(cnf1, mdm1, 'DPM-001I Dual Path Monitoring activated ... ', False, False, True)   # Reboot Alert

    # set timers to force initial 'heart-beat' checks for EVL4 and modem
    tpolltime = time.time_ns() - (1000000000 * tpollmins * 60)
    tkatime = time.time_ns() - (1000000000 * telkeepalive)
    mkatime = time.time_ns() - (1000000000 * mdmkeepalive)

    fullMsg = ''                                   # initialize collated EVL4 message

    while True :
        # Third Party Interface ("TPI") processing
        msg = tel1.getNextMessage()                # TPI 'telnet' socket interface port 4025
        fullMsg = TPI(cnf1, cid1, msg)             # process Third Party Interface message(s)

        if fullMsg != '' :                         # "full" TPI message to process ?
            if cnf1.doScanSyslog() :               # are we doing syslog scans?
                if checkSyslog(cnf1, slg1, msg['msg03txt'], True) :
                    pass                            # it was already reported via syslog
                else :                              # NOT already reported via syslog
                    logging.info('DPM-002I Alert: %s', fullMsg)
                    doAlerts(cnf1, mdm1, png1, fullMsg, False) # Uppercase matching
                    fullMsg = ''                    # re-initialize full message string
            else :                                  # we are not doing syslog scans
                logging.info('DPM-003I Alert: %s', fullMsg)
                doAlerts(cnf1, mdm1, png1, fullMsg, False) # Uppercase matching
                fullMsg = ''                        # re-initialize full message string
        else : pass                                 # there's no "full" message yet from TPI

        if cnf1.doScanSyslog() :                    # is scanning syslog enabled (True)?
            event = scanSyslog(cnf1, slg1, msg['msg03txt'])
            if event is None :                      # nothing to report from syslog
                pass
            else :
                msgstr = cid1.getDescription(event) # convert numeric CID into text
                logging.info('DPM-004I Decoded syslog CID is: %s', msgstr)
                doAlerts(cnf1, mdm1, png1, msgstr, True) # Lowercase matching
        else : pass                                 # we are not doing syslog scanning

        tmptime = time.time_ns()                    # get the current nanosec time

        # periodically (e.g. every 17 minutes) poll the EVL4.
        if ( ((tmptime - tpolltime) / 1000000000) >= (tpollmins * 60) ) :
            tpolltime = tmptime                     # save the latest time of polling
            tel1.doPoll()                           # poll the EVL4 to prevent it rebooting
        else : pass

        # periodically (e.g. approx every 3 minutes) 'ping' the EVL4
        if ( ((tmptime - tkatime) / 1000000000) >= (telkeepalive) ) :
            tkatime = tmptime                       # save the time of the latest event
            tel1.doInvalidRequest()                 # 'ping' the EVL4
        else : pass

        # periodically (e.g. every 60 secs) check for an SMS request or 'ping' the modem
        if ( ((tmptime - mkatime) / 1000000000) >= (mdmkeepalive) ) :
            mkatime = tmptime                       # save the time of the latest event
            if cnf1.doModemInboundSMS() :           # are we doing Inbound SMS ?
                doInboundSMS(cnf1, mdm1, tel1)      # process any inbound SMS request(s)
            else :                                  # otherwise, just check the modem
                mdm1.doStayAwake()                  # 'ping' the wireless modem with "AT"
        else : pass

    # end of while loop.

#end of main()


# TPI  Third Party Integration feature of EVL4 firmware (IP socket on port 4025)
# This logic assumes a setting of MAX_HISTORY=2 in the TelnetEVL4 instance.
def TPI(cnf1, cid1, msg):
    theMsg = ''                                                         # intialise the full message string
    # sort all keys to have the most recent first
    keys00 = sorted(msg['msgflag00'].keys(), reverse=True)              # alpha keypad message flags
    keys01 = sorted(msg['msgflag01'].keys(), reverse=True)              # zone(s) tripped message flags
    keys02 = sorted(msg['msgflag02'].keys(), reverse=True)              # partition status message flags
    keys03 = sorted(msg['msgflag03'].keys(), reverse=True)              # CID message flags
    keysFF = sorted(msg['msgflagFF'].keys(), reverse=True)              # Zone timers dump message flags

    # Honeywell alpha keypad messages
    if len(keys00) > 1 :
        # EVL4 issues a type "00" message every 10 secs or so and most are repeats to be ignored.
        if ( msg['msgflag00'][keys00[0]] == '1' ) :                     # a new, "not yet processed" message
            if( msg['msg00txt'][keys00[0]] == msg['msg00txt'][keys00[1]] ) :
                msg['msgflag00'][keys00[0]] = '0'                       # set status to "has been processed"
            else :
                logging.debug('DPM-005I New, unprocessed TPI message: %s', msg['msg00txt'][keys00[0]])
                msg['msgflag00'][keys00[0]] = '0'                       # set status to "has been processed"
        else :  pass
    elif len(keys00) == 1 :
        if ( msg['msgflag00'][keys00[0]] == '1' ) :                     # a new, "not yet processed" message
                logging.debug('DPM-006I New, unprocessed TPI message: %s', msg['msg00txt'][keys00[0]])
                msg['msgflag00'][keys00[0]] = '0'                       # set status to "has been processed"
        else :  pass
    else : pass

    # tripped security zones
    # we'll get what we need from the CID, but keep this code for possible future use.
    if len(keys01) > 0 :
        if ( msg['msgflag01'][keys01[0]] == '1' ) :                     # a new, "not yet processed" message
            msg['msgflag01'][keys01[0]] = '0'                           # set status to "has been processed"
        else : pass
    else : pass

    # security system Partition status(es)
    # we'll get this info from the CID, but keep this code for possible future use.
    if len(keys02) > 0 :
        if ( msg['msgflag02'][keys02[0]] == '1' ) :                     # a new, "not yet processed" message
            msg['msgflag02'][keys02[0]] = '0'                           # set status to "has been processed"
        else : pass
    else : pass

    # Contact ID "CID" messages
    # Typically, the EVL4 (firmware 01.04.176A or later) seems to issue a logical
    # group of three messages in the following order: a Partition Status message,
    # followed by an overall System Status message and finally a CID message.
    # Therefore, this seems to be the best place to collate the three messages.
    if len(keys03) > 0 :
        if ( msg['msgflag03'][keys03[0]] == '1' ) :     # a new, "not yet processed" message
            logging.debug('DPM-007I New, unprocessed TPI message: %s', msg['msg03txt'][keys03[0]])
            msg['msgflag03'][keys03[0]] = '0'           # set status to "has been processed"
            if len(keys03) > 1 :
            # there should not be duplicate adjacent CIDs, but we'll check, just in case.
                if ( (msg['msg03txt'][keys03[0]] == msg['msg03txt'][keys03[1]]) and (msg['msgflag03'][keys03[1]] == '0') ) :
                    pass
                else :
                    CID = msg['msg03txt'][keys03[0]]
                    tmplst = CID.split('=')                             # split off numeric CID
                    tmpstr = cid1.getDescription(tmplst[1])             # decode the numeric CID
                    theMsg= msg['msg00txt'][keys00[0]] + ' ! ' + tmpstr # Exclamation Mark is NOT arbitrary
            else :
                CID = msg['msg03txt'][keys03[0]]
                tmplst = CID.split('=')                                 # split off numeric CID
                tmpstr = cid1.getDescription(tmplst[1])                 # decode the numeric CID
                theMsg = msg['msg00txt'][keys00[0]] + ' ! ' + tmpstr    # Exclamation Mark is NOT arbitrary
        else : pass
    else : pass

    # en-masse dump of EVL4's internal zone timers
    # we're not currently using this feature but keep this code for possible future use.
    if len(keysFF) > 0 :
        if ( msg['msgflagFF'][keysFF[0]] == '1' ) :                     # a new, "not yet processed" message
            msg['msgflagFF'][keysFF[0]] = '0'                           # set status to "has been processed"
        else : pass
    else : pass

    if (theMsg.count('!') > 0) :                                        # Exclamation Mark is NOT arbitrary
        msgList = theMsg.split('!')                                     # Exclamation Mark is NOT arbitrary
        # need to compress this message to allow space for a  yyyy-mm-dd hh:mm:ss date-time prefix.
        # For 7-bit GSM encoding, the maximum payload for a single SMS message is 160 characters.
        tokens = cnf1.getIgnoreTokens()
        for tok1 in tokens :                                            # bare token
            msgList[0] = msgList[0].replace(tok1, '')                   # remove unwanted tokens from message
            msgList[0] = msgList[0].replace('  ', ' ')                  # eliminate any double spaces
            msgList[0] = msgList[0].replace(', ', ',')                  # replace comma space with comma
            msgList[0] = msgList[0].replace(',,', ',')                  # eliminate any double commas
        # end of for loop

        msgList[0] = msgList[0].strip(' ,')                             # strip any leading/trailing spaces or commas
        msgList[0] = msgList[0].replace(',', ', ')                      # add a space after a comma for readability
        theMsg =  msgList[0] + ' ! ' + msgList[1]                       # reassemble the full message
        theMsg = theMsg.strip(' ,')                                     # strip any leading/trailing spaces or commas
        theMsg = theMsg.replace('  ', ' ')                              # eliminate any residual double spaces

        maxsize = cnf1.getSMSsize() - len('yyyy-mm-dd hh:mm:ss ')
        if len(theMsg) > maxsize :
            theMsg = theMsg[0:maxsize]                                  # max payload without datetime prefix
            logging.debug('DPM-008I The message (theMsg): %s', theMsg)
            return theMsg
        else : return theMsg
    else : return ''


# scan message for signficant tokens to determine alert level.
# "Non Alerts" are defined by "NotTheseTokens" in the config file.
# "Red Alerts" (e.g. home on fire) should always trigger an SMS
# "Yellow Alerts" (e.g. system Arming) may trigger an SMS.

def doAlerts(cnf1, mdm1, png1, msg, doLowerCase) :

    # if message contains a NON Alert token, we are done.
    if checkNonAlert(cnf1, msg.lower()) : return

    logging.debug('DPM-009I Checking for Red or Yellow alerts')
    if doLowerCase :
        redAlert = checkRedAlert(cnf1, msg.lower())
    else :
        redAlert = checkRedAlert(cnf1, msg)
    if redAlert :
        logging.debug('DPM-010I Red Alert, so attempting to send SMS')
        callCellPhones(cnf1, mdm1, msg, True, False, False)
    else :
        if doLowerCase :
            yellowAlert = checkYellowAlert(cnf1, msg.lower())
        else :
            yellowAlert = checkYellowAlert(cnf1, msg)
        if yellowAlert :
            pingCmd = cnf1.getPingCommand()
            inetAlive = png1.isInternetAlive(pingCmd)
            if inetAlive :
                logging.debug('DPM-011I Have internet connection; wireless communication not required')
            else :
                logging.debug('DPM-012I NO internet connection; wireless communication may be used')
                callCellPhones(cnf1, mdm1, msg, False, True, False)
        else : pass
    return


# check for "Red Alert" events, such as FIRE
def checkRedAlert(cnf1, msg) :
    tmpmsg = msg.split('!')         # Exclamation Mark is NOT arbitrary
    msg = tmpmsg[0]
    tokens = cnf1.getUrgentTokens()
    hit = False
    for tok in tokens :
        if tok in msg :
            hit = True
            logging.info('DPM-013I Red Alert - found  \'%s\'  in message', tok)
        else : pass
    # end of for loop

    if hit :
        return True
    else :
        return False


# check for "Yellow Alert" events, such as Arming/Disarming
def checkYellowAlert(cnf1, msg) :
    tmpmsg = msg.split('!')         # Exclamation Mark is NOT arbitrary
    msg = tmpmsg[0]
    tokens = cnf1.getImportantTokens()
    hit = False
    for tok in tokens :
        if tok in msg :
            hit = True
            logging.info('DPM-014I Yellow Alert - found  \'%s\'  in message', tok)
        else : pass
    # end of for loop

    if hit :
        return True
    else :
        return False

# check for non Alert" events
def checkNonAlert(cnf1, msg) :
    tmpmsg = msg.split('!')         # Exclamation Mark is NOT arbitrary    
    if '!' in msg :
        msg = tmpmsg[1]             # the decoded CID half of the message
    else :
        msg = tmpmsg[0]             # the decoded CID message alone

    tokens = cnf1.getNotTheseTokens()
    hit = False
    for tok in tokens :
        tok = tok.lower()           # passed message must have been lowercased
        if tok in msg :
            hit = True
            logging.info('DPM-013W NON Alert token found  \'%s\'  in message', tok)
        else : pass
    # end of for loop

    if hit :
        return True
    else :
        return False


# Conditionally, send an SMS to one or more cellphones.  The sendSMS() method of the MyModem object
# will check for and supress duplicate messages, which can and do arise, for example, if the
# connection to a Zone Expander module is lost, dozens of duplicate alerts would othewise be sent.
def callCellPhones(cnf1, mdm1, fullMsg, redAlert, yellowAlert, rebootAlert) :
    phones = []                                                        # initialize to an empty list
    resultList = optimizeSMS(cnf1)                                     # three (True/False) booleans are returned
    if ( (resultList[0] and redAlert ) or  (resultList[1] and yellowAlert) ) or  (resultList[2] and rebootAlert) :
        if redAlert :
            phones = cnf1.getRedAlertCellPhones()
            if len(phones) == 0 : logging.info('DPM-001W No cell phones for Red Alerts in configuration file')
        elif yellowAlert :
            phones = cnf1.getYellowAlertCellPhones()
            if len(phones) == 0 : logging.info('DPM-002W No cell phones for Yellow Alerts in configuration file')
        elif rebootAlert :
            phones = cnf1.getRebootAlertCellPhones()
            if len(phones) == 0 : logging.info('DPM-003W No cell phones for Reboot Alerts in configuration file')
        else : pass

        for ph in phones :
            logging.info('DPM-015I Sending to cell phone: %s %s', ph, fullMsg)
            rc = mdm1.sendSMS(fullMsg, ph)
            if (rc == 0) :
                updateMetrics(cnf1, 1)
            elif (rc == 4) :
                logging.info('DPM-004W SMS NOT sent; Send SMS Flag in config file is False')
            elif (rc == 8) :
                logging.info('DPM-005W Duplicate SMS NOT sent return code %s from sendSMS()', str(rc))
            elif (rc == 16) :
                logging.info('DPM-006W SMS NOT sent; Bad return code %s from sendSMS()', str(rc))
                logging.info('DPM-007W Trying one last time to send SMS successfully')
                rc = mdm1.sendSMS(fullMsg, ph)
                if (rc == 0) :
                    updateMetrics(cnf1, 1)
                else : pass
            else :
                logging.debug('DPM-008W Invalid return code %s from sendSMS()', str(rc))
        # end of for loop
        mdm1.doPruning()                                            # keep SMS history clean and tidy

    else : pass

    return


# update the count of SMS messages sent and the most recent sent date
def updateMetrics(cnf1, count) :
    now = datetime.now()
    sentdate = now.strftime("%Y-%m-%d %H:%M:%S")
    cnf1.updateSMSmetrics(count,sentdate)   # update SMS metrics in config file


# Optimize the use of our SMS Allocation for the current billing cycle
def optimizeSMS(cnf1):
    rd = cnf1.getRenewalDay()
    now = datetime.now()
    days = now.strftime("%d")               # grab current days
    month = now.strftime("%m")              # grab current month
    year = now.strftime("%Y")               # grab current year
    i_days = int(days)
    i_month = int(month)
    i_year = int(year)
    i_renewDay = int(rd)
    # If a renewal has occurred and the most recently sent SMS was before
    # or on the renewal date, then reset the SMS metrics in the config
    # file (i.e. set SMS-Count count to zero and SMS-LatestDate to 'UNKNOWN'
    # Format of SMS LastSentDate in Config file is:  YYYY-MM-DD HH:MM:SS
    if (i_days >= i_renewDay) :
        recentRenewalDate = year + '-' + month + '-' + str(i_renewDay).zfill(2) + ' ' + '00:00:00'
        logging.trace('DPM-016I Recent renewal date: %s', recentRenewalDate)
        ts1 = datetime.strptime(recentRenewalDate, "%Y-%m-%d %H:%M:%S")

        SMSLastSentDate = cnf1.getSMSLatestDate()
        logging.trace('DPM-017I SMS last sent date: %s', SMSLastSentDate)
        if SMSLastSentDate == 'UNKNOWN' :   # no SMS yet sent this billing cycle, hence no date sent.
            SMSLastSentDate = recentRenewalDate
            logging.trace('DPM-018I Using SMS last sent date of: %s', SMSLastSentDate)
        ts2 = datetime.strptime(SMSLastSentDate, "%Y-%m-%d %H:%M:%S")

        diff = (ts1 - ts2).days # was most recently sent SMS before the latest renewal?
        logging.trace('DPM-019I Days difference: %s', diff)
        if (diff >= 0) : # SMS last sent before or essentially on the renewal date
            logging.trace('DPM-020I Will now reset SMS metrics')
            cnf1.resetSMSmetrics()
        else : pass

    else : pass

    SMS_allowance = cnf1.getSMS_Allowance()
    logging.trace('DPM-021I SMS Allowance: %s', SMS_allowance)
    sentSMS = cnf1.getCountSMS()
    instock = SMS_allowance - sentSMS
    logging.trace('DPM-022I Number of SMS remaining: %s', instock)

    # Calculate days until next Renewal, then see how many SMS have
    # already been sent and calculate the risk of prematurely exhausting
    # our allocation of SMS messages.
    if (i_days > i_renewDay) :
        logging.trace('DPM-023I Today ( %s ) > Renewal Day ( %s )', days, rd)
        if i_month == 12 :
            intnextmnth = 1
            intnextyr = i_year + 1
            # dt1 is the start date
            dt1 = year + '-' + month + '-' + days
            logging.trace('DPM-024I Current date: %s', dt1)
            dt2 = str(intnextyr) + '-' + str(intnextmnth).zfill(2) + '-' + str(i_renewDay).zfill(2)
            logging.trace('DPM-025I Next SMS renewal on: %s', dt2)
        else :
            # dt1 is the start date
            dt1 = year + '-' + month + '-' + days
            logging.trace('DPM-026I Current date: %s', dt1)
            intnextmnth = i_month + 1
            dt2 = str(i_year) + '-' + str(intnextmnth).zfill(2) + '-' + str(i_renewDay).zfill(2)
            logging.trace('DPM-027I Next SMS renewal on: %s', dt2)
    elif (i_days <= i_renewDay)  :
        logging.trace('DPM-028I Today ( %s ) LE Renewal Day ( %s )', days, rd)
        # dt1 is the start date
        dt1 = year + '-' + month + '-' + days
        logging.trace('DPM-029I Current date: %s', dt1)
        dt2 = str(i_year) + '-' + str(i_month).zfill(2) + '-' + str(i_renewDay).zfill(2)
        logging.trace('DPM-030I Next SMS renewal on: %s', dt2)

    ts1 = datetime.strptime(dt1, "%Y-%m-%d")
    ts2 = datetime.strptime(dt2, "%Y-%m-%d")
    daysToGo = abs((ts2 - ts1).days)
    if daysToGo == 0 :
        daysToGo = 30
        logging.trace('DPM-031I About %s days before next renewal', daysToGo)  # approx days to next renewal
    else :
        logging.trace('DPM-032I %s days before next renewal', daysToGo) # days to next renewal

    redphcnt = cnf1.getRedAlertCellPhoneCount()
    yelphcnt = cnf1.getYellowAlertCellPhoneCount()
    bootphcnt = cnf1.getRebootAlertCellPhoneCount()
    inbdphcnt = cnf1.getInboundSMSCellPhoneCount()
    avgphonect = (redphcnt + yelphcnt + bootphcnt + inbdphcnt) / 4

    logging.trace('DPM-033I Average phone count: %.2f', avgphonect)
    if avgphonect == 0 :
        logging.error('DPM-005E NO cell phone numbers in config file')
        return [False, False, False]

    # riskpc is the % risk of prematurely exhausting our SMS allowance
    divisor = (SMS_allowance - sentSMS)
    if divisor == 0 : divisor = 1           # circumvent zero division problem
    dividend = avgphonect * daysToGo
    riskpc = round ( (dividend / divisor ) * 100 )
    logging.trace('DPM-034I Percentage risk of exhausting SMS allocation: %s', riskpc)

    if (riskpc < 100 and ( (sentSMS + avgphonect) <= SMS_allowance) ) :
        redAlert = True
        yellowAlert = True
        rebootAlert = True
        logging.debug('DPM-035I Red, Yellow and Reboot Alerts allowed')
    elif (riskpc >= 100 and ( (sentSMS + avgphonect) <= SMS_allowance) ) :
        redAlert = True
        yellowAlert = False
        rebootAlert = False
        logging.debug('DPM-036I Red Alerts allowed')
    else :
        logging.debug('DPM-009W No SMS alerts allowed')
        redAlert = False
        yellowAlert = False
        rebootAlert = False

    return [redAlert, yellowAlert, rebootAlert]


# check the syslog for recent CID entries.  If the syslog has a recent
# unreported CID that TPI has not reported, that CID will be returned for
# subsequent decoding, token searching and possible alerting via SMS.
def scanSyslog(cnf1, slg1, msg03txt) :
    logging.trace('DPM-037I About to scan Syslog ... ')
    checkLogScan = {}
    finalCheckLS = {}
    # maximum age of a syslog entry to be considered "recent"
    RECENT_SECS = cnf1.getRecentSecondsEVL4()
    logging.trace('DPM-038I RECENT_SECS is: %s', RECENT_SECS)
    ADJACENT_SECS = cnf1.getAdjacentSecondsEVL4()
    logging.trace('DPM-039I ADJACENT_SECS is: %s', ADJACENT_SECS)
    logscan = slg1.getLogRecsWithCID()
    logging.trace('DPM-040I Syslog scan returned: %s', logscan)
    now = datetime.now()
    nowts = int(datetime.timestamp(now))

    # find and save "recent" event(s) from the scanned syslog entries
    for x in logscan :
        tmpkey = int(x)
        diff = abs(nowts - tmpkey)
        if diff <= RECENT_SECS :
            checkLogScan[x] = logscan[x]     # save this recent event
        else : pass
    # end of for loop

    # check each "recent" syslog CID against TPI's CIDs (in msg03txt
    # which may be an empty dictionary). If there is an "adjacent"
    # TPI vs. Syslog CID match that CID will be ignored.
    # If a "recent" unreported syslog CID is not matched, it will be
    # flagged as reported, in anticipation of its subsequent use.

    keyz = sorted(msg03txt.keys(), reverse=True)    # most recent first
    isMatched = None
    for key1 in checkLogScan :
        isMatched = False     # guard against msg03txt being empty
        for key2 in keyz :
            if msg03txt[key2].strip('CID=') == logscan[key1] :
                ts1 = int( key2 / 1000000000)       # eliminate nano seconds
                ts2 = int(key1)
                diff = abs(ts1 - ts2)
                if (diff <= ADJACENT_SECS) :
                    logging.debug('DPM-041I Syslog and TPI CIDs are recent, adjacent and match: %s', checkLogScan[key1])
                    slg1.flagAsReportedCID(key1) # set reported flag for this syslog CID
                    isMatched = True
                    break
                else :
                    pass
            else :
                pass
        # end of inner (CID matching and age checking) loop
        if isMatched is False : # this syslog CID has not yet been reported via TPI
            finalCheckLS[key1] = logscan[key1]
        else : pass

    # end of outer for loop

    if (len(finalCheckLS) > 0 ) :
        # just in case there is more than one, we'll use the least recent
        keys = sorted(finalCheckLS.keys()) # least recent first - chronological order
        logging.debug('DPM-042I Syslog captured an event before TPI did: CID=%s', finalCheckLS[keys[0]])
        slg1.flagAsReportedCID(keys[0])     # prevent duplicate alerts
        return finalCheckLS[keys[0]]
    else :
        return None


# If a TPI (msg03txt) CID matches an ajacent unreported, recent syslog CID,
# flag the matching syslog CID as reported and allow the TPI CID to take
# precedence.
# Example: of msg03txt: {1657479585020845200: 'CID=3373010010', 1657479615989407200: 'CID=1441010010'}
# Example of recentCIDs: {1657479585.0: '3131010030', 1657479615.0: '1441010010'}
def checkSyslog(cnf1, slg1, msg03txt, isReptd) :
    logging.trace('DPM-043I About to check Syslog ... ')
    RECENT_SECS = cnf1.getRecentSecondsEVL4()
    logging.trace('DPM-044I RECENT_SECS is: %s', RECENT_SECS)
    ADJACENT_SECS = cnf1.getAdjacentSecondsEVL4()
    logging.trace('DPM-045I ADJACENT_SECS is: %s', ADJACENT_SECS)
    recentCIDs = slg1.getRecentCIDs(RECENT_SECS, isReptd)
    keysSLG = sorted(recentCIDs.keys(), reverse=True)   # most recent first
    (status := 'reported') if isReptd else (status := 'unreported')
    logging.trace('DPM-046I Recent, %s CIDs from syslog: %s', status, recentCIDs)
    keysTPI = sorted(msg03txt.keys(), reverse=True)    # most recent first

    isMatched = False
    for key1 in keysSLG :
        if len(keysTPI) > 0 :
            if msg03txt[keysTPI[0]].strip('CID=') == recentCIDs[key1] :
                ts1 = int( keysTPI[0] / 1000000000)       # eliminate nano seconds
                ts2 = int(key1)
                diff = abs(ts1 - ts2)
                if (diff <= ADJACENT_SECS) :
                    logging.debug('DPM-047I TPI and Syslog CIDs are recent, adjacent and match: %s', recentCIDs[key1])
                    if not isReptd : slg1.flagAsReportedCID(key1) # set reported flag for this syslog CID
                    isMatched = True
                    break
                else :
                    pass
            else :
                pass
        else :
            pass
        # end of inner CID matching loop
    # end of outer for loop

    return isMatched

# process inbound SMS request, post massaging and simplification
def doInboundSMS(cnf1, mdm1, tel1) :
    # example:   [['1', '9990001212', 'Arm', 'partition', 'one', 'night', 'stay'], ['2', '9990001212', 'Status?']]
    SMSrequest = mdm1.getUnreadSMS()
    rlen = len(SMSrequest)
    if ( (rlen == 1) and (SMSrequest[0] == 'OK') ) :
        return              # OK response from modem, but no new inbound SMS
    elif (rlen == 0) :
        return              # completely empty list -- modem error condition

    logging.debug('DPM-048I inbound SMS request(s) %s', SMSrequest)
    updateMetrics(cnf1, rlen) # account for the inbound SMS message(s)

    for x in SMSrequest :
        validphone = cnf1.checkInboundPhoneSMS(x[1])
        if validphone is None :
            logging.debug('DPM-010W Invalid phone number %s', x[1])
        else :
            xlen = len(x)
            str1 = ''
            for i in range(2, xlen) :
                str1 = str1 + x[i] + ' ' # join list elements back into a string
            str1 = str1.upper()
            if 'STATUS' in str1 :
                logging.debug('DPM-049I Found STATUS request in \"%s\"', str1)
                status = tel1.getCurrentStatus()
                status = status.replace(',',', ') # add space after each intervening comma
                if cnf1.doSendSMS() :   # if Config flag is True, send SMS
                    rc = mdm1.sendSMS(status, validphone)
                    if (rc == 0) :
                        updateMetrics(cnf1, 1) # account for the outbound SMS message
                    else : pass
                else :
                    logging.debug('DPM-050I SMS NOT sent; Send SMS Flag in config file is False')
            # armMode:  '2' = AWAY ; '3' = STAY ; '33' = NIGHT STAY ; '7' = INSTANT
            elif 'ARM' in str1 :
                logging.debug('DPM-051I Found ARM request in \"%s\"', str1)
                partition = '1'     # default partition
                if( ('2' in str1) or ('TWO' in str1) ) :
                    partition = '2'
                armMode = '2'       # default AWAY arming mode
                if( ('STAY' in str1) ) :
                    armMode = '3'
                if( ('NIGHT' in str1) ) :
                    armMode = '33'
                if( ('INSTANT' in str1) ) :
                    armMode = '7'
                logging.debug('DPM-052I About to arm -- Partition: %s, Arming mode: %s', partition, armMode)
                tel1.systemArm(validphone, partition, armMode)
            else :
                logging.debug('DPM-011W Invalid Request %s', str1)

    # end of for loop

    return



if __name__ == "__main__":
        main()
