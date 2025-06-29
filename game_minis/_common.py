
import game_dbwrite as dbw
import game_dbread as dbr
import back_end_sub_tasks as best
import game_util as gut
import conversions as conv
import uistr
import time
import random
import json
import math
import print_util as put
import temporal_variations as tv

# origin_timestamp = int(time.mktime((2021, 6, 4, 0, 0, 0, 0, 0, 0)))
origin_timestamp = int(time.mktime((2025, 2, 6, 0, 0, 0, 0, 0, 0)))


# Currently available inventory items
'''
    coal            - Get in OM, DN and mystery_item, use in SR
    dice            - Get in DN and mystery_item, use in CP
    key             - Get in DN and mystery_item, use in OM
    investment_pass - Get in mystery_item, use in GSRF
    mystery_item    - Get in DN and mystery_item, use to get stuff (loot box)
'''


def ui_game_prizes_message(chat_id, owntype_blocks=0, owntype_money=0,
                           us_dollar_blocks=0, euro_blocks=0, yuan_blocks=0,
                           au_dollar_blocks=0, real_blocks=0, rupee_blocks=0,
                           afro_blocks=0):
    membership = best.get_types_of(chat_id)["membership"]
    if membership == "FED":
        us_dollar_blocks += owntype_blocks
    elif membership == "ECB":
        euro_blocks += owntype_blocks
    elif membership == "PCB":
        yuan_blocks += owntype_blocks
    elif membership == "RBA":
        au_dollar_blocks += owntype_blocks
    elif membership == "CBB":
        real_blocks += owntype_blocks
    elif membership == "RBI":
        rupee_blocks += owntype_blocks
    elif membership == "ACB":
        afro_blocks += owntype_blocks

    str_elements = []
    if us_dollar_blocks > 0:
        str_elements.append(put.pretty(us_dollar_blocks) + " mUSDmb")
    if euro_blocks > 0:
        str_elements.append(put.pretty(euro_blocks) + " mEmb")
    if yuan_blocks > 0:
        str_elements.append(put.pretty(yuan_blocks) + " mYmb")
    if au_dollar_blocks > 0:
        str_elements.append(put.pretty(au_dollar_blocks) + " mAUDmb")
    if real_blocks > 0:
        str_elements.append(put.pretty(real_blocks) + " mBRmb")
    if rupee_blocks > 0:
        str_elements.append(put.pretty(rupee_blocks) + " mIRmb")
    if afro_blocks > 0:
        str_elements.append(put.pretty(afro_blocks) + " mAmb")
    cur_sym = conv.name(membership=membership)["symbol"]
    if owntype_money > 0:
        str_elements.append(put.pretty(owntype_money) + " " + cur_sym)

    prizes_message = ""
    id = 0
    for _ in range(len(str_elements) - 2):
        prizes_message += str_elements[id] + ", "
        id += 1
    if len(str_elements) >= 2:
        prizes_message += str_elements[id] + \
            " " + uistr.get(chat_id, "and") + " "
        id += 1
    if len(str_elements) > 0:
        prizes_message += str_elements[id]

    return prizes_message

