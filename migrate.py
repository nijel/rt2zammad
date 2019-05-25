#!/usr/bin/env python
"""
Quick and dirty attempt to migrate issues from Request Tracker to Zammad.
"""

import pickle
import json
import os
import sys

from requests.exceptions import HTTPError
from zammad_py import ZammadAPI
from zammad_py.api import TagList
from rt import Rt, ALL_QUEUES

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

if os.path.exists('rt2zammad.cache'):
    with open('rt2zammad.cache', 'rb') as handle:
        data = pickle.load(handle)
    users = data['users']
    queues = data['queues']
    tickets = data['tickets']

else:
    users = {}
    tickets = []
    queues = set()

    def ensure_user(username):
        if username not in users:
            users[username] = source.get_user(username)


    for i in range(1, 1000):
        print('Loading ticket {}'.format(i))
        ticket = source.get_ticket(i)
        if ticket is None:
            break
        queues.add(ticket['Queue'])
        ensure_user(ticket['Creator'])
        ensure_user(ticket['Owner'])
        history = source.get_history(i)
        attachments = []
        for a in source.get_attachments_ids(i):
            attachment = source.get_attachment(i, a)
            attachments.append(attachments)
            ensure_user(attachment['Creator'])
        tickets.append({
            'ticket': ticket,
            'history': history,
            'attachments': attachments,
        })
    with open('rt2zammad.cache', 'wb') as handle:
        data = pickle.dump({'users': users, 'queues': queues, 'tickets': tickets}, handle)
