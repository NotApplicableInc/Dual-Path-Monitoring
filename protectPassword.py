#!/usr/bin/python3

"""
Copyright (c) N. A. Inc.  2022
This program is free software per V3, or later version, of the GNU General Public License.
It is distributed AS-IS, WITHOUT ANY WARRANTY, or implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.
"""

# Version 1.0

import sys
from stupefy import Stupefy

def main () :

    stu1 = Stupefy()

    if(len(sys.argv) == 2) :
        tmpstr1 = sys.argv[1].lower()
        if 'help' in tmpstr1 :
            print('This program obscures passwords when running under PiOS "Raspbian"')
            sys.exit(0)
        else: pass

    password = '????????'
    acceptable = False
    while acceptable is False:
        password = input('Enter your password (minimum of 8 characters): ')
        if len(password) > 7 :
            acceptable = True

    stupefiedpw = stu1.doStupefy(password)
    quotes = ''
    if ( (stupefiedpw.startswith("'")) and (stupefiedpw.endswith("'")) ) : quotes = 'single'
    if ( (stupefiedpw.startswith('"')) and (stupefiedpw.endswith('"')) ) : quotes = 'double'
    print('Your stupefied password is:', stupefiedpw, '  (including the enclosing', quotes, 'quotation marks!)', flush=True)
    print('  ... now copy and paste it into its target destination.', flush=True)

    tmpstr = stu1.undoStupefy(stupefiedpw)
    print ('As a final check, you entered: ', tmpstr, ' as your cleartext password', flush=True)



if __name__ == "__main__":
        main()
