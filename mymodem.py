#!/usr/bin/python3
"""
Copyright (c) N. A. Inc.  2022
This program is free software per V3, or later version, of the GNU General Public License.
It is distributed AS-IS, WITHOUT ANY WARRANTY, or implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.

This class was written for a Telit LE910-NA1 Cat1 wireless modem, but with no,
or some changes, it may also work for other Telit modems (e.g. LE910C1-NF)
Many AT commands are "industry standard", but wireless modem manufacturers
(Quectel, Sierra, Simcom, etc.) also have their own AT language dialects.
"""

import serial                           # use serial for UART/USB communications
import time
from time import sleep
from datetime import datetime
import logging

class MyModem:

# Version 1.2
# A Python class to manage a wireless modem with its AT command
# language, using serial communications, via USB interface.

# TO DO: Ideally, should enforce a Singleton, since multiple instances
# for just one modem is illogical, but this works fine for now.

    # class constructor
    def __init__(self, cnf1, boot, comms, baud, timeout, retries, fastPath) :

        self.cnf1 = cnf1        # reference to Configuration object
        self.bootcon = None     # modem boot device connection
        self.commscon = None    # modem serial communications device connection
        self.boot = boot        # modem boot device connection
        self.comms = comms      # modem serial communications device connection
        self.baud = baud        # modem baud rate
        self.timeout = timeout  # modem connection timeout (seconds)
        self.retries = retries  # modem failed connection retry count
        self.bootwait = cnf1.getModemWaitSecsForBoot()  # seconds to wait for modem to finish rebooting

        logging.info('MDM-001I MyModem object created')
        reply = ''

        if fastPath :
            # Fast Path should just be used by the startup process to speed up an overall
            # system reboot, when it only needs to get date and time from the cellular network.
            for x in range(0, self.retries) :
                try :
                    self.commscon = serial.Serial(port=self.comms, baudrate=self.baud, timeout=self.timeout)
                    if self.commscon is None :
                        raise Exception('Not connected to modem')
                    else :
                        logging.debug('MDM-002I Modem connection is: %s', self.commscon)
                        break

                except Exception as ex :
                    logging.error('MDM-001E Modem issue ... will re-try: %s', str(ex))
                    if (self.commscon is not None) : self.commscon.__del__()
                    self.commscon = None
                    sleep(30)   # snooze and hope for better luck next time around
            # end of for loop

        else :
            # This is the normal initialization logic. Settings will be stored
            # as user-profile-2 in Non Volatile Memory on the wireless modem.
            for x in range(0, self.retries) :
                try :
                    self.commscon = serial.Serial(port=self.comms, baudrate=self.baud, timeout=self.timeout)
                    if self.commscon is None :
                        raise Exception('Not connected to modem')
                    else :
                        logging.debug('MDM-002I Modem connection is: %s', self.commscon)

                    self.commscon.write(b'ATE0\r')              # Echo off
                    sleep(0.5)
                    reply = self.commscon.readall()
                    str1 = str(reply, "UTF-8")
                    if (str1.endswith('OK\r\n')) :
                        logging.debug('MDM-003I Modem replied \"OK\" to: ATE0')
                    else :
                        raise Exception('No OK response from modem (#1)')

                    self.commscon.write(b'AT+CSCS=\"GSM\"\r')   # GSM character set
                    sleep(0.5)
                    reply = self.commscon.readall()
                    str1 = str(reply, "UTF-8")
                    if (str1.endswith('OK\r\n')) :
                        logging.debug('MDM-004I Modem replied \"OK\" to: AT+CSCS=GSM')
                    else :
                        raise Exception('No OK response from modem (#2)')

                    self.commscon.write(b'AT+CMGF=1\r')         # Text format for SMS
                    sleep(0.5)
                    reply = self.commscon.readall()
                    str1 = str(reply, "UTF-8")
                    if (str1.endswith('OK\r\n')) :
                        logging.debug('MDM-005I Modem replied \"OK\" to: AT+CMGF=1')
                    else :
                        raise Exception('No OK response from modem (#3)')

                    self.commscon.write(b'AT+CPMS=\"ME\",\"ME\",\"ME\"\r') # Save messages in NVM
                    sleep(0.5)
                    reply = self.commscon.readall()
                    str1 = str(reply, "UTF-8")
                    if (str1.endswith('OK\r\n')) :
                        logging.debug('MDM-006I Modem replied \"OK\" to: AT+CPMS="ME","ME","ME"')
                    else :
                        raise Exception('No OK response from modem (#4)')

                    self.commscon.write(b'AT&W1\r')     # Write settings to NVM
                    sleep(0.5)
                    reply = self.commscon.readall()
                    str1 = str(reply, "UTF-8")
                    if (str1.endswith('OK\r\n')) :
                        logging.debug('MDM-007I Modem replied \"OK\" to: AT&W1')
                    else :
                        raise Exception('No OK response from modem (#5)')

                    self.commscon.write(b'AT&P1\r')     # User profile at modem (re)boot
                    sleep(0.5)
                    reply = self.commscon.readall()
                    str1 = str(reply, "UTF-8")
                    if (str1.endswith('OK\r\n')) :
                        logging.debug('MDM-008I Modem replied \"OK\" to: AT&P1')
                    else :
                        raise Exception('No OK response from modem (#6)')

                    self.commscon.write(b'AT+CMGD=1,2\r')   # Delete old read and sent messages
                    sleep(0.5)
                    reply = self.commscon.readall()
                    str1 = str(reply, "UTF-8")
                    if (str1.endswith('OK\r\n')) :
                        logging.debug('MDM-009I Modem replied \"OK\" to: AT+CMGD=1,2')
                        break   # if this last AT command was successful, break out of the loop
                    else :
                        raise Exception('No OK response from modem (#7)')

                except Exception as ex :
                    logging.error('MDM-001E Modem issue ... will re-try: %s', str(ex))
                    if (self.commscon is not None) : self.commscon.__del__()
                    self.commscon = None
                    sleep(30)   # snooze and hope for better luck next time around
            # end of for loop


        self.RECENT_SECS = self.cnf1.getRecentSecondsSMS()

        # A recent history of sent SMS messages is maintained to reduce the
        # risk of sending duplicate messages in close temporal proximity and
        # thereby exhausting the SMS allocation or exceeding the SMS budget.
        # MAX_HISTORY value reflects the possible one or more alerts sent to
        # one or more cell phones e.g. 4 alerts to 4 phones = 16 combinations
        self.MAX_HISTORY = 16
        # key = nanosecond timestamp, value = phone number
        # key = same nanosecond timestamp, value = alert text
        self.SMS_history = {
            'alert' : {},
            'phone' : {}
            }


    # checkConnection
    def checkConnection(self) :
        return self.commscon


    # send an SMS message to recipient.
    def sendSMS(self, message, recipient) :
        if (self.isDuplicate(message, recipient)) :
            # it was a duplicate, but save history anyway due to future pruning
            self.saveHistory(message, recipient)
            return 8    # signal duplicate message condition
        else :          # it is NOT a recent, duplicate message
            if self.cnf1.doSendSMS() :      # if Config flag is True, send SMS
                try :
                    # assumes settings from user-profile-2 are in effect (&P1)
                    # for GSM character set and text format messaging.
                    self.commscon.write(b'AT+CMGS="' + recipient.encode() + b'"\r')
                    sleep(0.5)
                    msg = self.getDateTimeStr() + ' ' + message
                    self.commscon.write(msg.encode() + b"\r")
                    sleep(0.5)
                    cntrlZ = '\x1A'
                    self.commscon.write(cntrlZ.encode())    # add <Cntrl-Z> to send the SMS
                    sleep(0.5)
                    reply = self.commscon.readall()
                    str1 = reply.decode('utf-8')
                    if (str1.endswith('OK\r\n')) :
                        logging.debug('MDM-010I Modem replied \"OK\" to: AT+CMGS')
                        logging.info('MDM-011I Modem sent SMS: %s to %s', message, recipient)
                        self.saveHistory(message, recipient)
                        return 0
                    else :
                        raise Exception('No OK response from modem')
                except Exception as ex :
                    logging.error('MDM-002E Modem issue arose while sending SMS: %s', str(ex))
                    self.doReconnect()
                    return 16
            else :      # signal that SendSMS flag is False in configuration file
                return 4

    # send pay ATtention command to cellular modem
    def doStayAwake(self):
        try :
            self.commscon.write(b'AT\r')
            sleep(0.5)
            reply = self.commscon.readall()
            str1 = str(reply, "UTF-8")
            if (str1.endswith('OK\r\n')) :
                logging.debug('MDM-012I Modem replied \"OK\" to: \"AT\" \'stay awake\' command')
            else :
                raise Exception('No OK response from modem')

        except Exception as ex :
            logging.error('MDM-003E Modem did not respond to \"AT\" command: %s', str(ex))
            self.doReconnect()        
 

    # get currrent date and time from wireless network
    def getDateTime(self):
        try :
            self.commscon.write(b'AT+CCLK?\r')             # get date and time
            sleep(0.5)
            reply = self.commscon.readall()
            str1 = str(reply, "UTF-8")
            if (str1.endswith('OK\r\n')) :
                logging.info('MDM-013I Modem replied \"OK\" to: AT+CCLK?')
                return self.extractDateTime(str1)
            else :
                raise Exception('No OK response from modem')

        except Exception as ex :
            logging.error('MDM-004E Modem issue ... will not retry: %s', str(ex))
            return None


    # Try to reconnect.  Assumes the settings in user-profile-2 (&P1) are in effect.
    def doReconnect(self) :
        if self.commscon is not None :
            self.commscon.__del__()
            self.commscon = None
        else : pass

        logging.debug('MDM-014I Trying to reconnect modem for normal communications ...')
        for x in range(0, self.retries) :
            try :
                self.commscon = serial.Serial(port=self.comms, baudrate=self.baud, timeout=self.timeout)
                if self.commscon is not None :
                    logging.debug('MDM-015I Modem connection is now: %s', self.commscon)
                    break
                else :
                    raise Exception('not connected to modem')

            except Exception as ex :
                logging.debug('MDM-005E Could not connect to modem, but will re-try: %s', str(ex))
                if (self.commscon is not None) :
                    self.commscon.__del__()
                    self.commscon = None
                else : pass
                sleep(30)           #snooze and hope for better luck next time around
        # end of for loop

        if self.commscon is None :
            self.doReboot()
        else :
            logging.info('MDM-016I Modem connection is now: %s', self.commscon)



    # Sometimes, the device (for example, /dev/ttyACM3) being used for routine serial
    # communication "plays dead", but usually can be resurected by rebooting the modem.
    # So, we'll attempt to use a different serial communication device, for example,
    # /dev/ttyACM0 to soft-reboot the modem and trust it resolves the problem.
    def doReboot(self) :
        if (self.commscon is not None) : # check as not just doReconnect() can invoke this method
            self.commscon.__del__()
        else : pass

        try :
            # device passed should be the ModemRebootDevice from the config file
            # bootcon will use setting from factory profile stored within NVM on the modem (&Y0)
            self.bootcon = serial.Serial(port=self.boot, baudrate=self.baud, timeout=self.timeout)
            logging.debug('MDM-017I Modem reboot connection is: %s', self.bootcon)
            logging.debug('MDM-018I Will try one \'ping\' before attempting to reboot')
            self.bootcon.write(b'AT\r')
            sleep(0.5)
            reply = self.bootcon.readall()
            logging.debug('MDM-019I Modem replied: %s', reply)
            logging.info('MDM-001W About to REBOOT modem ...')
            self.bootcon.write(b'AT#REBOOT\r')
            sleep(1)
            # must now destroy the reboot serial object
            if (self.bootcon is not None) : self.bootcon.__del__()
            sleep(self.bootwait)        # give modem time to reboot and be ready

        except Exception as ex :
            logging.error('MDM-006E Failed to reboot modem with \'AT#REBOOT\' : %s', str(ex))



    # save brief history of SMS messages sent
    def saveHistory(self, message, recipient) :
        tstamp = time.time_ns()
        self.SMS_history['alert'][tstamp] = message
        self.SMS_history['phone'][tstamp] = recipient
        return


    # check to see if this message is a recent duplicate, to guard against
    # exhausting the monthly SMS allocation or exceeding the monthly SMS budget
    def isDuplicate(self, message, recipient) :
        isMatched = False
        keys = sorted(self.SMS_history['alert'].keys(), reverse=True) # most recent first
        for k in keys :
            if ( (self.SMS_history['alert'][k] == message) and (self.SMS_history['phone'][k] == recipient) ) :
                ts1 = time.time_ns()
                if ( abs( (ts1 - k) / 1000000000) ) <= self.RECENT_SECS :
                    isMatched = True
                    break

        return isMatched


    # get string containing current date and time from the O/S (not the modem)
    def getDateTimeStr(self) :
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        return dt_string


    # extract date and time from the modem's overall response
    # Telit LE910-NA1 generalized actual response examples:
    # without DST  'AT+CCLK?\r\r\n+CCLK: "yy/mm/dd,hh:mm:ss-nn"\r\n\r\nOK\r\n'
    # with DST     'AT+CCLK?\r\r\n+CCLK: "yy/mm/dd,hh:mm:ss+nn,d"\r\n\r\nOK\r\n'
    # (the "-nn" means local time is nn*15 minutes behind GMT; +nn means ahead of GMT)
    def extractDateTime(self, rawstr) :
        if (rawstr.count('"') == 2) :
            startpos = rawstr.find('"')
            nextstart = startpos + 1
            endpos = rawstr.find('"', nextstart)

            minuspos = rawstr.find('-', startpos, endpos)
            if (minuspos != -1) :
                newendpos = minuspos
            else :
                newendpos = rawstr.find('+', startpos, endpos)
                if newendpos != -1 :
                    pass
                else : return None

            str1 = rawstr[nextstart:newendpos]
            str1 = str1.replace('/', '')           # remove the slashes
            return str1.split(',')                 # i.e. 'yymmdd' 'hh:mm:ss'

        else : return None


    # get unread SMS message(s), for example:
    # \r\n+CMGL: 1,"REC UNREAD","9990001212","","yy/mm/dd,hh:mm:ss+nn"\r\nStatus?\r\nOK\r\n'
    def getUnreadSMS(self):
        str1 = ''
        try :
            self.commscon.write(b'AT+CMGL=\"REC UNREAD\"\r')
            sleep(0.5)
            reply = self.commscon.readall()
            str1 = str(reply, "UTF-8")
            if (str1.endswith('OK\r\n')) :
                logging.debug('MDM-020I Modem replied \"OK\" to: AT+CMGL="REC UNREAD"')
                logging.trace('MDM-021I Reply was: %s', reply)
                return (self.InboundSMS(str1))
            else :
                raise Exception('No OK response from modem')

        except Exception as ex :
            logging.error('MDM-007E Modem issue: %s', str(ex))
            self.doReconnect()
            return []


    # Massage response from an AT+CMGL command into a simplified list, for example:
    # [['1', '9990001212', 'Arm', 'partition', '1', 'away'], ['2', '9990001212', 'Status?']]
    # This method will be sensitive to any change to modem firmware which affects
    # the text format response to the AT+CMGL command and so is potentially fragile.
    def InboundSMS(self, reply) :
        if (reply == '\r\nOK\r\n') :
            logging.trace('no unread SMS messages -- reply was just: \"OK\" ')
            return ['OK']
        else :
            tmplst1 = []
            tmplst2 = []
            tmplst3 = []
            finalList = []

            reply = reply.replace('\r\nOK\r\n', '')
            reply = reply.replace('\r\n', '')
            tmplst1 = reply.split('+CMGL: ')
            tmplst1.pop(0)

            for x in  tmplst1 :
                tmpstr = x.replace('REC UNREAD', '')
                tmpstr = tmpstr.replace('""', '"None"')
                tmpstr = tmpstr.replace('"', ' ')
                tmpstr = tmpstr.replace(',', ' ', 4)    # retain date,time comma
                tmpstr = tmpstr.replace('  ', ' ')
                tmpstr = tmpstr.replace('  ', ' ')
                tmplst2.append(tmpstr)

            for y in tmplst2 :
                tmplst3 = y.split(' ')
                tmplst3.pop(1)
                tmplst3.pop(2)
                tmplst3.pop(2)
                finalList.append(tmplst3)

            return finalList


    # Method to prune one or more surplus historical alert message and
    # phone number, SMS events (having the same nanosecond timestamp key).
    def doPruning(self) :
        logging.trace('MDM-022I Sent SMS history before pruning: %s', self.SMS_history)

        keys = sorted(self.SMS_history['alert'].keys())
        popLim = 0
        length = len(keys)
        if length > self.MAX_HISTORY : popLim = (length - self.MAX_HISTORY)
        for x in range(0, popLim) :
            k = keys[x]
            self.SMS_history['alert'].pop(k)
            self.SMS_history['phone'].pop(k)
        # end of for loop

        logging.trace('MDM-023I Sent SMS history after pruning : %s', self.SMS_history)

        return


    # class finalizer ('destructor')
    def __del__(self) :
        del self.commscon


 # end of MyModem class
