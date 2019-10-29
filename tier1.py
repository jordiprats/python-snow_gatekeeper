#!/usr/bin/env python
from __future__ import print_function

"""
shh, no diguis res
"""

import re
import os
import sys
import getopt
import pysnow
import argparse
import requests
from datetime import datetime, timedelta
from configparser import SafeConfigParser

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def showJelp(msg=''):
    print("Usage:")
    print("   [-c|--config] <config file>")
    print("   [-l|--list]")
    print("");
    sys.exit(msg)

if __name__ == '__main__':
    list_option = False
    config_file = os.path.expanduser('~')+'/.shhrc'

    SHH_INSTANCE = ''
    SHH_USERNAME = ''
    SHH_PASSWORD = ''
    debug = False

    # parse opts
    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'hlc:', [
                                                                    'help'
                                                                    'list',
                                                                    'config=',
                                                                 ])
    except Exception as e:
        showJelp(str(e))


    for opt, arg in options:
        if opt in ('-l', '--list'):
            list_option = True
        elif opt in ('-c', '--config'):
            config_file = arg
        else:
            showJelp("unknow option")

    config = SafeConfigParser()
    config.read(config_file)

    if debug : eprint("CONFIG FILE PATH: "+config_file)

    try:
        debug = config.getboolean('shh', 'debug')
    except:
        pass

    try:
        SHH_INSTANCE = config.get('shh', 'instance').strip('"').strip()
        if debug : eprint("INSTANCE: "+SHH_INSTANCE)
    except Exception as e:
        sys.exit("ERROR: instance is mandatory - "+str(e))

    try:
        SHH_USERNAME = config.get('shh', 'username').strip('"').strip()
    except:
        sys.exit("ERROR: username is mandatory")

    try:
        SHH_PASSWORD = config.get('shh', 'username').strip('"').strip()
    except:
        sys.exit("ERROR: username is mandatory")

    # Create client object
    c = pysnow.client.Client(instance=SHH_INSTANCE, user=SHH_USERNAME, password=SHH_PASSWORD)

    today = datetime.today()
    sixty_days_ago = today - timedelta(days=60)

    # Query incident records with number starting with 'INC0123', created between 60 days˓→ago and today.

    qb = (pysnow.QueryBuilder().field('sys_created_on').between(sixty_days_ago, today))
    incident = c.resource(api_path='/table/incident')
    response = incident.get(query=qb)

    # Iterate over the matching records and print out number
    for record in response.all():
        print(record['number'])
