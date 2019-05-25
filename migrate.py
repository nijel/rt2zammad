#!/usr/bin/env python
"""
Quick and dirty attempt to migrate issues from Request Tracker to Zammad.
"""

import json
import os
import sys

from requests.exceptions import HTTPError
from zammad_py import ZammadAPI
from rt import Rt

TEMPLATE = """{
"zammad_host": "",
"zammad_user": "",
"zammad_password": "",
"zammad_secure": true,
"rt_url": "",
"rt_user": "",
"rt_pass": ""
}
"""

if not os.path.exists('rt2zammad.json'):
    print('Missing rt2zammad.json!')
    print('Create one based on following template:')
    print(TEMPLATE)
    sys.exit(1)

with open('rt2zammad.json') as handle:
    config = json.load(handle)

target = ZammadAPI(
    host=config['zammad_host'],
    username=config['zammad_user'],
    password=config['zammad_password'],
    is_secure=config['zammad_secure'],
)
target.user.me()

source = Rt(config['rt_url'], config['rt_user'], config['rt_pass'])
if not source.login():
    print('Failed to login to RT!')
    sys.exit(2)
