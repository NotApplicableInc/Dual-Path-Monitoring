#!/usr/bin/python3
"""
Copyright (c) N. A. Inc.  2022
This program is free software per V3, or later version, of the GNU General Public License.
It is distributed AS-IS, WITHOUT ANY WARRANTY, or implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.
"""

from datetime import datetime
import time
from time import sleep
import sys
import subprocess
import logging
from luhn import *

# The python Telnet library is to be deprecated after Python V3.11
# https://peps.python.org/pep-0594/#telnetlib.  However, as an
# insurance policy, a copy of that source code will be bundled in
# with this overall project.

from telnetlib import Telnet                # Python's telnet library

class TelnetEVL4 :

# Version 1.0
# A Python class to communicate with an EVL4 via an IP socket using
# the python Telnet library. There can only be one active session.

# TO DO: Ideally, should enforce a Singleton, since multiple instances
# for just one EVL4 is illogical, but this works fine for now.

    # security system Partition states
    pstates = {1 : 'READY', 2 : 'READY TO ARM', 3 : 'NOT READY', 4 : 'ARMED STAY', 5 : 'ARMED AWAY',
        6 : 'ARMED INSTANT', 7 : 'EXIT DELAY', 8 : 'ALARMING NOW', 9 : 'WAS ALARMING', 10 : 'ARMED MAXIMUM'}

    # class constructor.
    def __init__(self, url, host, port, passwd, timeout, retries, rebootOnly) :
        logging.info('TEL-001I TelnetEVL4 object created')

        self.tn = None
        self.rebooturl = url        # EVL4's reboot URL
        self.host = host            # EVL4's IPV4 address
        self.port = port            # EVL4's port (4025)
        self.passwd = passwd        # EVL4's cleartext password
        self.timeout = timeout      # EVL4's connection attempt timeout
        self.retries = retries      # EVL4's connection attempt retry count


    # A dictionary of dictionaries of the most recent messages, by type. A value
    # of 2 for MAX_HISTORY is optimal.  A value of 1 prevents elimination of duplicate
    # messages. A value of 3 obscures the current status of the security system.
    # Do NOT change this value, else the behavior of DPM.py will be unpredictable.
        self.MAX_HISTORY = 2

        self.recentMsgs = {
            'msg00raw' : {},
            'msg00txt' : {},
            'msg01raw' : {},
            'msg01txt' : {},
            'msg02raw' : {},
            'msg02txt' : {},
            'msg03raw' : {},
            'msg03txt' : {},
            'msgFFraw' : {},
            'msgFFtxt' : {},
            'req00' : {},
            'rsp00' : {},
            'req01' : {},
            'rsp01' : {},
            'req02' : {},
            'rsp02' : {},
            'req03' : {},
            'rsp03' : {},
            'msgflag00' : {},
            'msgflag01' : {},
            'msgflag02' : {},
            'msgflag03' : {},
            'msgflagFF' : {}
        }   # end of recentMsgs

        if rebootOnly :
            # for rebootOnly, we don't need a socket ("Telnet") connection to the EVL4
            pass
        else :
            # We will keep trying to connect to the EVL4 until we succeed,
            # exhaust retries, or the invoking application is terminated.
            for x in range(0, self.retries) :
                try :
                    self.tn = Telnet(self.host, self.port, self.timeout)
                    logging.debug('TEL-002I Telnet connection: %s', self.tn)
                    self.tn.read_until(b'Login:')
                    self.tn.write(self.passwd.encode('utf-8') + "\n".encode('utf-8'))
                    reply = self.tn.read_until(b'OK', self.timeout).decode('utf-8')
                    reply = reply.strip()
                    logging.debug('TEL-003I Reply from login to EVL4 was %s', reply)
                    if reply.endswith('OK') :  # "FAILED" is the other possibility
                        break
                    else :
                        raise Exception('failed to login to EVL4')

                except (Exception) as ex :
                    logging.error('TEL-001E Could not connect to EVL4\'s TPI, but will re-try: %s', str(ex))
                    if (self.tn is not None) :
                         self.tn.close()
                         self.tn = None
                    else : pass
                    sleep(20)       #snooze and hope for better luck next time around

        # end of for loop


    # checkConnection
    def checkConnection(self) :
        return self.tn


    # get next message
    def getNextMessage(self) :
        try :
            msg = self.tn.read_until(b'$', self.timeout).decode('utf-8')
            msg = msg.strip()                       # remove any leading/trailing whitespace
            logging.trace('TEL-004I message (post strip) from EVL4 is: %s', msg)

            # msg type ^09 is an invalid type, but is used for 'stay awake' requests
            if msg.startswith('^09'):
                if msg.startswith('^09,02$') :  # '02' = "Unknown Command" error
                    logging.debug('TEL-005I EVL4 responded \"OK\" to \'stay awake\' request')
                else :
                    logging.debug('TEL-001W EVL4 did NOT respond \"OK\" to \'stay awake\' request')

            # poll requests are used to stop the EVL4 rebooting every 20 minutes
            # should connectivity to the Internet be lost for an extended period
            elif msg.startswith('^00') :
                self.recentMsgs['rsp00'][time.time_ns()] = msg
                if msg.startswith('^00,00$') :
                    logging.debug('TEL-006I EVL4 responded \"OK\" to poll request')
                else :
                    logging.debug('TEL-002W EVL4 did NOT respond \"OK\" to poll request')

            elif msg.startswith('^01') :
                self.checkRC(msg)
                self.recentMsgs['rsp01'][time.time_ns()] = msg
            elif msg.startswith('^02') :
                self.checkRC(msg)
                self.recentMsgs['rsp02'][time.time_ns()] = msg
            elif msg.startswith('^03') :
                self.checkRC(msg)
                self.recentMsgs['rsp03'][time.time_ns()] = msg

            elif msg.startswith('%00') :
                ts00 = time.time_ns()
                self.recentMsgs['msg00raw'][ts00] = msg
                self.recentMsgs['msg00txt'][ts00] = self.doType00(msg)
                self.recentMsgs['msgflag00'][ts00] = '1'
            elif msg.startswith('%01') :
                ts01 = time.time_ns()
                self.recentMsgs['msg01raw'][ts01] = msg
                self.recentMsgs['msg01txt'][ts01] = self.doType01(msg)
                self.recentMsgs['msgflag01'][ts01] = '1'
            elif msg.startswith('%02') :
                ts02 = time.time_ns()
                self.recentMsgs['msg02raw'][ts02] = msg
                self.recentMsgs['msg02txt'][ts02] = self.doType02(msg)
                self.recentMsgs['msgflag02'][ts02] = '1'
            elif msg.startswith('%03') :
                ts03 = time.time_ns()
                self.recentMsgs['msg03raw'][ts03] = msg
                self.recentMsgs['msg03txt'][ts03] = self.doType03(msg)
                self.recentMsgs['msgflag03'][ts03] = '1'
            elif msg.startswith('%FF') :
                tsff = time.time_ns()
                self.recentMsgs['msgFFraw'][tsff] = msg
                self.recentMsgs['msgFFtxt'][tsff] = self.doTypeFF(msg)
                self.recentMsgs['msgflagFF'][tsff] = '1'
            elif (msg == "") :
                pass
            else :
                logging.debug('TEL-002E Unexpected message type %s', msg)

        except (Exception) as ex :
            logging.error('TEL-003E Error accessing EVL\'s TPI: %s', str(ex))
            self.doReconnect()

        self.pruneAll()                                 # drop oldest, surplus messages
        logging.trace('TEL-007I Most recent messages %s', self.recentMsgs)
        return self.recentMsgs


    # process Alpha Keypad type '%00' message
    def doType00 (self, msg) :

    # Honeywell 6160 Alpha keypads may revolve multiple text messages
    # for several minutes, for example, "LO BAT", "AC LOSS", and "ARMED STAY"
    # Example message: %00,01,8C08,08,03,ARMED ***STAY***You may exit now$
    # Bit flags (third field from left) of message type "00", defined
    # by V1.03 of EVL4's TPI (Third Party Interface) specification.
    # For example: "8C08" means "ARMED STAY, AC PRESENT"

    # leftmost nibble
    #    ARMED_STAY                     = 0x80
    #    LOW_BATTERY                    = 0x40
    #    FIRE                           = 0x20
    #    SYSTEM_READY                   = 0x10
    # left nibble
    #    UNUSED_1                       = 0x08
    #    UNUSED_2                       = 0x04
    #    SYSTEM_TROUBLE                 = 0x02
    #    FIRE_ZONE_ALARM                = 0x01
    # right nibble
    #    ARMED_NO_DELAY                 = 0x80
    #    UNUSED_3                       = 0x40
    #    CHIME                          = 0x20
    #    ZONES_BYPASSED                 = 0x10
    #rightmost nibble
    #    AC_PRESENT                     = 0x08
    #    ARMED_AWAY                     = 0x04
    #    ALARM_IN_MEMORY                = 0x02
    #    ALARMED_STATUS                 = 0x01

    # Test each bit of two hex status bytes (converted to a 2 byte integer)
    # and create an equivalent textual status.  Some bit flags are NOT
    # mutually exclusive, for example, can have "ARMED and LOW BATTERY"

        status = ''             # initialize overall status message string
        msglist=msg.split(',')  # split out the message status bit flags
        myint = int(msglist[2], 16)   # convert hex chars to integer for bit flag tests

        if  (myint & 1 << 15 ) : status = status +  'ARMED STAY,'
        if  (myint & 1 << 14 ) : status = status +  'LOW BATTERY,'
        if  (myint & 1 << 13 ) : status = status +  'FIRE,'
        if  (myint & 1 << 12 ) : status = status +  'SYSTEM READY,'
        #if  (myint & 1 << 11 ) : status = status +  'UNUSED_1'
        #if  (myint & 1 << 10 ) : status = status +  'UNUSED_2'
        if  (myint & 1 << 9 ) : status = status +  'SYSTEM TROUBLE,'
        if  (myint & 1 << 8 ) : status = status +  'FIRE ZONE ALARM,'
        if  (myint & 1 << 7 ) : status = status +  'ARMED NO DELAY,'
        #if  (myint & 1 << 6 ) : status = status +  'UNUSED_3'
        if  (myint & 1 << 5 ) : status = status +  'CHIME,'
        if  (myint & 1 << 4 ) : status = status +  'ZONES BYPASSED,'
        if  (myint & 1 << 3) :  status = status +  'AC PRESENT,'
        else : status = status +  'AC LOSS,'
        if  (myint & 1 << 2 ) : status = status +  'ARMED AWAY,'
        if  (myint & 1 << 1 ) : status = status +  'ALARM IN MEMORY,'
        if  (myint & 1 ) : status = status +  'ALARMED STATE,'
        # There does not seem to be an explicit bit flag for "NIGHT-STAY"
        # or 'DISARMED' so, reluctanty, we will do string searches.
        if msg.count('NIGHT-STAY') > 0 : status = status + 'NIGHT-STAY,'
        if msg.count('DISARMED') > 0 : status = status + 'DISARMED,'
        return status.strip(' ,')  # drop trailing comma and any whitespace


    # process Zone State Change type '01' message.  Returns a string of
    # three-digit, triggered zone numbers, e.g. '004,008,016'
    def doType01(self, msg) :
    # Eight blocks of 4 hex chars (max 128 zones) little-endian ("LE")
    # Example 1: Zone-4 triggered
    #   %01,08000000000000000000000000000000$
    #   0800 = '0000 1000 0000 0000' (BE) --> '0001 0000 0000 0000' (LE)
    # Example 2: Zone-16 triggered
    #   %01,00800000000000000000000000000000$
    #   0080 = '0000 0000 1000 0000' (BE) --> '0000 0000 0000 0001' (LE)
    # Example 3: Zones 4 and 8 triggered
    #   %01,88000000000000000000000000000000$
    #   8800 = '1000 1000 0000 0000' (BE) --> '0001 0001 0000 0000' (LE)
    # Example 4: Zones 4 and 16 triggered
    #   %01,08800000000000000000000000000000$
    #   0880 = '0000 1000 1000 0000' (BE) --> '0001 0000 0000 0001' (LE)
        msglst = msg.split(',')
        zones = msglst[1]
        zones = zones.strip('$')
        znums = ''
        for x in range(0,8) :  # x = 0,2,3,4,5,6,7
            fourhex = zones[(x*4) : (x*4 + 4)]  # grab 4 hex chars per iteration
            zbits = int(fourhex, 16) # convert hex chars to int for bit flag tests
            # Zone flags are little endian, accomodated here by the bit testing order.
            if (zbits & 1 << 8 )  : znums = znums + str('%03d' % ((16 * x) + 1)) + ','
            if (zbits & 1 << 9 )  : znums = znums + str('%03d' % ((16 * x) + 2)) + ','
            if (zbits & 1 << 10 ) : znums = znums + str('%03d' % ((16 * x) + 3)) + ','
            if (zbits & 1 << 11 ) : znums = znums + str('%03d' % ((16 * x) + 4)) + ','
            if (zbits & 1 << 12 ) : znums = znums +  str('%03d' % ((16 * x) + 5)) + ','
            if (zbits & 1 << 13 ) : znums = znums + str('%03d' % ((16 * x) + 6)) + ','
            if (zbits & 1 << 14 ) : znums = znums + str('%03d' % ((16 * x) + 7)) + ','
            if (zbits & 1 << 15)  : znums = znums + str('%03d' % ((16 * x) + 8)) + ','
            if (zbits & 1 << 0 )  : znums = znums + str('%03d' % ((16 * x) + 9)) + ','
            if (zbits & 1 << 1 )  : znums = znums + str('%03d' % ((16 * x) + 10)) + ','
            if (zbits & 1 << 2 )  : znums = znums + str('%03d' % ((16 * x) + 11)) + ','
            if (zbits & 1 << 3 )  : znums = znums + str('%03d' % ((16 * x) + 12)) + ','
            if (zbits & 1 << 4 )  : znums = znums + str('%03d' % ((16 * x) + 13)) + ','
            if (zbits & 1 << 5 )  : znums = znums + str('%03d' % ((16 * x) + 14)) + ','
            if (zbits & 1 << 6 )  : znums = znums + str('%03d' % ((16 * x) + 15)) + ','
            if (zbits & 1 << 7 )  : znums = znums + str('%03d' % ((16 * x) + 16)) + ','
            if (znums != '') : znums = znums.strip(',') # strip final trailing comma

        return znums  # string of 3-digit, comma delimted, triggered zone numbers


    # process Partition State type '02' message (maximum 8 partitions)
    def doType02(self, msg) :
    # Example: %02,0A01000000000000$ (partition #1 Armed Max. ; partition #2 Ready)
    # Honeywell Vista home security systems typically support up to 2 partitions.
    # Values below per V1.03 of EVL4's TPI (Third Party Interface) specification.
    # 00 – Partition is not Used/Doesn't Exist
    # 01 – Ready
    # 02 – Ready to Arm (Zones are Bypasses)
    # 03 – Not Ready
    # 04 – Armed in Stay Mode
    # 05 – Armed in Away Mode
    # 06 – Armed Instant (Zero Entry Delay - Stay)
    # 07 – Exit Delay (not implemented on all platforms)
    # 08 – Partition is in Alarm
    # 09 – Alarm Has Occurred (Alarm in Memory)
    # 10 – Armed Maximum (Zero Entry Delay - Away)

        notice = ''
        msglst = msg.split(',')
        partitions = msglst[1]
        partitions = partitions.strip('$')
        for x in range(0,8) :  # 0,2,3,4,5,6,7
            part = 'PTN' + str(x+1)
            state = partitions[(x*2) : (x*2 + 2)]       # grab 2 chars per iteration
            intstate = int(state, 16)                   # convert hex chars to integer
            if intstate != 0 :
                notice = notice + part + '=' + self.pstates[intstate] + ','
        notice = notice.strip(',')                      # strip final trailing comma
        return(notice)


    # process Contact ID "CID" type '03'message
    def doType03(self, msg) :
    # example: %03,1373010010$
        msglst = msg.split(',')
        tmpstr = str(msglst[1])
        return 'CID=' + tmpstr.strip('$')


    # process Zone Timers type 'FF' message (keep for future enhancement)
    # TO DO:  transform raw zone times for active zones only
    def doTypeFF(self, msg) :
    # Zone Timer message
    # Example: %FF,00000000E2F6D5F70000 ... ... 0000$  Zones 3 and 4 have timers running.
    # A 256 character packed HEX string representing 64 zone timers. Zone timers
    # count down from 0xFFFF (zone is open) to 0x0000 (zone closed eons ago). Each
    # “tick” of the zone time is 5 seconds. For example, 0xFFFE means “5 seconds ago”,
    # but zone timers are LITTLE ENDIAN, so that would be transmitted as FEFF
        return 'Zone nnn Closed mm Minutes Ago'


    # issue poll command to TelnetEVL4.  It will prevent EVL4 from rebooting
    # every 20 minutes if the EVL4 cannnot communicate with Eyezon's servers.
    def doPoll(self) :
        try :
            logging.debug('TEL-008I Submitting poll request to EVL4')
            self.tn.write(b'^00,$')
            self.recentMsgs['req00'][time.time_ns()] = '^00,$'

        except (Exception) as ex :
            logging.error('TEL-004E Error accessing EVL\'s TPI: %s', str(ex))
            self.doReconnect()
            if self.tn is not None :
                logging.debug('TEL-009I Resubmitting poll request to EVL4')
                self.tn.write(b'^00,$')
                self.recentMsgs['req00'][time.time_ns()] = '^00,$'
            else : pass

    # when EVL4 boots it talks to Partition 1 by default.  However, some
    # Honeywell systems (e.g. Vista 20P) have more than one partition
    def doChangePartition(self, partnum) :
        req = '^' + '01,' + partnum + '$'
        try :
            logging.debug('TEL-010I Submitting Change Partition request %s', req)
            self.tn.write(req.encode('utf-8'))
            self.recentMsgs['req01'][time.time_ns()] = req

        except (Exception) as ex :
            logging.error('TEL-005E Error accessing EVL\'s TPI: %s', str(ex))
            self.doReconnect()
            if self.tn is not None :
                logging.debug('TEL-011I Resubmitting Change Partition request %s', req)
                self.tn.write(req.encode('utf-8'))
                self.recentMsgs['req01'][time.time_ns()] = req
            else : pass

    # request a subsequent dump of the EVL4's Zone Timers array
    def doDumpZoneTimers(self) :
        try :
            logging.debug('TEL-012I Submitting Dump Zone Timers request')
            self.tn.write(b'^02,$')
            self.recentMsgs['req02'][time.time_ns()] = '^02,$'

        except (Exception) as ex :
            logging.error('TEL-006E Error accessing EVL\'s TPI: %s', str(ex))
            self.doReconnect()
            if self.tn is not None :
                logging.debug('TEL-013I Resubmitting Dump Zone Timers request')
                self.tn.write(b'^02,$')
                self.recentMsgs['req02'][time.time_ns()] = '^02,$'
            else : pass


    # send valid keystrokes <0..9,A,B,C,D,*,#> to the target parition
    def doKeystrokesToPartition(self, partnum, keystrokes) :
        req = '^' + '03,' + partnum + '$' + keystrokes
        try :
            logging.debug('TEL-014I Submitting Process Keystrokes request %s', req)
            self.tn.write(req.encode('utf-8'))
            self.recentMsgs['req03'][time.time_ns()] = req

        except (Exception) as ex :
            logging.error('TEL-007E Error accessing EVL\'s TPI: %s', str(ex))
            self.doReconnect()
            if self.tn is not None :
                logging.debug('TEL-015I Resubmitting Process Keystrokes request %s', req)
                self.tn.write(req.encode('utf-8'))
                self.recentMsgs['req03'][time.time_ns()] = req
            else : pass


    # send a deliberately invalid request.  This can be used as a "stay awake"
    # request to prevent loss of the socket ('telnet') connection to an EVL4
    # module that, due to prolonged internet outage, cannot talk to Eyezon's
    # servers, even if doPoll() requests are also issued more frequently than every
    # 20 minutes, to prevent EVL4's watchdog timer from triggering an EVL4 reboot.
    def doInvalidRequest(self) :
        try :
            logging.debug('TEL-016I Submitting \'stay awake\' to EVL4')
            self.tn.write(b'^09,$')     # deliberately invalid request type

        except (Exception) as ex :
            logging.error('TEL-008E Error accessing EVL\'s TPI: %s', str(ex))
            self.doReconnect()
            if self.tn is not None :
                logging.debug('TEL-017I Resubmitting \'stay awake\' to EVL4')
                self.tn.write(b'^09,$')     # deliberately invalid request type
            else : pass


    # method to prune surplus and aged historical messages
    def pruneAll(self) :
        for key1 in self.recentMsgs :
            keys = sorted(self.recentMsgs[key1].keys())
            popLim = 0
            length = len(keys)
            if length > self.MAX_HISTORY : popLim = (length - self.MAX_HISTORY)
            for x in range(0, popLim) :
                k = keys[x]
                self.recentMsgs[key1].pop(k)
        return


    # Check return code from prior request
    # per V1.03 of EVL4's TPI (Third Party Interface) specification:
    # 0 No Error – Command Accepted
    # 1 Receive Buffer Overrun (a command was received while one still being processed)
    # 2 Unknown Command
    # 3 Syntax Error. Data appended to the command is incorrect
    # example:  '09,02$'  response to deliberately invalid request '09'
    def checkRC(self, msg) :
        if msg.endswith(',00$') :
            pass
        else :
            logging.debug('TEL-009E Bad return code %s from request to EVL4', msg)


    # get current security system status.  We'll double check for consistent
    # messages to reduce risk of delivering stale/incorrect status information.
    def getCurrentStatus(self) :
        msg1 = None
        msg2 = None
        for x in range (0, 10) : # a while loop would be too dangerous here
            logging.trace('TEL-018I About to get Messages for iteration # %s', x)
            self.getNextMessage()
            keys1 = sorted(self.recentMsgs['msg00txt'].keys(), reverse=True) # most recent first
            if len(keys1) > 1 :
                msg1 = self.recentMsgs['msg00txt'][keys1[0]]
            sleep(10) # NOT an arbitrary value; the EVL4 issues updates about every 10 seconds.
            self.getNextMessage()
            keys2 = sorted(self.recentMsgs['msg00txt'].keys(), reverse=True) # most recent first
            if len(keys2) > 1 :
                msg2 = self.recentMsgs['msg00txt'][keys2[0]]
            if ( ((msg1 != None) and (msg2 != None)) and (msg1 == msg2) ) :
                logging.debug('TEL-019I 1st status check = %s ; 2nd status check = %s', msg1, msg2)
                break
            logging.debug('TEL-020I 1st status check = %s ; 2nd status check = %s', msg1, msg2)

        return msg2


    # Arm the system using an ARM-ONLY privilege-level, security system user account.
    # SMS text messages are NOT secure.  Do NOT use SMS to disarm a security system,
    # as that would need public-key-private-key encryption or similarly robust security.
    # armtype:  '2' = AWAY ; '3' = STAY ; '33' = NIGHT STAY ; '7' = INSTANT
    def systemArm(self, cellphone, partition, armtype) :
        cellreverse = cellphone[::-1]   # some 'security', via obscurity
        cellchk1 = generate(cellphone)  # some 'security', via Luhn obscurity
        cellchk2 = (cellchk1 + 7)       # some 'security' via obscurity
        if cellchk2 > 9 : cellchk2 -= 9 # some 'security' via obscurity
        keystrokes = cellreverse[0:2] + str(cellchk1) + str(cellchk2) + armtype
        self.doKeystrokesToPartition(partition, keystrokes)
        return


    def doReconnect(self) :
        # We will keep trying to reconnect to the EVL4 until we succeed,
        # or the invoking application is terminated.
        if (self.tn is not None) :
             self.tn.close()
             self.tn = None

        for x in range(0, self.retries) :
            try :
                self.tn = Telnet(self.host, self.port, self.timeout)
                logging.debug('TEL-021I Telnet connection is now: %s', self.tn)
                self.tn.read_until(b'Login:')
                self.tn.write(self.passwd.encode('utf-8') + "\n".encode('utf-8'))
                reply = self.tn.read_until(b'OK', self.timeout).decode('utf-8')
                reply = reply.strip()
                logging.debug('TEL-022I Reply from login to EVL4 was %s', reply)
                if reply.endswith('OK') :  # "FAILED" is the other possibility
                    break
                else :
                    raise Exception('failed to login to EVL4')

            except (ConnectionResetError, OSError, Exception) as ex :
                logging.error('TEL-010E Could not connect to EVL4\'s TPI, but will re-try: %s', str(ex))
                if (self.tn is not None) :
                    self.tn.close()
                    self.tn = None
                else : pass
                sleep(20)       # snooze and hope for better luck next time around

        # end of for loop

        if self.tn is None :
            self.doReboot()
        else :
            logging.info('TEL-023I Telnet connection is now: %s', self.tn)


    # reboot the EVL4 IP interface module
    def doReboot(self) :
        if (self.tn is not None) :  # check as not just doReconnect() can invoke this method
             self.tn.close()
             self.tn = None
        tmpstr1 = 'user:' + self.passwd
        cmd = ['curl', '-u']
        cmd.append(tmpstr1)
        cmd.append(self.rebooturl)
        rc = subprocess.run(args=cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        if rc == 0 :
            logging.info('TEL-024I The curl command to reboot EVL4 succeeded!')
        else :
            logging.info('TEL-011E The curl command to reboot EVL4 failed')
        sleep(20)       # give the EVL4 time to reboot and get ready


    # class finalizer ('destructor')
    def __del__(self) :
        del self.tn


  # end of TelnetEVL4 class
