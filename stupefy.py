#!/usr/bin/python3
"""
Copyright (c) N. A. Inc.  2022
This program is free software per V3, or later version, of the GNU General Public License.
It is distributed AS-IS, WITHOUT ANY WARRANTY, or implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.
"""

class Stupefy :

# Version 1.0
# A Python class to protect cleartext passwords, ideally of at least 8 characters,
# for Python applications running on a Raspberry Pi under Pi OS.


    # class constructor.
    def __init__(self) :
        self.cpuserial = ''
        try :
            fp = open('/proc/cpuinfo','rt')
            for line in fp :
                line = line.lower()
                line = line.strip()
                if( 'serial' in line and ':' in line ) :
                    self.cpuserial = line[-8:]
            fp.close()
        except (OSError) as ex :
            print('Unable to find or process file  /proc/cpuinfo', str(ex))
            exit(16)
        finally :
            if self.cpuserial == '' :
                print('Fatal error in Stupefy object -- cannot continue')
                exit (16)


    # obscure a cleartext password
    def doStupefy(self, clearPasswd) :
        key = self.generateKey(clearPasswd, self.cpuserial)
        stupefied = self.sxor(clearPasswd, key)
        return (repr(stupefied))


    # convert password back to cleartext
    def undoStupefy(self, stupefiedPasswd) :
        tmppwd = eval(stupefiedPasswd)
        key = self.generateKey(tmppwd, self.cpuserial)
        return self.sxor(tmppwd, key)


    # exclusive OR of two strings (thanks to Mark Byers)
    def sxor(self, str1, str2) :
        # convert strings to a list of character pair tuples
        # go through each tuple, converting them to ASCII code (ord)
        # perform exclusive or on the ASCII code
        # then convert the result back to ASCII (chr)
        # merge the resulting array of characters as a string
        return ''.join(chr(ord(a) ^ ord(b)) for a,b in zip(str1,str2))


    # generate key of same length as the cleartext password itself
    def generateKey(self, clearPasswd, cpuserial) :
        lenpw = len(clearPasswd)
        lenkey = len(cpuserial)
        if lenkey < lenpw :
            repeat = int(lenpw / lenkey)
        else : repeat = 0

        tmpkey = cpuserial
        while repeat > 0 :
            tmpkey = tmpkey + tmpkey
            repeat -= 1

        key = tmpkey[-lenpw:]       # only as long as the password
        key = key[::-1]             # reverse the key (because we can)
        return key



# end of Stupefy class
