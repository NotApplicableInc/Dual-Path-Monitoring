#!/usr/bin/python3
"""
Copyright (c) N. A. Inc.  2022
This program is free software per V3, or later version, of the GNU General Public License.
It is distributed AS-IS, WITHOUT ANY WARRANTY, or implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.
"""

import sys
import configparser     #standard Python parser for config files
import logging
from functools import partial, partialmethod
from datetime import datetime

class Configuration:

# Version 1.03
# A Python class to manage the config file for the DPM.py application
# The main configuration file (DPM.ini) contains read-only, string variables.
# The separate, small DPM-metrics.ini config file contains a [Metrics] section that
# records the number of SMS messages processed and the date of the latest SMS.

# TO DO: Ideally, should enforce a Singleton, since multiple instances
# potentially updating the [Metrics] section would be problematic.

    # class constructor
    def __init__(self, overridelog) :

        self.DPMparse = None
        self.MetricsParse = None
        self.validRedAlertPhones = []
        self.validYellowAlertPhones = []
        self.validRebootAlertPhones = []
        self.validInboundSMSPhones = []

        try :
            self.DPMparse = configparser.ConfigParser()
            cfg1file = ['DPM.ini']  # read-only configuration file
            result1 = self.DPMparse.read(cfg1file)
            if len(result1) != len(cfg1file): raise ValueError("Failed to open DPM configuration file", cfg1file[0])
        except ValueError as ex :
            print('CFG-001E FATAL ERROR:', str(ex))
            sys.exit(16)

        # Upon write, to retain comment lines within Sections, set "comment_prefixes"
        # option to a character NOT used to identify comments in the config file
        # (tilde used here) and allow empty values for the comment's 'keyword'.
        # Also preserved upper and lower case!
        try :
            self.MetricsParse = configparser.ConfigParser(comment_prefixes='~', allow_no_value=True)
            self.MetricsParse.optionxform=str       # preserve upper and lower case
            cfg2file = ['DPM-metrics.ini']          # read and written to configuration file
            result2 = self.MetricsParse.read(cfg2file)
            if len(result2) != len(cfg2file): raise ValueError("Failed to open Metrics configuration file", cfg2file[0])
        except ValueError as ex :
            print('CFG-002E FATAL ERROR:', str(ex))
            sys.exit(16)


        # Add a custom, most verbose, TRACE level to the logger
        logging.TRACE = 5
        logging.addLevelName(logging.TRACE, 'TRACE')
        logging.Logger.trace = partialmethod(logging.Logger.log, logging.TRACE)
        logging.trace = partial(logging.log, logging.TRACE)

        loglevel = self.DPMparse.get('Logging', 'LogLevel')
        validlevels = 'TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL'
        if loglevel.upper() in validlevels :
            pass
        else :
            print('CFG-001W Invalid or missing Logging Level in configuration file -- will use DEBUG')
            loglevel = 'DEBUG'

        loglevelnum = getattr(logging, loglevel.upper())

        if overridelog is None :
            logfile = self.DPMparse.get('Logging', 'LogFile')
            logfile = logfile.replace('%s', self.getLogFileDateTimeStr())
        else : logfile = overridelog


        logging.basicConfig(filename=logfile, level=loglevelnum,format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        logging.info('CFG-001I Configuration object created (logging level: %s)', loglevel)

        self.validRedAlertPhones = self.checkRedAlertCellPhones()
        self.validYellowAlertPhones = self.checkYellowAlertCellPhones()
        self.validRebootAlertPhones = self.checkRebootAlertCellPhones()
        self.validInboundSMSPhones = self.checkInboundSMSCellPhones()


    def checkRedAlertCellPhones(self) :
        if self.DPMparse.has_option('CellPhones', 'RedAlertCellPhones') :
            phones = self.DPMparse.get('CellPhones', 'RedAlertCellPhones')
            if ( (phones != '') and (phones is not None) ) :
                validphones = []
                phList = phones.split(",")
                for ph in phList :
                    tmp = ph
                    ph = ph.replace(' ','')     # remove any spaces
                    ph = ph.replace('-','')     # remove any dashes
                    ph = ph.replace('+','')     # for international numbers
                    if( ph.isnumeric() ) :
                        if '+' in tmp :
                            ph = '+' + ph       # must have + for international
                        else : pass
                        validphones.append(ph)
                    else :
                        logging.info('CFG-002W Invalid phone number: %s', tmp)
                return (validphones)
            else : return []
        else : return []


    def checkYellowAlertCellPhones(self) :
        if self.DPMparse.has_option('CellPhones', 'YellowAlertCellPhones') :
            phones = self.DPMparse.get('CellPhones', 'YellowAlertCellPhones')
            if ( (phones != '') and (phones is not None) ) :
                validphones = []
                phList = phones.split(",")
                for ph in phList :
                    tmp = ph
                    ph = ph.replace(' ','')     # remove any spaces
                    ph = ph.replace('-','')     # remove any dashes
                    ph = ph.replace('+','')     # for international numbers
                    if( ph.isnumeric() ) :
                        if '+' in tmp :
                            ph = '+' + ph       # must have + for international
                        else : pass
                        validphones.append(ph)
                    else :
                        logging.info('CFG-003W Invalid phone number: %s', tmp)
                return (validphones)
            else : return []
        else : return []


    def checkRebootAlertCellPhones(self) :
        if self.DPMparse.has_option('CellPhones', 'RebootAlertCellPhones') :
            phones = self.DPMparse.get('CellPhones', 'RebootAlertCellPhones')
            if ( (phones != '') and (phones is not None) ) :
                validphones = []
                phList = phones.split(",")
                for ph in phList :
                    tmp = ph
                    ph = ph.replace(' ','')     # remove any spaces
                    ph = ph.replace('-','')     # remove any dashes
                    ph = ph.replace('+','')     # for international numbers
                    if( ph.isnumeric() ) :
                        if '+' in tmp :
                            ph = '+' + ph       # must have + for international
                        else : pass
                        validphones.append(ph)
                    else :
                        logging.info('CFG-004W Invalid phone number: %s', tmp)
                return (validphones)
            else : return []
        else : return []


    def checkInboundSMSCellPhones(self) :
        if self.DPMparse.has_option('CellPhones', 'InboundSMSCellPhones') :
            phones = self.DPMparse.get('CellPhones', 'InboundSMSCellPhones')
            if ( (phones != '') and (phones is not None) ) :
                validphones = []
                phList = phones.split(",")
                for ph in phList :
                    tmp = ph
                    ph = ph.replace(' ','')     # remove any spaces
                    ph = ph.replace('-','')     # remove any dashes
                    ph = ph.replace('+','')     # for international numbers
                    if( ph.isnumeric() ) :
                        if '+' in tmp :
                            ph = '+' + ph       # must have + for international
                        else : pass
                        validphones.append(ph)
                    else :
                        logging.info('CFG-005W Invalid phone number: %s', tmp)
                return (validphones)
            else : return []
        else : return []


    def checkInboundPhoneSMS(self, inphone) :
        validphone = None
        for x in self.validInboundSMSPhones :
            if inphone in x :
                validphone = x
                break
        # end of for loop

        return validphone


    def getRenewalDay(self) :
        if self.DPMparse.has_option('WirelessProvider', 'RenewalDay') :
            return self.DPMparse.get('WirelessProvider', 'RenewalDay')
        else : return '15'


    def getSMS_Allowance(self) :
        if self.DPMparse.has_option('WirelessProvider', 'SMS-Allowance') :
            return  int(self.DPMparse.get('WirelessProvider', 'SMS-Allowance'))
        else : return 0


    def getModemCommsDevice(self) :
        if self.DPMparse.has_option('Modem', 'ModemCommsDevice') :
            return self.DPMparse.get('Modem', 'ModemCommsDevice')
        else : return 'what\'s the modem communication device?'


    def getModemRebootDevice(self) :
        if self.DPMparse.has_option('Modem', 'ModemRebootDevice') :
            return self.DPMparse.get('Modem', 'ModemRebootDevice')
        else : return 'what\'s the modem reboot device?'

    def getModemBaud(self) :
        if self.DPMparse.has_option('Modem', 'ModemBaud') :
            return int(self.DPMparse.get('Modem', 'ModemBaud'))
        else : return 9600


    def getModemTimeOut(self) :
        if self.DPMparse.has_option('Modem', 'ModemTimeOutSecs') :
            return float(self.DPMparse.get('Modem', 'ModemTimeOutSecs'))
        else : return 10.0


    def getModemRetries(self) :
        if self.DPMparse.has_option('Modem', 'ModemConnectRetries') :
            return int(self.DPMparse.get('Modem', 'ModemConnectRetries'))
        else : return 20


    def getModemCheckIn(self) :
        if self.DPMparse.has_option('Modem', 'ModemCheckInSecs') :
            return int(self.DPMparse.get('Modem', 'ModemCheckInSecs'))
        else : return 61     # deliberately a prime number


    def doModemInboundSMS(self) :
        if self.DPMparse.has_option('Modem', 'ModemInboundSMS') :
            flag = eval(self.DPMparse.get('Modem', 'ModemInboundSMS'))
        if ( (flag is True ) or (flag is False) ) :
            return flag
        else : return False


    def doModemSoftReboot(self) :
        if self.DPMparse.has_option('Modem', 'ModemSoftReboot') :
            flag = eval(self.DPMparse.get('Modem', 'ModemSoftReboot'))
        if ( (flag is True ) or (flag is False) ) :
            return flag
        else : return True


    def getRedAlertCellPhones(self) :
        return self.validRedAlertPhones


    def getYellowAlertCellPhones(self) :
        return self.validYellowAlertPhones


    def getRebootAlertCellPhones(self) :
        return self.validRebootAlertPhones


    def getInboundSMSCellPhones(self) :
        return self.validInboundSMSPhones


    def getRedAlertCellPhoneCount(self) :
        return len(self.validRedAlertPhones)


    def getYellowAlertCellPhoneCount(self) :
        return len(self.validYellowAlertPhones)


    def getRebootAlertCellPhoneCount(self) :
        return len(self.validRebootAlertPhones)


    def getInboundSMSCellPhoneCount(self) :
        return len(self.validInboundSMSPhones)


    def getZones(self) :
        if self.DPMparse.has_option('SecuritySystem', 'Zones') :
            return eval(self.DPMparse.get('SecuritySystem', 'Zones'))
        else: return None


    def getUsers(self) :
        if self.DPMparse.has_option('SecuritySystem', 'Users') :
            return eval(self.DPMparse.get('SecuritySystem', 'Users'))
        else: return None


    def getIgnoreTokens(self) :
        if self.DPMparse.has_option('SecuritySystem', 'IgnoreTokens') :
            return eval(self.DPMparse.get('SecuritySystem', 'IgnoreTokens'))
        else: return []


    def getNotTheseTokens(self) :
        if self.DPMparse.has_option('SecuritySystem', 'NotTheseTokens') :
            return eval(self.DPMparse.get('SecuritySystem', 'NotTheseTokens'))
        else: return []


    def getUrgentTokens(self) :
        if self.DPMparse.has_option('SecuritySystem', 'UrgentTokens') :
            return eval(self.DPMparse.get('SecuritySystem', 'UrgentTokens'))
        else: return []


    def getImportantTokens(self) :
        if self.DPMparse.has_option('SecuritySystem', 'ImportantTokens') :
            return eval(self.DPMparse.get('SecuritySystem', 'ImportantTokens'))
        else: return []


    def doScanSyslog(self) :
        if self.DPMparse.has_option('EVL4-Syslog', 'ScanSyslog') :
            flag = eval(self.DPMparse.get('EVL4-Syslog', 'ScanSyslog'))
        if ( (flag is True ) or (flag is False) ) :
            return flag
        else : return False


    def getRecentSecondsEVL4(self) :
        if self.DPMparse.has_option('Timings', 'RecentSecondsEVL4') :
            return int(self.DPMparse.get('Timings', 'RecentSecondsEVL4'))
        else : return 120


    def getAdjacentSecondsEVL4(self) :
        if self.DPMparse.has_option('Timings', 'AdjacentSecondsEVL4') :
            return int(self.DPMparse.get('Timings', 'AdjacentSecondsEVL4'))
        else : return 90


    def getRecentSecondsSMS(self) :
        if self.DPMparse.has_option('Timings', 'RecentSecondsSMS') :
            return int(self.DPMparse.get('Timings', 'RecentSecondsSMS'))
        else : return 60


    def getEVL4Log(self) :
        if self.DPMparse.has_option('EVL4-Syslog', 'Log') :
            return self.DPMparse.get('EVL4-Syslog', 'Log')
        else : return 'EVL4.log'


    def getEVL4Offset(self) :
        if self.DPMparse.has_option('EVL4-Syslog', 'Offset') :
            return self.DPMparse.get('EVL4-Syslog', 'Offset')
        else : return 'EVL4.offset'


    def getTelEVL4RebootURL(self) :
        # vulnerable to EVL4 firmware changes
        if self.DPMparse.has_option('TelEVL4', 'TelEVL4RebootURL') :
            return self.DPMparse.get('TelEVL4', 'TelEVL4RebootURL')
        else : return 'http://192.168.1.2/3?A=2'


    def doTelEVL4SoftReboot(self) :
        if self.DPMparse.has_option('TelEVL4', 'TelEVL4SoftReboot') :
            flag = eval(self.DPMparse.get('TelEVL4', 'TelEVL4SoftReboot'))
        if ( (flag is True ) or (flag is False) ) :
            return flag
        else : return True


    def getTelEVL4Host(self) :
        if self.DPMparse.has_option('TelEVL4', 'TelEVL4Host') :
            return self.DPMparse.get('TelEVL4', 'TelEVL4Host')
        else : return '192.168.1.1'


    def getTelEVL4Port(self) :
        if self.DPMparse.has_option('TelEVL4', 'TelEVL4Port') :
            return self.DPMparse.get('TelEVL4', 'TelEVL4Port')
        else : return '4025'


    def getTelEVL4Password(self) :
        if self.DPMparse.has_option('TelEVL4', 'TelEVL4Password') :
            return self.DPMparse.get('TelEVL4', 'TelEVL4Password')
        else : return 'PASSWORD?'


    def getTelEVL4TimeOut(self) :
        if self.DPMparse.has_option('TelEVL4', 'TelEVL4TimeOutSecs') :
            return float(self.DPMparse.get('TelEVL4', 'TelEVL4TimeOutSecs'))
        else : return 10.0


    def getTelEVL4Retries(self) :
        if self.DPMparse.has_option('TelEVL4', 'TelEVL4ConnectRetries') :
            return int(self.DPMparse.get('TelEVL4', 'TelEVL4ConnectRetries'))
        else : return 20


    def getTelEVL4Polling(self) :
        if self.DPMparse.has_option('TelEVL4', 'TelEVL4PollingMins') :
            return int(self.DPMparse.get('TelEVL4', 'TelEVL4PollingMins'))
        else : return 17    # deliberately a prime number less than 20


    def getTelEVL4StayAwake(self) :
        if self.DPMparse.has_option('TelEVL4', 'TelEVL4StayAwakeSecs') :
            return int(self.DPMparse.get('TelEVL4', 'TelEVL4StayAwakeSecs'))
        else : return 179   # deliberately a prime number


    def getPingCommand(self) :
        if self.DPMparse.has_option('Ping', 'PingCommand') :
            return eval(self.DPMparse.get('Ping', 'PingCommand'))
        else : return 'ping ... pong'


    def getPingers(self) :
        if self.DPMparse.has_option('Ping', 'Pingers') :
            pingers = self.DPMparse.get('Ping', 'Pingers')
            return pingers
        else : return None


    def doSendSMS(self) :
        if self.DPMparse.has_option('SMS', 'SendSMS') :
            flag = eval(self.DPMparse.get('SMS', 'SendSMS'))
        if ( (flag is True ) or (flag is False) ) :
            return flag
        else : return False


    def getSMSsize(self) :
        if self.DPMparse.has_option('SMS', 'SMSsize') :
            return int(self.DPMparse.get('SMS', 'SMSsize'))
        else : return 160   # for 7-bit GSM code page


    def getLogLevel(self) :
        if self.DPMparse.has_option('Logging', 'LogLevel') :
            return self.DPMparse.get('Logging', 'LogLevel')
        else : return 'DEBUG'


    def getLogFileDateTimeStr(self) :
        now = datetime.now()
        dt_string = now.strftime("%Y%m%d%H%M%S")
        return dt_string


    def getCountSMS(self) :
        if self.MetricsParse.has_option('SMS-Metrics', 'SMS-Count') :
            return int(self.MetricsParse.get('SMS-Metrics', 'SMS-Count'))
        else : return 1000000


    def getSMSLatestDate(self) :
        if self.MetricsParse.has_option('SMS-Metrics', 'SMS-LatestDate') :
            return self.MetricsParse.get('SMS-Metrics', 'SMS-LatestDate')
        else : return self.getDateTimeStr()


    def updateSMSmetrics(self, sent, sentdate) :
        # "SMS-Count" includes both Outbound and Inbound SMS messages.
        # "SMS-LatestDate" includes the date an Inbound SMS was processed.
        if ( (self.MetricsParse.has_section('SMS-Metrics'))
         and (self.MetricsParse.has_option('SMS-Metrics', 'SMS-Count'))
          and (self.MetricsParse.has_option('SMS-Metrics', 'SMS-LatestDate')) ) :
            oldcnt = int(self.MetricsParse.get('SMS-Metrics', 'SMS-Count'))
            newcnt = oldcnt + sent
            newcntstr  = str(newcnt)
            self.MetricsParse.set('SMS-Metrics', 'SMS-Count', newcntstr)
            self.MetricsParse.set('SMS-Metrics', 'SMS-LatestDate', sentdate)
            try :
                fp=open('DPM-metrics.ini','w')
                self.MetricsParse.write(fp)
                fp.close()
            except (configparser.Error, IOError, OSError) as ex :
                logging.exception('CFG-003E Error while attempting to update DPM-metrics config file: %s', ex)
        else : logging.error('CFG-004E DPM-metrics Configuration file has no, or an invalid SMS-Metrics section!')


    def resetSMSmetrics(self) :
        if ( (self.MetricsParse.has_section('SMS-Metrics'))
         and (self.MetricsParse.has_option('SMS-Metrics', 'SMS-Count'))
          and (self.MetricsParse.has_option('SMS-Metrics', 'SMS-LatestDate')) ) :
            self.MetricsParse.set('SMS-Metrics', 'SMS-Count', '0')
            self.MetricsParse.set('SMS-Metrics', 'SMS-LatestDate', 'UNKNOWN')
            try :
                fp=open('DPM-metrics.ini','w')
                self.MetricsParse.write(fp)
                fp.close()
            except (configparser.Error, IOError, OSError) as ex :
                logging.exception('CFG-005E Error while attempting to update DPM-metrics config file: %s', ex)
        else : logging.error('CFG-006E DPM-metrics Configuration file has no, or an invalid SMS-Metrics section!')


    def getDateTimeStr(self) :
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        return dt_string


    def doRasPiReboot(self) :
        if self.DPMparse.has_option('RasPi', 'RasPiReboot') :
            flag = eval(self.DPMparse.get('RasPi', 'RasPiReboot'))
        if ( (flag is True ) or (flag is False) ) :
            return flag
        else : return True


    def getRasPiRebootRetries(self) :
        if self.DPMparse.has_option('RasPi', 'RasPiRebootRetries') :
            return int(self.DPMparse.get('RasPi', 'RasPiRebootRetries'))
        else : return 2


    def getCountRasPiReboots(self) :
        if self.MetricsParse.has_option('RaspberryPi', 'RasPiReboots') :
            return int(self.MetricsParse.get('RaspberryPi', 'RasPiReboots'))
        else : return 1000000


    def updateRasPiReboots(self) :
        if ( (self.MetricsParse.has_section('RaspberryPi'))
         and (self.MetricsParse.has_option('RaspberryPi', 'RasPiReboots')) ) :
            newcnt = 1 + int(self.MetricsParse.get('RaspberryPi', 'RasPiReboots'))
            newcntstr  = str(newcnt)
            self.MetricsParse.set('RaspberryPi', 'RasPiReboots', newcntstr)
            try :
                fp=open('DPM-metrics.ini','w')
                self.MetricsParse.write(fp)
                fp.close()
            except (configparser.Error, IOError, OSError) as ex :
                logging.exception('CFG-007E Error while attempting to update DPM-metrics config file: %s', ex)
        else : logging.error('CFG-008E DPM-metrics Configuration file has no, or an invalid RaspberryPi section!')


    def resetRasPiReboots(self) :
        if ( (self.MetricsParse.has_section('RaspberryPi'))
         and (self.MetricsParse.has_option('RaspberryPi', 'RasPiReboots')) ) :
            self.MetricsParse.set('RaspberryPi', 'RasPiReboots', '0')
            try :
                fp=open('DPM-metrics.ini','w')
                self.MetricsParse.write(fp)
                fp.close()
            except (configparser.Error, IOError, OSError) as ex :
                logging.exception('CFG-009E Error while attempting to update DPM-metrics config file: %s', ex)
        else : logging.error('CFG-010E DPM-metrics Configuration file has no, or an invalid RaspberryPi section!')



 # end of Configuration class
