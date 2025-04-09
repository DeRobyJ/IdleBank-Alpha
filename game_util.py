# Code with most of the main progression math, and various utility functions
import time
import uistr
import math
import conversions as conv
import os

list = {"membership": ["FED", "ECB", "PBC", "RBA", "CBB", "RBI", "ACB"]}
for field in ["currency", "block", "symbol", "badge_letter", "badgemoji"]:
    list[field] = [conv.name(memb)[field] for memb in list["membership"]]
list["crypto"] = [
    "Ada",
    "Bitcoin",
    "BitTorrent",
    "Dogecoin",
    "Ether",
    "Filecoin",
    "IdleCoin",
    "Litecoin",
    "Shiba",
    "Solana",
    "Polkadot",
    "Terra",
    "Tether",
]


def time_s():
    real_time = time.time_ns() // 1000000000
    if os.environ["TABLE_NAME"] == "idlebank_alpha_testing":
        return int(real_time + 60 * 60 * 24 * 7)
    return int(real_time)


def hourly_production_rate_of_level(lvl):
    return lvl * 720


def block_cost_formula(lvl):
    return lvl // 10 + 1


def money_cost_formula(lvl):
    if lvl == 1:
        mon = 2
    else:
        cur_hprod = hourly_production_rate_of_level(lvl - 1)
        mon = cur_hprod * lvl // 240  # aka: 3 * lvl**2
    return mon


def production_upgrade_costs(lvl):
    return {
        "Blocks": block_cost_formula(lvl),
        "Money": money_cost_formula(lvl)
    }


def bulk_upgrade_costs(base_lvl, target_lvl, block_cost_mult):
    # Both formulas are slightly imprecise, they overextimate a bit, and it's ok
    money = (
        target_lvl * (target_lvl + 1) * (2 * target_lvl + 1) -
        base_lvl * (base_lvl + 1) * (2 * base_lvl + 1)
    ) // 2
    blocks = (
        (
            target_lvl * (target_lvl + 1) -
            base_lvl * (base_lvl + 1)
        ) // 20 + target_lvl - base_lvl
    ) * block_cost_mult
    return {
        "Blocks": blocks,
        "Money": money
    }


def bulk_upgradability(base_lvl, money, blocks, block_cost_mult):
    # estimate
    money_max_lvl = int(math.pow(
        base_lvl * (base_lvl + 1) * (2 * base_lvl + 1) / 2 + money,
        1 / 3
    ))
    # exact
    blocks_max_lvl = int(
        (
            math.sqrt(
                441 + 4 * (
                    base_lvl**2 + 21 * base_lvl + 20 * (blocks // block_cost_mult)
                )
            ) - 21
        ) / 2
    )
    return min(money_max_lvl, blocks_max_lvl)


def season_ranking_point_tax(blocks):
    tier_A_blocks = min(blocks, 10)
    tier_B_blocks = max(0, min(blocks - 10, 30 - 10))
    tier_C_blocks = max(0, min(blocks - 30, 60 - 30))
    tier_D_blocks = max(0, min(blocks - 60, 100 - 60))
    tier_E_blocks = max(0, min(blocks - 100, 1000 - 100))
    tier_F_blocks = max(0, min(blocks - 1000, 10000 - 1000))

    to_self_market = (
        tier_B_blocks * 30 // 100 +
        tier_C_blocks * 50 // 100
    )
    to_last_market = (
        tier_D_blocks * 75 // 100 +
        tier_E_blocks * 90 // 100 +
        tier_F_blocks * 99 // 100
    )
    points = (
        tier_A_blocks +
        tier_B_blocks + tier_C_blocks - to_self_market +
        tier_D_blocks + tier_E_blocks + tier_F_blocks - to_last_market
    )

    return points, to_self_market, to_last_market


def bulk_season_ranking_point_tax(totblocks, levels):
    blocks_per_level = totblocks // levels
    points, to_self_market, to_last_market = season_ranking_point_tax(
        blocks_per_level
    )
    return (
        points * levels,
        to_self_market * levels,
        to_last_market * levels
    )


def current_balance(production_level, saved_balance, timestamp, multiplier=1):
    time_since_ts = time_s() - timestamp
    produced = (hourly_production_rate_of_level(production_level) *
                multiplier * time_since_ts / (60 * 60))
    return int(saved_balance + produced)


# Deprecated
def gear_multipliers(gear_badges):
    superbadges = len(gear_badges) // 100
    badgemoji = {
        "D": "💵",
        "E": "💶",
        "Y": "💴",
        "O": "🌊",
        "B": "🐊",
        "I": "🪔",
        "A": "🌍",
    }
    badgelist = []
    keys = [key for key in badgemoji.keys()]
    # list(badgemoji.keys()) didn't work
    for badgekey in keys:
        badgemoji[badgemoji[badgekey]] = badgemoji[badgekey]
        badgelist.append(badgemoji[badgekey])
    gears = {}
    for gear in badgelist:
        gears[gear] = 0
    for badge in gear_badges[superbadges * 100:]:
        gears[badgemoji[badge]] += 1
    multipliers = {}
    for gear in badgelist:
        multipliers[gear] = 1 + superbadges * 2 + (.1 * gears[gear])
    return multipliers


def total_multiplier(gear_badges):
    return 1 + len(gear_badges) / 10
    # Old code here
    multipliers = gear_multipliers(gear_badges)
    multiplier = 1
    for m in multipliers:
        multiplier *= multipliers[m]
    return multiplier


def total_multiplier_from_nick(nick_data):
    return 1 + len(get_badge_line(nick_data)) / 10
    # Old code here
    multipliers = gear_multipliers(
        get_badge_line(nick_data))
    tot_multiplier = 1
    for gear in multipliers:
        tot_multiplier *= multipliers[gear]
    return tot_multiplier


def balance(production_level, gear_level,
            gear_badges, saved_balance, balance_timestamp):
    multiplier = total_multiplier(gear_badges)

    res = current_balance(production_level, saved_balance,
                          balance_timestamp, multiplier)
    # return min(res, (10 ** 10)-1)
    return res


def float_balance(production_level, gear_level,
                  gear_badges, saved_balance, balance_timestamp):
    multiplier = total_multiplier(gear_badges)

    time_since_ts = time_s() - balance_timestamp
    produced = (hourly_production_rate_of_level(production_level) *
                multiplier * time_since_ts / (60 * 60))
    res = produced + saved_balance
    return res


def new_account_data(membership):
    cur_time = time_s()
    data = []
    data += [("account_creation_timestamp", cur_time)]
    data += [("last_login_timestamp", cur_time)]
    data += [("production_level", 0)]
    data += [("gear_level", 0)]
    data += [("saved_balance", 20)]
    for cur in list["currency"]:
        if cur == conv.name(membership=membership)["currency"]:
            data += [("blocks_" + cur, 50)]
        else:
            data += [("blocks_" + cur, 0)]
    data += [("balance_timestamp", cur_time)]
    data += [("settings", default_settings)]
    return data


def check_block_growth_old(last_login, account_creation,
                           membership, global_production, gear_level):
    current_time = time_s()
    player_cur = conv.name(membership=membership)["currency"]
    best_prod = max(global_production.values()) + 1

    blocks = []
    count = 10 - (global_production[player_cur]) * 10 // best_prod
    # 10 - ((a-1) * 10 // b)

    if gear_level > 0:
        count *= gear_level

    checked_time = account_creation
    while checked_time <= current_time:
        if checked_time > last_login:
            if (time.gmtime(checked_time).tm_mon == 12 and
               time.gmtime(checked_time).tm_mday > 23):
                changed_type = (
                    list["currency"].index(player_cur) +
                    time.gmtime(checked_time).tm_year % (
                        len(list["currency"])) + 1) % len(
                    list["currency"])
                blocks.append(
                    (list["currency"][changed_type],
                     count, checked_time))
            else:
                blocks.append((player_cur, count, checked_time))
        # print(checked_time, last_login, current_time)
        if gear_level == 0:
            checked_time += (60 * 60 * 24 * 7)
        else:
            checked_time += (60 * 60 * 24)
    # print(blocks)
    return blocks


def gear_blocks(badge_line):
    badgemoji = {
        "D": "💵",
        "E": "💶",
        "Y": "💴",
        "O": "🌊",
        "B": "🐊",
        "I": "🪔",
        "A": "🌍",
    }
    badgelist = []
    keys = [key for key in badgemoji.keys()]
    # list(badgemoji.keys()) didn't work
    for badgekey in keys:
        badgemoji[badgemoji[badgekey]] = badgemoji[badgekey]
        badgelist.append(badgemoji[badgekey])
    gears = {}
    for gear in badgelist:
        gears[gear] = 0
    for badge in badge_line:
        gears[badgemoji[badge]] += 1
    return {
        "Dollar": gears[badgemoji["D"]] * 10,
        "Euro": gears[badgemoji["E"]] * 10,
        "Yuan": gears[badgemoji["Y"]] * 10,
        "AUDollar": gears[badgemoji["O"]] * 10,
        "Real": gears[badgemoji["B"]] * 10,
        "Rupee": gears[badgemoji["I"]] * 10,
        "Afro": gears[badgemoji["A"]] * 10
    }


def check_block_growth(badge_line, last_login, account_creation):
    checked_time = account_creation
    current_time = time_s()
    blocks = []
    while checked_time <= current_time:
        if checked_time > last_login:
            to_give = gear_blocks(badge_line)
            for cur in to_give:
                if to_give[cur] > 0:
                    blocks.append((cur, to_give[cur], checked_time))
        checked_time += (60 * 60 * 24)
    return blocks


def is_offer_valid(proposed_amt, ordered_offer_list):
    if len(ordered_offer_list) == 0:
        return True
    return proposed_amt >= (ordered_offer_list[0][1]["offer"] +
                            ordered_offer_list[0][1]["offer"] // 10)


def offer_id_to_reserve(ordered_offer_list):
    ids = [i for i in range(10)]
    if len(ordered_offer_list) < len(ids):
        for item in ordered_offer_list:
            ids.remove(item[0])
        return ids[0], True, -1
    else:
        return ordered_offer_list[-1][0], False, ordered_offer_list[-1][1][
            "bidder_chat_id"]


def is_user_in_list(chat_id, offer_list):
    for offer in offer_list:
        if chat_id == offer[1]["bidder_chat_id"]:
            return True, offer[0]
    return False, -1


def nickname_pack(nick_data):
    nick_packed = {}
    nick_packed["language"] = {"S": nick_data["language"]}
    nick_packed["adjective_1"] = {"N": str(nick_data["adjective_1"])}
    nick_packed["adjective_2"] = {"N": str(nick_data["adjective_2"])}
    nick_packed["noun"] = {"N": str(nick_data["noun"])}
    nick_packed["badges"] = {"S": nick_data["badge_line"]}

    return nick_packed


def nickname_unpack(nick_packed):
    if nick_packed == "-":
        return "-"
    nick_data = {}
    nick_data["language"] = nick_packed["language"]["S"]
    nick_data["adjective_1"] = int(nick_packed["adjective_1"]["N"])
    nick_data["adjective_2"] = int(nick_packed["adjective_2"]["N"])
    nick_data["noun"] = int(nick_packed["noun"]["N"])
    if "badges" in nick_packed:
        nick_data["badge_line"] = nick_packed["badges"]["S"]
    else:
        nick_data["badge_line"] = ""

    return nick_data


def user_season_data_pack(user_sd):
    sd_packed = {}
    sd_packed["season"] = {"S": user_sd["season"]}
    sd_packed["blocks_contributed"] = {"N": str(user_sd["blocks_contributed"])}

    return sd_packed


def user_season_data_unpack(sd_packed):
    user_sd = {}
    user_sd["season"] = sd_packed["season"]["S"]
    user_sd["blocks_contributed"] = int(sd_packed["blocks_contributed"]["N"])

    return user_sd


settings_list = [
    "Bulk_confirm",
    "CP_notification",
    "DN_Agency_mysteryitem_notification"
]


def settings_pack(settings):
    flag = 0
    v = 1
    for setting in settings_list:
        if settings[setting]:
            flag += v
        v *= 2
    return flag


def settings_unpack(flag):
    settings = {}
    for setting in settings_list:
        if flag % 2 == 1:
            settings[setting] = True
        else:
            settings[setting] = False
        flag //= 2
    return settings


default_settings = settings_pack({
    "Bulk_confirm": False,
    "CP_notification": True,
    "DN_Agency_mysteryitem_notification": True
})


def get_badge_line(nick_data):
    if nick_data == "-":
        return ""
    elif "badge_line" not in nick_data:
        return ""
    else:
        return nick_data["badge_line"]


def nickname_randomize(chat_id):
    adj1s = len(uistr.get(chat_id, "NICK adjective_1"))
    adj2s = len(uistr.get(chat_id, "NICK adjective_2"))
    nouns = len(uistr.get(chat_id, "NICK noun"))

    nick_data = {}
    nick_data["language"] = "Translate"
    nick_data["adjective_1"] = chat_id % adj1s
    nick_data["adjective_2"] = (chat_id // adj1s) % adj2s
    nick_data["noun"] = ((chat_id // adj1s) // adj2s) % nouns
    nick_data["badge_line"] = ""
    return nick_data


def cutify_number(number, nzdigits, floor=False):
    number = int(number)
    digits = len(str(number))
    nzdigits = max(1, nzdigits)
    if digits <= nzdigits:
        return number
    zdigits = digits - nzdigits
    if not floor:
        number += 5 * (10 ** (zdigits - 1))
    number = (number // (10 ** zdigits)) * (10 ** zdigits)
    return number


def sort(dict_data):
    data = [(i, dict_data[i]) for i in dict_data]
    data = sorted(data, key=lambda item: item[1], reverse=True)
    return data


def mean(dict_data):
    return sum([dict_data[i] for i in dict_data]) / len(dict_data)


def prod_mean(dict_data):
    prod = 1
    for i in dict_data:
        prod *= dict_data[i]
    return prod**(1 / len(dict_data))


def season_to_ts(season):
    # season example: 1_2022
    month = {
        "1": "1",  # Jan
        "2": "4",  # Apr
        "3": "7",  # Jul
        "4": "10"  # Oct
    }[season[0]]
    year = season[2:]
    return int(time.mktime(time.strptime(year + "-" + month, "%Y-%m")))


def ts_to_season(ts):
    struct_t = time.gmtime(ts)
    year = struct_t.tm_year
    month = struct_t.tm_mon
    if month < 4:
        season = "1"
    elif month < 7:
        season = "2"
    elif month < 10:
        season = "3"
    else:
        season = "4"
    return season + "_" + str(year)


def current_season():
    return ts_to_season(time_s())


def time_till_next_season():
    cur_season = int(current_season()[0])
    cur_year = int(current_season()[2:])
    if cur_season == 4:
        next_season = 1
        next_year = cur_year + 1
    else:
        next_season = cur_season + 1
        next_year = cur_year
    return season_to_ts(str(next_season) + "_" + str(next_year)) - time_s()


season_emojis = {
    "1": "❄️",
    "2": "💐",
    "3": "☀️",
    "4": "🍁"
}


def faction_badge_increase(current):
    previous_season = {
        "1": "4",
        "2": "1",
        "3": "2",
        "4": "3"
    }[current_season()[0]]
    return current + previous_season


def faction_badge_line(badge_string):
    line = ""
    for c in badge_string:
        line += season_emojis[c]
    return line


def check_time_change(old_ts, new_ts, period):
    print("Period time pass:",
          old_ts / period, "to", new_ts / period, "::", period)
    return old_ts // period < new_ts // period


# pcent value to be applied to 3 minutes of production, in a range of 1m-9m
def market_target_price(m, b):
    # m is current ratio of money / target_money
    # b is current ration of blocks / target_blocks
    # Where "target" is half the storage size
    m = max(0, min(1, m / 2))
    b = max(0, min(1, b / 2))
    p = int(
        (1 - b) * 100 -
        2 * abs(m - .5) * 20
    )
    return max(0, min(100, p))


def gear_up_level_cost(base, to):
    return 25 * (to * (to + 1) - base * (base + 1))


def gear_up_block_prize(base, to):
    return gear_up_level_cost(base, to) // 5


def get_titlecode_forlvl(level):
    code = 0
    for tier_level in [
            10, 20, 30, 40, 50, 70, 100, 150, 200, 300, 450, 600, 1000]:
        if level < tier_level:
            return code
        code += 1
    return code
