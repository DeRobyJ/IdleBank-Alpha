# All game variations that happen at different times
import game_dbwrite as dbw
import game_dbread as dbr
import game_util as gut
import conversions as conv
import time

origin = gut.season_to_ts("3_2019")


def get_faction_ranking():
    data = dbr.get_season_info()
    faction_ranking = gut.sort({
        i: data["faction"][i]["blocks_used"]
        for i in data["faction"]
    })
    return faction_ranking


# This function returns all the current effects and their parameters
def stream(delta_month=0):
    variations = {
        "seasonal": {},
        "monthly": {}
    }
    # Seasonal (just for ui info)
    struct_t = time.gmtime(gut.time_s())
    month = (struct_t.tm_mon - 1 + delta_month) % 12
    current_season = gut.current_season()[0]
    if month < 3:
        current_season = "1"
    elif month < 6:
        current_season = "2"
    elif month < 9:
        current_season = "3"
    else:
        current_season = "4"
    if current_season == "1":
        variations["seasonal"]["First Faction Daily Shrink"] = None
        variations["seasonal"]["Block Cost Multiplier by Gear"] = None
    elif current_season == "3":
        variations["seasonal"]["Top3 Factions Biweek Shrink"] = None
        variations["seasonal"]["Top3 Captains Block Buying Lock"] = None
    elif current_season == "4":
        variations["seasonal"]["First Faction No Discounts or Bonus"] = None

    # Monthly
    origin_month = 2019 * 12 + 4
    struct_t = time.gmtime(gut.time_s())
    month = struct_t.tm_year * 12 + struct_t.tm_mon + delta_month - origin_month

    # DN
    if month % 13 == 0:
        variations["monthly"]["DN Options"] = -1
    elif month % 13 == 5:
        variations["monthly"]["DN Options"] = +1
    # CP
    if month % 4 == 0:
        variations["monthly"]["CP Dice Pity"] = None
    if month % 17 in [0, 9]:
        variations["monthly"]["CP House Degrade"] = 8
    elif month % 17 in [4, 14]:
        variations["monthly"]["CP Coin Tax"] = .5
    # OM
    if month % 7 == 0:
        variations["monthly"]["OM Extra Tool Durability"] = 5
    elif month % 7 == 4:
        variations["monthly"]["OM Extra Layer HP"] = 10
    # GSR
    if month % 9 == 0:
        variations["monthly"][
            "GSRF Extra Dividends and Degrade"] = (10, 10)
    if month % 23 in [0, 3, 6, 10, 13, 16]:
        variations["monthly"]["GSRF Invest Frenzy"] = None
    # IP
    if month % 11 == 0:
        variations["monthly"]["IP Turn Multiplier"] = 2
    if month % 5 == 0:
        variations["monthly"]["IP Comeback"] = .1  # invest price multiplier

    return variations


def get_month(delta_month):
    struct_t = time.gmtime(gut.time_s())
    return (struct_t.tm_mon - 1 + delta_month) % 12


# Seasonal variations


def market_reset(pcent):
    markets = {}
    for section in gut.list["block"]:
        markets[section] = dbr.get_market_data(section)
    new_limit_blocks = int(gut.mean(
        {sec: markets[sec]["block_limit"] for sec in markets}
    ))
    new_limit_money = int(gut.mean(
        {sec: markets[sec]["money_limit"] for sec in markets}
    ))
    for section in gut.list["block"]:
        markets[section]["block_limit"] = new_limit_blocks
        markets[section]["blocks"] = int(new_limit_blocks * pcent) // 100
        markets[section]["money_limit"] = new_limit_money
        markets[section]["money"] = int(new_limit_money * pcent) // 100
        dbw.market_update(section, markets[section])


def time_check(old_timestamp):
    new_timestamp = gut.time_s()
    if new_timestamp < old_timestamp + 30:
        return old_timestamp
    if old_timestamp < gut.season_to_ts("3_2019"):
        return new_timestamp
    current_season = gut.ts_to_season(new_timestamp)[0]

    if current_season == "1":  # Winter
        to_apply = gut.check_time_change(
            old_timestamp,
            new_timestamp,
            60 * 60 * 25)  # 25 hours
        if to_apply:
            section = conv.name(
                membership=get_faction_ranking()[0][0])["block"]
            market_data = dbr.get_market_data(section)
            market_data["block_limit"] -= market_data["block_limit"] // 10
            dbw.market_update(section, market_data)

    if current_season == "2":  # Spring
        if gut.ts_to_season(old_timestamp)[0] != current_season:
            market_reset(50)

    if current_season == "3":  # Summer
        to_apply = gut.check_time_change(
            old_timestamp,
            new_timestamp,
            60 * 60 * (24 * 14 + 2))  # 14 days + 2 hours
        if to_apply:
            market_data = dbr.get_market_data(conv.name(
                membership=get_faction_ranking()[0][0])["block"])
            market_data["block_limit"] = market_data["block_limit"] // 10
            market_data["money_limit"] = market_data["money_limit"] // 10
            dbw.market_update(conv.name(
                membership=get_faction_ranking()[0][0])["block"], market_data)

            market_data = dbr.get_market_data(conv.name(
                membership=get_faction_ranking()[1][0])["block"])
            market_data["block_limit"] = market_data["block_limit"] // 5
            market_data["money_limit"] = market_data["money_limit"] // 5
            dbw.market_update(conv.name(
                membership=get_faction_ranking()[1][0])["block"], market_data)

            market_data = dbr.get_market_data(conv.name(
                membership=get_faction_ranking()[2][0])["block"])
            market_data["block_limit"] = market_data["block_limit"] // 2
            market_data["money_limit"] = market_data["money_limit"] // 2
            dbw.market_update(conv.name(
                membership=get_faction_ranking()[2][0])["block"], market_data)

    if current_season == "4":  # Fall
        if gut.ts_to_season(old_timestamp)[0] != current_season:
            market_reset(10)

    return new_timestamp


def block_upgrade_cost_multiplier(chat_id, sd):
    if sd["current_season"][0] == "1":
        user_gear = dbr.login(chat_id)["gear_level"]
        return user_gear // 5 + 1
    return 1


def can_use_market(chat_id, sd):
    if sd["current_season"][0] != "3":
        return True
    data = dbr.get_season_info()
    faction_ranking = get_faction_ranking()

    return chat_id not in [
        data["faction"][faction_ranking[i][0]]["top_contributor"]
        for i in [0, 1, 2]
    ]


def skip_bonus_and_discounts(chat_id, sd):
    if sd["current_season"][0] != "4":
        return False
    if dbr.login(chat_id)["membership"] != get_faction_ranking()[0][0]:
        return False
    return True


# Monthly variations

def is_on(variation):
    return variation in stream()["monthly"]


def DN_options_increment():
    tv = stream()["monthly"]
    if "DN Options" in tv:
        return tv["DN Options"]
    return 0


def CP_house_degrade():
    tv = stream()["monthly"]
    if "CP House Degrade" in tv:
        return tv["CP House Degrade"]
    return 1


def CP_coin_tax():
    tv = stream()["monthly"]
    if "CP Coin Tax" in tv:
        return tv["CP Coin Tax"]
    return 0.


def OM_extra_durability():
    tv = stream()["monthly"]
    if "OM Extra Tool Durability" in tv:
        return tv["OM Extra Tool Durability"]
    return 0


def OM_extra_layer_hp():
    tv = stream()["monthly"]
    if "OM Extra Layer HP" in tv:
        return tv["OM Extra Layer HP"]
    return 0


def GSRF_extra_divdeg():
    tv = stream()["monthly"]
    if "GSRF Extra Dividends and Degrade" in tv:
        return tv["GSRF Extra Dividends and Degrade"]
    return (1, 0)


def GSRF_frenzy_invest_price_multiplier():
    tv = stream()["monthly"]
    if "GSRF Invest Frenzy" in tv:
        return .2
    return 1


def GSRF_frenzy_invest_count(chat_id):
    tv = stream()["monthly"]
    if "GSRF Invest Frenzy" in tv:
        fr = get_faction_ranking()
        position = 0
        while dbr.login(chat_id)["membership"] != fr[position][0]:
            position += 1
        return max(3, position + 1)
    return 3


def IP_turn_multiplier():
    tv = stream()["monthly"]
    if "IP Turn Multiplier" in tv:
        return tv["IP Turn Multiplier"]
    return 1


def IP_price_pity(chat_id):
    if dbr.login(chat_id)["membership"] == get_faction_ranking()[0][0]:
        return 1  # full price
    tv = stream()["monthly"]
    if "IP Comeback" in tv:
        return tv["IP Comeback"]
    return 1
