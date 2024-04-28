# This has basically only been used in the game's early days, but it is convenient to keep it
import game_dbwrite as dbw
import game_dbread as dbr
import uistr
import time
import conversions as conv
import random


current_event = {
    "name": "moneycap_compensation",
    "max_usage": 1
}
'''
current_allowlist = [
    59444387
    ]
'''
#                               y  m  d   h  m  s
time_of_event = time.mktime((2021, 6, 24, 0, 0, 0, 0, 0, 0))  # global time
max_creation_timestamp = time.mktime((2021, 6, 24, 0, 0, 0, 0, 0, 0))


def exe_event(chat_id, event_name):
    user_data = dbr.login(chat_id)
    if user_data["account_status"] == "Not Activated":
        return "Abort", None

    if event_name == "AlphaPioneer":
        block_type = conv.name(membership=user_data["membership"])["currency"]
        dbw.add_block(chat_id, block_type, 20)
        return "Ok", uistr.get(chat_id, "Event " + current_event["name"])
    elif event_name == "1monthOld":
        block_type = conv.name(membership=user_data["membership"])["currency"]
        oftype = max(dbr.login(chat_id)["production_level"] // 5, 2)
        generalblocks = max(dbr.login(chat_id)["production_level"] // 10, 1)
        dbw.add_block(chat_id, block_type, oftype)
        dbw.add_block(chat_id, "Dollar", generalblocks)
        dbw.add_block(chat_id, "Euro", generalblocks)
        dbw.add_block(chat_id, "Yuan", generalblocks)
        return ("Ok",
                uistr.get(chat_id, "Event " + current_event["name"]).format(
                    blocks=(oftype + generalblocks * 3)))
    elif event_name == "moneycap_compensation":
        block_type = conv.name(membership=user_data["membership"])["currency"]
        dbw.add_block(chat_id, block_type, 20)
        return "Ok", uistr.get(chat_id, "Event " + current_event["name"])

    return "Abort", None


def check_event(chat_id):
    return False, None
    account_creation = dbr.login(chat_id)["account_creation_timestamp"]
    if time.time() < time_of_event:
        # print(time.time(), time.gmtime(time.time()))
        # print(time_of_event, time.gmtime(time_of_event))
        return False, None
    # if chat_id not in current_allowlist:
    if account_creation > max_creation_timestamp:
        return False, None
    event_usage_count = dbr.check_event_count(chat_id, current_event["name"])
    if event_usage_count >= current_event["max_usage"]:
        return False, None
    return True, event_usage_count


# returns message and keyboard!
def do_event(chat_id):
    account_creation = dbr.login(chat_id)["account_creation_timestamp"]
    # if chat_id not in current_allowlist:
    if account_creation > max_creation_timestamp:
        return uistr.get(chat_id, "Event none"), None
    check, count = check_event(chat_id)
    if not check:
        return uistr.get(chat_id, "Event done"), None

    r = dbw.up_event_count(chat_id, current_event["name"], count + 1)
    if r != "Ok":
        return uistr.get(chat_id, "Internal error"), None

    r, message = exe_event(chat_id, current_event["name"])
    if r != "Ok":
        return uistr.get(chat_id, "Internal error"), None
    # print(chat_id, " got the event ", current_event["name"], count+1)

    return message, None


# This is still running!
def check_halloween_ghost():
    can = False
    if time.gmtime().tm_mon == 10:
        if time.gmtime().tm_mday >= 27:
            can = True
    if time.gmtime().tm_mon == 11:
        if time.gmtime().tm_mday <= 2:
            can = True
    if can:
        if random.random() > 0.99:
            return True
    return False
