#!/usr/bin/python3
"""
Copyright (c) N. A. Inc.  2022
This program is free software per V3, or later version, of the GNU General Public License.
It is distributed AS-IS, WITHOUT ANY WARRANTY, or implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.
"""

from datetime import datetime
import logging

class DecodeCID:

    # Version 1.01
    # A Python class to decode Ademco-Honeywell-Resideo Vista security system CID (Contact ID)
    # event codes, furnished by an Eyezon Envisalink EVL4 module, via it's IP socket "TPI"
    # interface, or via it's syslog client feature (EVL4 firmware 1.1.108 or later).
    #
    # Example syslog entry:   Date Time LAN IP Address ENVISALINK[MAC Address]: CID Event: 1373020010
    #       CID Sub-field structure:  1-373-02-001-0
    # 1 = Event Qualifier,  373 = Event Code,  02 = Partition ID,  001 = User ID/Zone Number,  0 = check digit (unused)
    # Example in English: "Protection Loop: New - 373 Fire trouble, Partition: 02, Zone: Ground Floor Smoke Detectors"

    # read-only Class variables follow -- mainly python dictionaries.

    # Default zone descriptions dictionary
    # Invoke the setZones method, post instantiation to customize for your own security system configuration.
    zones = {'001': 'zone-1', '002': 'zone-2', '003': 'zone-3', '004': 'zone-4', '005': 'zone-5', '006': 'zone-6', '007': 'zone-7', '008': 'zone-8',
                '009': 'zone-9', '010': 'zone-10', '011': 'zone-11', '012': 'zone-12', '013': 'zone-13', '014': 'zone-14', '015': 'zone-15', '016': 'zone-16' }

    # Default user descriptions dictionary
    # Invoke the setUsers method, post instantiation to customize for your own security system configuration.
    users = {'001': 'Installer', '002': 'Master', '003': 'user-3', '004': 'user-4', '005': 'user-5', '006': 'user-6',
                '007': 'user-7', '008': 'user-8', '009': 'user-9', '010': 'user-10', '011': 'user-11', '012': 'user-12' }

    #Event Categories dictionary
    CID_EventCategory = {
    'A': 'Medical Alarms',
    'B': 'Fire Alarms',
    'C': 'Panic Alarms',
    'D': 'Burglar Alarms',
    'E': 'General Alarm',
    'F': '24 Hour Non-Burglary',
    'G': 'Fire Supervisory',
    'H': 'System Troubles',
    'I': 'Sounder/Relay Trouble',
    'J': 'System Peripheral Trouble',
    'K': 'Communication Troubles',
    'L': 'Protection Loop',
    'M': 'Sensor Trouble',
    'N': 'Open/Close',
    'O': 'Remote Access',
    'P': 'Access Control',
    'Q': 'System Disables',
    'R': 'Sounder/Relay Disables',
    'S': 'System Peripheral Disables',
    'T': 'Communication Disables',
    'U': 'Bypasses',
    'V': 'Test/Miscellaneous',
    'W': 'Event Log',
    'X': 'Scheduling',
    'Y': 'Personnel Monitoring',
    'Z': 'Miscellaneous',
    '*': 'Customized'
    }

    # Event Qualifiers -- a dictionary of dictionaries to provide contextualy sensitive descriptions of events
    # and hopefully, more intuitive messages.  See examples in Appendix A of the Security Industry Association
    # document SIA DC-05-1999.09 (can be found on the Internet using Google) for a couple of examples.
    # First digit of the overall CID is the Event Qualifier code with valid values of '1', '3', and '6'.
    # This class has no "setter" method to override these values -- code changes will be required here and to the
    # corresponding Event Qualifier selector value of one or more CID-EventCodes tuples below.
    CID_EventQualifiers = { 'a': {'1': 'New event', '3': 'Restore event', '6': 'Duplicate message'},
                            'b': {'1': 'Open event', '3': 'Close event', '6': 'Duplicate message'},
                            'c': {'1': 'Start event', '3': 'End event', '6': 'Duplicate message'},
                            'd': {'1': 'Activation event', '3': 'Deactivation event', '6': 'Duplicate message'} }

    # EventCodes -- a dictionary of event tuples.
    # Key is Event Code, value is: Category Code, Description, Type (Z = zone, U = user, X = ID or unknown),
    #  and an Event Qualifier description selector (lowercase alphabetic)
    # Update the information for any User Assigned values (750 thru' 789) to match your own configuration.
    CID_EventCodes = {
    '100': ('A', 'Medical Emergency', 'Z', 'a'),
    '101': ('A', 'Pendant Transmitter', 'Z', 'a'),
    '102': ('A', 'Failed to report in', 'Z', 'a'),
    '110': ('B', 'Fire', 'Z', 'a'),
    '111': ('B', 'Smoke', 'Z', 'a'),
    '112': ('B', 'Combustion', 'Z', 'a'),
    '113': ('B', 'Water flow', 'Z', 'a'),
    '114': ('B', 'Heat', 'Z', 'a'),
    '115': ('B', 'Pull Station', 'Z', 'a'),
    '116': ('B', 'Duct', 'Z', 'a'),
    '117': ('B', 'Flame', 'Z', 'a'),
    '118': ('B', 'Near Alarm', 'Z', 'a'),
    '120': ('C', 'Panic', 'Z', 'a'),
    '121': ('C', 'Duress', 'U', 'a'),
    '122': ('C', 'Silent', 'Z', 'a'),
    '123': ('C', 'Audible', 'Z', 'a'),
    '124': ('C', 'Duress-Access granted', 'Z', 'a'),
    '125': ('C', 'Duress-Egress granted', 'Z', 'a'),
    '126': ('C', 'Hold-up suspicion print', 'U', 'a'),
    '130': ('D', 'Burglary', 'Z', 'a'),
    '131': ('D', 'Perimeter', 'Z', 'a'),
    '132': ('D', 'Interior', 'Z', 'a'),
    '133': ('D', '24 Hour burglary', 'Z', 'a'),
    '134': ('D', 'Entry/Exit', 'Z', 'a'),
    '135': ('D', 'Day/Night', 'Z', 'a'),
    '136': ('D', 'Outdoor', 'Z', 'a'),
    '137': ('D', 'Tamper', 'Z', 'a'),
    '138': ('D', 'Near alarm', 'Z', 'a'),
    '139': ('D', 'Intrusion Verifier', 'Z', 'a'),
    '140': ('E', 'General Alarm', 'Z', 'a'),
    '141': ('E', 'Polling loop open', 'Z', 'a'),
    '142': ('E', 'Polling loop short', 'Z', 'a'),
    '143': ('E', 'Expansion module failure', 'Z', 'a'),
    '144': ('E', 'Sensor tamper', 'Z', 'a'),
    '145': ('E', 'Expansion module tamper', 'Z', 'a'),
    '146': ('E', 'Silent Burglary', 'Z', 'a'),
    '147': ('E', 'Sensor Supervision Failure', 'Z', 'a'),
    '150': ('F', '24 Hour Non-Burglary', 'Z', 'a'),
    '151': ('F', 'Gas detected', 'Z', 'a'),
    '152': ('F', 'Refrigeration', 'Z', 'a'),
    '153': ('F', 'Loss of heat', 'Z', 'a'),
    '154': ('F', 'Water Leakage', 'Z', 'a'),
    '155': ('F', 'Foil Break', 'Z', 'a'),
    '156': ('F', 'Day Trouble', 'Z', 'a'),
    '157': ('F', 'Low bottled gas level', 'Z', 'a'),
    '158': ('F', 'High temp', 'Z', 'a'),
    '159': ('F', 'Low temp', 'Z', 'a'),
    '161': ('F', 'Loss of air flow', 'Z', 'a'),
    '162': ('F', 'Carbon Monoxide detected', 'Z', 'a'),
    '163': ('F', 'Tank level', 'Z', 'a'),
    '168': ('F', 'High Humidity', 'Z', 'a'),
    '169': ('F', 'Low Humidity', 'Z', 'a'),
    '200': ('G', 'Fire Supervisory', 'Z', 'a'),
    '201': ('G', 'Low water pressure', 'Z', 'a'),
    '202': ('G', 'Low CO2', 'Z', 'a'),
    '203': ('G', 'Gate valve sensor', 'Z', 'a'),
    '204': ('G', 'Low water level', 'Z', 'a'),
    '205': ('G', 'Pump activated', 'Z', 'a'),
    '206': ('G', 'Pump failure', 'Z', 'a'),
    '300': ('H', 'System Trouble', 'Z', 'a'),
    '301': ('H', 'AC Loss', 'Z', 'a'),
    '302': ('H', 'Low system battery', 'Z', 'a'),
    '303': ('H', 'RAM Checksum bad', 'Z', 'a'),
    '304': ('H', 'ROM checksum bad', 'Z', 'a'),
    '305': ('H', 'System reset', 'Z', 'a'),
    '306': ('H', 'Panel programming changed', 'Z', 'a'),
    '307': ('H', 'Self-test failure', 'Z', 'a'),
    '308': ('H', 'System shutdown', 'Z', 'a'),
    '309': ('H', 'Battery test failure', 'Z', 'a'),
    '310': ('H', 'Ground fault', 'Z', 'a'),
    '311': ('H', 'Battery Missing/Dead', 'Z', 'a'),
    '312': ('H', 'Power Supply Overcurrent', 'Z', 'a'),
    '313': ('H', 'Engineer Reset', 'U', 'a'),
    '314': ('H', 'Primary Power Supply Failure', 'Z', 'a'),
    '316': ('H', 'System Tamper', 'X', 'a'),
    '320': ('I', 'Sounder/Relay', 'Z', 'a'),
    '321': ('I', 'Bell 1', 'Z', 'a'),
    '322': ('I', 'Bell 2', 'Z', 'a'),
    '323': ('I', 'Alarm relay', 'Z', 'a'),
    '324': ('I', 'Trouble relay', 'Z', 'a'),
    '325': ('I', 'Reversing relay', 'Z', 'a'),
    '326': ('I', 'Notification Appliance Ckt. #3', 'Z', 'a'),
    '327': ('I', 'Notification Appliance Ckt. #4', 'Z', 'a'),
    '330': ('J', 'System Peripheral trouble', 'Z', 'a'),
    '331': ('J', 'Polling loop open', 'Z', 'a'),
    '332': ('J', 'Polling loop short', 'Z', 'a'),
    '333': ('J', 'Expansion module failure', 'Z', 'a'),
    '334': ('J', 'Repeater failure', 'Z', 'a'),
    '335': ('J', 'Local printer out of paper', 'Z', 'a'),
    '336': ('J', 'Local printer failure', 'Z', 'a'),
    '337': ('J', 'Exp. Module DC Loss', 'Z', 'a'),
    '338': ('J', 'Exp. Module Low Battery', 'Z', 'a'),
    '339': ('J', 'Exp. Module Reset', 'Z', 'a'),
    '341': ('J', 'Exp. Module Tamper', 'Z', 'a'),
    '342': ('J', 'Exp. Module AC Loss', 'Z', 'a'),
    '343': ('J', 'Exp. Module self-test fail', 'Z', 'a'),
    '344': ('J', 'RF Receiver Jam Detect', 'Z', 'a'),
    '345': ('J', 'AES Encryption disabled/enabled', 'Z', 'a'),
    '350': ('K', 'Communication trouble', 'Z', 'a'),
    '351': ('K', 'Telco 1 fault', 'Z', 'a'),
    '352': ('K', 'Telco 2 fault', 'Z', 'a'),
    '353': ('K', 'Long Range Radio xmitter fault', 'Z', 'a'),
    '354': ('K', 'Failure to communicate event', 'Z', 'a'),
    '355': ('K', 'Loss of Radio supervision', 'Z', 'a'),
    '356': ('K', 'Loss of central polling', 'Z', 'a'),
    '357': ('K', 'Long Range Radio Transmitter VSWR', 'Z', 'a'),
    '370': ('L', 'Protection loop', 'Z', 'a'),
    '371': ('L', 'Protection loop open', 'Z', 'a'),
    '372': ('L', 'Protection loop short', 'Z', 'a'),
    '373': ('L', 'Fire trouble', 'Z', 'a'),
    '374': ('L', 'Exit error by User', 'Z', 'a'),
    '375': ('L', 'Panic zone trouble', 'Z', 'a'),
    '376': ('L', 'Hold-up zone trouble', 'Z', 'a'),
    '377': ('L', 'Swinger Trouble', 'Z', 'a'),
    '378': ('L', 'Cross-zone Trouble', 'Z', 'a'),
    '380': ('M', 'Sensor trouble global', 'Z', 'a'),
    '381': ('M', 'Loss of supervision - RF', 'Z', 'a'),     # Radio Frequency (RF transmitter)
    '382': ('M', 'Loss of supervision - RPM', 'Z', 'a'),    # Remote Point Module (zone expander)
    '383': ('M', 'Sensor tamper', 'Z', 'a'),
    '384': ('M', 'RF low battery', 'Z', 'a'),
    '385': ('M', 'Smoke detector Hi sensitivity', 'Z', 'a'),
    '386': ('M', 'Smoke detector Low sensitivity', 'Z', 'a'),
    '387': ('M', 'Intrusion detector Hi sensitivity', 'Z', 'a'),
    '388': ('M', 'Intrusion detector Low sensitivity', 'Z', 'a'),
    '389': ('M', 'Sensor self-test failure', 'Z', 'a'),
    '391': ('M', 'Sensor Watch failure', 'Z', 'a'),
    '392': ('M', 'Drift Compensation Error', 'Z', 'a'),
    '393': ('M', 'Maintenance Alert', 'Z', 'a'),
    '400': ('N', 'Open/Close', 'U', 'b'),
    '401': ('N', 'Open/Close by User', 'U', 'b'),
    '402': ('N', 'Group Open/Close', 'U', 'b'),
    '403': ('N', 'Automatic Open/Close', 'U', 'b'),
    '404': ('N', 'Late to O/C (Note: use 453, 454 instead)', 'U', 'b'),
    '405': ('N', 'Deferred O/C (Obsolete - do not use)', 'U', 'b'),
    '406': ('N', 'Cancel (by User)', 'U', 'b'),
    '407': ('N', 'Remote arm/disarm', 'U', 'b'),
    '408': ('N', 'Quick arm', 'U', 'b'),
    '409': ('N', 'Keyswitch Open/Close', 'U', 'b'),
    '411': ('O', 'Callback requested', 'U', 'a'),
    '412': ('O', 'Successful download access', 'U', 'a'),
    '413': ('O', 'Unsuccessful access', 'U', 'a'),
    '414': ('O', 'System shutdown command received', 'U', 'a'),
    '415': ('O', 'Dialer shutdown command received', 'U', 'a'),
    '416': ('O', 'Successful Upload', 'Z', 'a'),
    '421': ('P', 'Access denied', 'U', 'a'),
    '422': ('P', 'Access report by User', 'U', 'a'),
    '423': ('P', 'Forced Access', 'Z', 'a'),
    '424': ('P', 'Egress Denied', 'U', 'a'),
    '425': ('P', 'Egress Granted', 'U', 'a'),
    '426': ('P', 'Access Door propped open', 'Z', 'a'),
    '427': ('P', 'Access point Door Status Monitor trouble', 'Z', 'a'),
    '428': ('P', 'Access point Request To Exit trouble', 'Z', 'a'),
    '429': ('P', 'Access program mode entry', 'U', 'a'),
    '430': ('P', 'Access program mode exit', 'U', 'a'),
    '431': ('P', 'Access threat level change', 'U', 'a'),
    '432': ('P', 'Access relay/trigger fail', 'Z', 'a'),
    '433': ('P', 'Access Request to Exit shunt', 'Z', 'a'),
    '434': ('P', 'Access Door Status Monitor shunt', 'Z', 'a'),
    '435': ('P', 'Second Person Access', 'U', 'a'),
    '436': ('P', 'Irregular Access', 'U', 'a'),
    '441': ('N', 'Armed Stay', 'U', 'b'),
    '442': ('N', 'Keyswitch Armed Stay', 'U', 'b'),
    '450': ('N', 'Exception Open/Close', 'U', 'b'),
    '451': ('N', 'Early Open/Close', 'U', 'b'),
    '452': ('N', 'Late Open/Close', 'U', 'b'),
    '453': ('N', 'Failed to Open', 'U', 'b'),
    '454': ('N', 'Failed to Close', 'U', 'b'),
    '455': ('N', 'Auto-arm Failed', 'U', 'b'),
    '456': ('N', 'Partial Arm', 'U', 'b'),
    '457': ('N', 'User Exit Error', 'U', 'b'),
    '458': ('N', 'User on Premises', 'U', 'b'),
    '459': ('N', 'Recent Close', 'U', 'b'),
    '461': ('N', 'Wrong Code Entry', 'Z', 'b'),
    '462': ('N', 'Legal Code Entry', 'U', 'b'),
    '463': ('N', 'Re-arm after Alarm', 'U', 'b'),
    '464': ('N', 'Auto-arm Time Extended', 'U', 'b'),
    '465': ('N', 'Panic Alarm Reset', 'Z', 'b'),
    '466': ('N', 'Service On/Off Premises', 'U', 'b'),
    '501': ('Q', 'Access reader disable', 'Z', 'a'),
    '520': ('R', 'Sounder/Relay Disable', 'Z', 'a'),
    '521': ('R', 'Bell 1 disable', 'Z', 'a'),
    '522': ('R', 'Bell 2 disable', 'Z', 'a'),
    '523': ('R', 'Alarm relay disable', 'Z', 'a'),
    '524': ('R', 'Trouble relay disable', 'Z', 'a'),
    '525': ('R', 'Reversing relay disable', 'Z', 'a'),
    '526': ('R', 'Notification Appliance Ckt. # 3 disable', 'Z', 'a'),
    '527': ('R', 'Notification Appliance Ckt. # 4 disable', 'Z', 'a'),
    '531': ('S', 'Module Added', 'Z', 'a'),
    '532': ('S', 'Module Removed', 'Z', 'a'),
    '551': ('T', 'Dialer disabled', 'Z', 'a'),
    '552': ('T', 'Radio transmitter disabled', 'Z', 'a'),
    '553': ('T', 'Remote Upload/Download disabled', 'Z', 'a'),
    '570': ('U', 'Zone/Sensor bypass', 'Z', 'a'),
    '571': ('U', 'Fire bypass', 'Z', 'a'),
    '572': ('U', '24 Hour zone bypass', 'Z', 'a'),
    '573': ('U', 'Burglary Bypass', 'Z', 'a'),
    '574': ('U', 'Group Bypass', 'U', 'a'),
    '575': ('U', 'Swinger Bypass', 'Z', 'a'),
    '576': ('U', 'Access zone shunt', 'Z', 'a'),
    '577': ('U', 'Access point bypass', 'Z', 'a'),
    '578': ('U', 'Vault Bypass', 'Z', 'a'),
    '579': ('U', 'Vent Bypass', 'Z', 'a'),
    '601': ('V', 'Manual trigger test report', 'Z', 'a'),
    '602': ('V', 'Periodic test report', 'Z', 'a'),
    '603': ('V', 'Periodic RF transmission', 'Z', 'a'),
    '604': ('V', 'Fire test', 'U', 'a'),
    '605': ('V', 'Status report to follow', 'Z', 'a'),
    '606': ('V', 'Listen-in to follow', 'Z', 'a'),
    '607': ('V', 'Walk test mode', 'U', 'a'),
    '608': ('V', 'System Trouble Present', 'Z', 'a'),
    '609': ('V', 'Video Transmitter active', 'Z', 'a'),
    '611': ('V', 'Point tested OK', 'Z', 'a'),
    '612': ('V', 'Point not tested', 'Z', 'a'),
    '613': ('V', 'Intrusion Zone Walk Tested', 'Z', 'a'),
    '614': ('V', 'Fire Zone Walk Tested', 'Z', 'a'),
    '615': ('V', 'Panic Zone Walk Tested', 'Z', 'a'),
    '616': ('V', 'Trouble Service Request', 'Z', 'a'),
    '621': ('W', 'Event Log reset', 'Z', 'a'),
    '622': ('W', 'Event Log 50% full', 'Z', 'a'),
    '623': ('W', 'Event Log 90% full', 'Z', 'a'),
    '624': ('W', 'Event Log overflow', 'Z', 'a'),
    '625': ('W', 'Time/Date reset', 'U', 'a'),
    '626': ('W', 'Time/Date inaccurate', 'Z', 'a'),
    '627': ('W', 'Program mode entry', 'Z', 'a'),
    '628': ('W', 'Program mode exit', 'Z', 'a'),
    '629': ('W', '32 Hour Event log marker', 'Z', 'a'),
    '630': ('X', 'Schedule change', 'Z', 'a'),
    '631': ('X', 'Exception schedule change', 'Z', 'a'),
    '632': ('X', 'Access schedule change', 'Z', 'a'),
    '641': ('Y', 'Senior Person Watch Trouble (No movement)', 'Z', 'a'),
    '642': ('Y', 'Latch-key Supervision', 'U', 'a'),
    '651': ('Z', 'Identifies ADT Authorized Dealer', 'Z', 'a'),
    '652': ('Z', 'Reserved for ADEMCO Use', 'U', 'a'),
    '653': ('Z', 'Reserved for ADEMCO Use', 'U', 'a'),
    '654': ('Z', 'System Inactivity', 'Z', 'a'),
    '703': ('Z', 'Auxiliary #3', 'Z', 'a'),
    '704': ('Z', 'Installer Test', 'Z', 'a'),
    '750': ('*', 'Assign Your Own Description', '?', 'a'),
    '751': ('*', 'Assign Your Own Description', '?', 'a'),
    '752': ('*', 'Assign Your Own Description', '?', 'a'),
    '753': ('*', 'Assign Your Own Description', '?', 'a'),
    '754': ('*', 'Assign Your Own Description', '?', 'a'),
    '755': ('*', 'Assign Your Own Description', '?', 'a'),
    '756': ('*', 'Assign Your Own Description', '?', 'a'),
    '757': ('*', 'Assign Your Own Description', '?', 'a'),
    '758': ('*', 'Assign Your Own Description', '?', 'a'),
    '759': ('*', 'Assign Your Own Description', '?', 'a'),
    '760': ('*', 'Assign Your Own Description', '?', 'a'),
    '761': ('*', 'Assign Your Own Description', '?', 'a'),
    '762': ('*', 'Assign Your Own Description', '?', 'a'),
    '763': ('*', 'Assign Your Own Description', '?', 'a'),
    '764': ('*', 'Assign Your Own Description', '?', 'a'),
    '765': ('*', 'Assign Your Own Description', '?', 'a'),
    '766': ('*', 'Assign Your Own Description', '?', 'a'),
    '767': ('*', 'Assign Your Own Description', '?', 'a'),
    '768': ('*', 'Assign Your Own Description', '?', 'a'),
    '769': ('*', 'Assign Your Own Description', '?', 'a'),
    '770': ('*', 'Assign Your Own Description', '?', 'a'),
    '771': ('*', 'Assign Your Own Description', '?', 'a'),
    '772': ('*', 'Assign Your Own Description', '?', 'a'),
    '773': ('*', 'Assign Your Own Description', '?', 'a'),
    '774': ('*', 'Assign Your Own Description', '?', 'a'),
    '775': ('*', 'Assign Your Own Description', '?', 'a'),
    '776': ('*', 'Assign Your Own Description', '?', 'a'),
    '777': ('*', 'Assign Your Own Description', '?', 'a'),
    '778': ('*', 'Assign Your Own Description', '?', 'a'),
    '779': ('*', 'Assign Your Own Description', '?', 'a'),
    '780': ('*', 'Assign Your Own Description', '?', 'a'),
    '781': ('*', 'Assign Your Own Description', '?', 'a'),
    '782': ('*', 'Assign Your Own Description', '?', 'a'),
    '783': ('*', 'Assign Your Own Description', '?', 'a'),
    '784': ('*', 'Assign Your Own Description', '?', 'a'),
    '785': ('*', 'Assign Your Own Description', '?', 'a'),
    '786': ('*', 'Assign Your Own Description', '?', 'a'),
    '787': ('*', 'Assign Your Own Description', '?', 'a'),
    '788': ('*', 'Assign Your Own Description', '?', 'a'),
    '789': ('*', 'Assign Your Own Description', '?', 'a'),
    '796': ('Z', 'Unable to output signal (Derived Channel)', 'Z', 'a'),
    '798': ('Z', 'STU Controller down (Derived Channel)', 'Z', 'a'),
    '900': ('Z', 'Download Abort Downloader', 'X', 'a'),
    '901': ('Z', 'Download Start/End', 'X', 'a'),
    '902': ('Z', 'Download Interrupted', 'X', 'a'),
    '910': ('Z', 'Auto-close with Bypass', 'Z', 'a'),
    '911': ('Z', 'Bypass Closing', 'Z', 'a'),
    '912': ('Z', 'Fire Alarm Silenced', 'X', 'a'),
    '913': ('Z', 'Supervisory Point test Start/End', 'U', 'a'),
    '914': ('Z', 'Hold-up test Start/End', 'U', 'a'),
    '915': ('Z', 'Burglary Test Print Start/End', 'X', 'a'),
    '916': ('Z', 'Supervisory Point test Start/End', 'X', 'a'),
    '917': ('Z', 'Burg. Diagnostics Start/End', 'Z', 'a'),
    '918': ('Z', 'Fire Diagnostics Start/End', 'Z', 'a'),
    '919': ('Z', 'Untyped diagnostics', 'Z', 'a'),
    '920': ('Z', 'Trouble Closing (closed with burg. During exit)', 'U', 'a'),
    '921': ('Z', 'Access Denied Code Unknown', 'U', 'a'),
    '922': ('Z', 'Supervisory Point Alarm', 'Z', 'a'),
    '923': ('Z', 'Supervisory Point Bypass', 'Z', 'a'),
    '924': ('Z', 'Supervisory Point Trouble', 'Z', 'a'),
    '925': ('Z', 'Hold-up Point Bypass', 'Z', 'a'),
    '926': ('Z', 'AC Failure for 4 hours', 'Z', 'a'),
    '927': ('Z', 'Output Trouble', 'Z', 'a'),
    '928': ('Z', 'User code for event', 'U', 'a'),
    '929': ('Z', 'Log-off', 'U', 'a'),
    '954': ('Z', 'Call Center Connection Failure', 'X', 'a'),
    '961': ('Z', 'Receiver Database Connection Fail/Restore', 'X', 'a'),
    '962': ('Z', 'License Expiration Notify', 'X', 'a'),
    '999': ('Z', '1 and 1/3 day no read log event', 'X', 'a')
    }


    # class constructor
    def __init__(self, decodelvl):
        logging.info('CID-001I DecodeCID object created')
        self.decodeLevel = decodelvl.upper()
        if ( (self.decodeLevel != 'VERBOSE') and (self.decodeLevel != 'NORMAL') and (self.decodeLevel != 'TERSE') ) :
            self.decodeLevel = 'NORMAL'


    # customize the Zone descriptions for your own security system
    def setZones(self,myZones):
        if ( (isinstance(myZones, dict)) and (len(myZones) != 0) ) :
            self.zones = myZones
        else : logging.info('CID-001W setZones() requires a populated dictionary')


    # customize the User descriptions for your own security system
    def setUsers(self,myUsers):
        if ( (isinstance(myUsers, dict)) and (len(myUsers) != 0) ) :
            self.users = myUsers
        else : logging.info('CID-002W setUsers() requires a populated dictionary')


    # decode the CID into reasonably simple English
    def getDescription(self, CID):
        thisCID = CID
        CID_QualCode = thisCID[0]
        CID_Event = thisCID[1:4]
        CID_Partition = thisCID[4:6]
        CID_AgentID = thisCID[6:9]

        try :
            resultTuple = self.CID_EventCodes[CID_Event]
            EQselector = resultTuple[3]
        except KeyError as ex :
                logging.error('CID-001E No description available for CID event code %s', CID_Event)
                return 'No description available for CID event code ' + CID_Event

        try :
            if resultTuple[2] == 'U':
                agent = 'User:' + self.users[CID_AgentID]
            elif resultTuple[2] == 'Z':
                agent = 'Zone:' + self.zones[CID_AgentID]
            elif resultTuple[2] == 'X':
                agent = 'ID:' + CID_AgentID
            else:
                agent = 'User: ???'
        except KeyError as ex :
                logging.error('CID-002E No description available for user/zone/agent %s',CID_AgentID)
                agent = 'Unknown user/zone/agent'

        try :
            if (self.decodeLevel == 'VERBOSE') :
                reply = ('Partition:' + CID_Partition + ', ' + self.CID_EventCategory[resultTuple[0]] + ', ' + (self.CID_EventQualifiers[EQselector][CID_QualCode]) + ':' + CID_Event + ' ' + resultTuple[1] + ', ' + agent)
            elif (self.decodeLevel == 'NORMAL') :
                reply = ('Partition:' + CID_Partition + ', ' + self.CID_EventQualifiers[EQselector][CID_QualCode] + ':' + CID_Event + ' ' + resultTuple[1] + ', ' + agent)
            elif (self.decodeLevel == 'TERSE') :
                reply = ('Partition:' + CID_Partition + ', ' + resultTuple[1] + ', ' + agent)
            else :
                logging.error('CID-003E Invalid input - unable to decode CID')
                return 'CID-003E Invalid input - unable to decode CID'

            reply = reply.replace('!','') # remove any exclamation mark(s) before they wreak havoc
            return reply

        except Exception as ex :
                logging.error('CID-004E Unable to decode CID %s', str(ex))
                return 'Unable to decode CID'


# end of DecodeCID Class
