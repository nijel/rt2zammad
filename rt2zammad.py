#!/usr/bin/env python
"""
Quick and dirty attempt to migrate issues from Request Tracker to Zammad.
"""

import base64
import json
import os
import pickle
import sys

from rt import Rt
from zammad_py import ZammadAPI
from zammad_py.api import Resource, TagList, TicketArticle


class Tag(Resource):

    path_attribute = "tags"

    def add(self, obj, id, item):
        response = self._connection.session.post(
            self.url + "/add",
            data={
                "object": obj,
                "o_id": id,
                "item": item,
            },
        )
        return self._raise_or_return_json(response)


TEMPLATE = """{
"zammad_host": "",
"zammad_user": "",
"zammad_password": "",
"zammad_secure": true,
"rt_url": "",
"rt_user": "",
"rt_pass": "",
"rt_start": 1,
"rt_end": 1000,
"usermap": {},
"userdata": {}
}
"""

COMMENT_TEMPLATE = """
Ticket imported from Request Tracker

URL: https://oldsupport.weblate.org/Ticket/Display.html?id={numerical_id}
Created: {Created}
Resolved: {Resolved}
"""


if not os.path.exists("rt2zammad.json"):
    print("Missing rt2zammad.json!")
    print("Create one based on following template:")
    print(TEMPLATE)
    sys.exit(1)

with open("rt2zammad.json") as handle:
    config = json.load(handle)


ZAMMADS = {}


def get_zammad(user=None):
    if user not in ZAMMADS:
        kwargs = {}
        if user:
            kwargs["on_behalf_of"] = user
        ZAMMADS[user] = ZammadAPI(
            host=config["zammad_host"],
            username=config["zammad_user"],
            password=config["zammad_password"],
            is_secure=config["zammad_secure"],
            **kwargs
        )
    return ZAMMADS[user]


target = get_zammad()
target.user.me()

source = Rt(config["rt_url"], config["rt_user"], config["rt_pass"])
if not source.login():
    print("Failed to login to RT!")
    sys.exit(2)

if os.path.exists("rt2zammad.cache"):
    # Load RT from cache
    with open("rt2zammad.cache", "rb") as handle:
        data = pickle.load(handle)
    users = data["users"]
    queues = data["queues"]
    tickets = data["tickets"]
    attachments = data["attachments"]

else:
    # Load RT from remote
    users = {}
    attachments = {}
    tickets = []
    queues = set()

    def ensure_user(username):
        if username not in users:
            users[username] = source.get_user(username)

    for i in range(config["rt_start"], config["rt_end"]):
        print("Loading ticket {}".format(i))
        ticket = source.get_ticket(i)
        if ticket is None:
            break
        ticket["original_id"] = str(i)
        queues.add(ticket["Queue"])
        ensure_user(ticket["Creator"])
        ensure_user(ticket["Owner"])

        if ticket["original_id"] != ticket["numerical_id"]:
            # Merged ticket
            history = []
        else:
            history = source.get_history(i)
            for item in history:
                for a, title in item["Attachments"]:
                    attachments[a] = source.get_attachment(i, a)
                ensure_user(item["Creator"])
        tickets.append({"ticket": ticket, "history": history})
    with open("rt2zammad.cache", "wb") as handle:
        data = pickle.dump(
            {
                "users": users,
                "queues": queues,
                "tickets": tickets,
                "attachments": attachments,
            },
            handle,
        )

# Create tags
tag_list = TagList(target)
ticket_article = TicketArticle(target)
tag_obj = Tag(target)
tags = {tag["name"] for tag in tag_list.all()}
for queue in queues:
    queue = queue.lower().split()[0]
    if queue not in tags:
        tag_list.create({"name": queue})

STATUSMAP = {"new": 1, "open": 2, "resolved": 4, "rejected": 4, "deleted": 4}

USERMAP = {}

for user in target.user.all():
    USERMAP[user["email"].lower()] = user


def get_user(userdata, attr="login", default=None):
    email = userdata["EmailAddress"]
    lemail = email.lower()
    if lemail in config["usermap"]:
        email = lemail = config["usermap"][lemail]
    # Search existing users
    if lemail not in USERMAP:
        for user in target.user.search({"query": email}):
            USERMAP[user["email"].lower()] = user
    # Create new one
    if lemail not in USERMAP:
        kwargs = {"email": email}
        kwargs.update(config["userdata"])
        if "RealName" in userdata:
            realname = userdata["RealName"]
            if ", " in realname:
                last, first = realname.split(", ", 1)
            elif " " in realname:
                first, last = realname.split(None, 1)
            else:
                last = realname
                first = ""
            kwargs["lastname"] = last
            kwargs["firstname"] = first
        user = target.user.create(kwargs)
        USERMAP[user["email"].lower()] = user

    if default is None:
        return USERMAP[lemail][attr]
    return USERMAP[lemail].get(attr, default)


# Create tickets
for ticket in tickets:
    label = "RT-{}".format(ticket["ticket"]["original_id"])
    creator = get_user(users[ticket["ticket"]["Creator"]])
    print(f"Importing {label} ({creator})")

    if ticket["ticket"]["original_id"] != ticket["ticket"]["numerical_id"]:
        # Merged ticket
        get_zammad(creator).ticket.create(
            {
                "title": "{} [{}]".format(ticket["ticket"]["Subject"], label),
                "group": "Users",
                "state_id": 4,
                "customer": creator,
                "note": "RT-import:{}".format(ticket["ticket"]["original_id"]),
                "article": {
                    "subject": ticket["ticket"]["Subject"],
                    "body": "RT ticket merged into {}".format(
                        ticket["ticket"]["numerical_id"]
                    ),
                },
            }
        )
        continue
    new = get_zammad(creator).ticket.create(
        {
            "title": "{} [{}]".format(ticket["ticket"]["Subject"], label),
            "group": "Users",
            "state_id": STATUSMAP[ticket["ticket"]["Status"]],
            "customer": creator,
            "note": "RT-import:{}".format(ticket["ticket"]["original_id"]),
            "article": {
                "subject": ticket["ticket"]["Subject"],
                "body": ticket["history"][0]["Content"],
            },
        }
    )
    tag_obj.add("Ticket", new["id"], ticket["ticket"]["Queue"].lower().split()[0])
    ticket_article.create(
        {
            "ticket_id": new["id"],
            "body": COMMENT_TEMPLATE.format(**ticket["ticket"]),
            "internal": True,
        }
    )

    for item in ticket["history"]:
        if item["Type"] not in ("Correspond", "Comment"):
            continue
        files = []
        for a, title in item["Attachments"]:
            data = attachments[a]
            if data["Filename"] in ("", "signature.asc"):
                continue
            files.append(
                {
                    "filename": data["Filename"],
                    "data": base64.b64encode(data["Content"]).decode("utf-8"),
                    "mime-type": data["ContentType"],
                }
            )
        creator_id = get_user(users[item["Creator"]], "id")
        chown = creator_id != new["customer_id"] and "Agent" not in get_user(
            users[item["Creator"]], "roles", []
        )
        if chown:
            target.ticket.update(new["id"], {"customer_id": creator_id})
        TicketArticle(get_zammad(get_user(users[item["Creator"]]))).create(
            {
                "ticket_id": new["id"],
                "body": item["Content"],
                "internal": item["Type"] == "Comment",
                "attachments": files,
            }
        )
        if chown:
            target.ticket.update(new["id"], {"customer_id": new["customer_id"]})
