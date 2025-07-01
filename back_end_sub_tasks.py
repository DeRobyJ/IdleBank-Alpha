# aka "best", here are some common tasks that call the db functions
# Designed for use in game_action and game_minis
import game_dbwrite as dbw
import game_dbread as dbr
import game_util as gut
import conversions as conv
import temporal_variations as tv
import random
import math


# Deprecated, converts currency based on global production
def cur_convert(amount, currency, original_currency=None):
    cur_status = dbr.get_currencies_status()
    if cur_status[currency] == 0:
        return amount
    if original_currency:
        if cur_status[original_currency] == 0:
            return amount
    return conv.currency(cur_status, amount, currency, original_currency)


def get_base_production(chat_id):
    return gut.hourly_production_rate_of_level(
        dbr.login(chat_id)["production_level"])


def get_gear_multiplier(chat_id):
    return gut.total_multiplier_from_nick(
        dbr.login(chat_id)["nickname"])


def get_production(chat_id):
    return int(
        get_base_production(chat_id) *
        get_gear_multiplier(chat_id)
    )


def get_production_for_level(chat_id, lvl):
    user_multiplier = get_gear_multiplier(chat_id)
    return int(gut.hourly_production_rate_of_level(lvl) *
               user_multiplier)


def get_types_of(chat_id):
    memb = dbr.login(chat_id)["membership"]
    types_of_memb = conv.name(membership=memb)
    types = {"membership": memb}
    for type in types_of_memb:
        types[type] = types_of_memb[type]
    return types


def get_all_market_limits():
    block_limits = {}
    money_limits = {}
    for section in gut.list["block"]:
        data = dbr.get_market_data(section)
        block_limits[section] = data["block_limit"]
        money_limits[conv.name(block=section)[
            "currency"]] = data["money_limit"]
    return block_limits, money_limits


# Product average rate of money storages
def get_market_temperature():
    temp = 1
    for section in gut.list["block"]:
        data = dbr.get_market_data(section)
        temp *= data["money"] / data["money_limit"]
    temp = temp ** (1 / 7)
    return temp


# Average rate of money storages
def get_market_impulse():
    imp = 0
    for section in gut.list["block"]:
        data = dbr.get_market_data(section)
        imp += data["money"] / data["money_limit"]
        # imp += data["blocks"] / data["block_limit"]
    imp = imp / 7
    return imp


def get_section_money_rate(section, after_variation=0):
    data = dbr.get_market_data(section)
    return (data["money"] + after_variation) / data["money_limit"]


# Returns the rate to multiply to the from_cur to get the equivalent to_cur
def get_exchange_rate(from_cur, to_cur):
    block_limits, money_limits = get_all_market_limits()
    from_rate = money_limits[from_cur] / block_limits[
        conv.name(currency=from_cur)["block"]]
    to_rate = money_limits[to_cur] / block_limits[
        conv.name(currency=to_cur)["block"]]
    return max(0.1, min(10, from_rate / to_rate))


# from_cur is the section currency, to_cur is the user currency
def exchange_cur(qty, from_cur, to_cur):
    return max(min(qty, 10), int(qty * get_exchange_rate(from_cur, to_cur)))


# Automatically calculates and applies the bonus
def apply_block_bonus(qty, type=None, chat_id=None, deal=False):
    if chat_id:
        if tv.skip_bonus_and_discounts(chat_id, season_upget()):
            return int(qty)
    if not type:
        type = get_types_of(chat_id)["block"]
    block_limits, _ = get_all_market_limits()
    mean = gut.mean(block_limits)
    bonus_mult = max(1, min(10, block_limits[type] / mean))
    new_qty = int(qty * bonus_mult)
    print(qty, " -> ", new_qty)
    if False:  # deal and int(new_qty) > int(qty):
        market_give_blocks(type, int(new_qty - qty))
        print("Blocks taken from market")
    return new_qty


# Automatically calculates and applies the discount
def apply_discount(qty, cur=None, chat_id=None, deal=False):
    if chat_id:
        if tv.skip_bonus_and_discounts(chat_id, season_upget()):
            return int(qty)
    if not cur:
        cur = get_types_of(chat_id)["currency"]
    _, money_limits = get_all_market_limits()
    mean = gut.mean(money_limits)
    cost_mult = max(.1, min(1, money_limits[cur] / mean))
    new_qty = max(min(qty, 10), int(qty * cost_mult))
    if False:  # deal and int(new_qty) > int(qty):
        section = conv.name(currency=gut.sort(money_limits)[0][0])[
            "block"]
        market_give_money(section, int(qty - new_qty))
    return new_qty


# current_price_multiplier_pcent is an int between 0 and 100
# It should represent an interval centered at 3m
#  that is divided by 3 at 0 and multiplied by 3 at 100
def get_market_base_price(chat_id, section):
    viewer_level = dbr.login(chat_id)["production_level"]
    if viewer_level < 50:
        ref_lvl = viewer_level
    else:
        ref_lvl = viewer_level // 100 * 100 + 50
    ref_production_rate = gut.hourly_production_rate_of_level(ref_lvl)
    ref_production_rate = int(
        ref_production_rate * get_gear_multiplier(chat_id))
    market_data = dbr.get_market_data(section)
    center_price = ref_production_rate // 20
    calc_price = center_price * math.pow(
        3,
        market_data["current_price_multiplier_pcent"] / 50.0 - 1
    )
    base_price = max(10, calc_price)
    '''base_price = max(
        10,
        min(
            calc_price,
            int(market_data["money_limit"] * 1.01 / market_data["block_limit"])
        )
    )'''
    return base_price


def get_price_for_market(chat_id, section):
    # return get_market_base_price(chat_id, section)
    return get_market_final_price(chat_id, section)


def get_market_final_price(chat_id, section):
    prod = get_production(chat_id)
    final_price = exchange_cur(
        get_market_base_price(chat_id, section),
        conv.name(block=section)["currency"],
        get_types_of(chat_id)["currency"]
    )
    final_price = max(10, final_price)
    if prod < 1000:  # For new players, limit price to 2 minutes of production
        final_price = min(final_price, prod // 30)
    return final_price


def get_market_blocks_for(chat_id, money, section):
    price = get_market_final_price(chat_id, section)
    return int(money / price)


def market_put_money(section, amount):
    data = dbr.get_market_data(section)
    data["money"] += amount
    dbw.market_update(section, data)


def market_give_money(section, amount):
    data = dbr.get_market_data(section)
    print("market data:", data)
    data["money"] -= amount
    if data["money"] < 0:
        data["money_limit"] = max(
            1000000,
            data["money_limit"] + data["money"])
        data["money"] = 0
    dbw.market_update(section, data)


def market_put_blocks(section, amount):
    data = dbr.get_market_data(section)
    data["blocks"] += amount
    dbw.market_update(section, data)


def market_give_blocks(section, amount):
    data = dbr.get_market_data(section)
    data["blocks"] -= amount
    if data["blocks"] < 0:
        data["block_limit"] = max(
            1000,
            data["block_limit"] + data["blocks"])
        data["blocks"] = 0
    dbw.market_update(section, data)


def inventory_get(chat_id, item):
    if item in ["coal", "dice", "key", "mystery_item", "investment_pass"]:
        inventory = dbr.mini_get_player(chat_id, "inventory")
        if item not in inventory:
            return 0
        return inventory[item]
    if item in gut.list["block"]:
        type_name = conv.name(block=item)["currency"]
        return dbr.login(chat_id)["blocks"][type_name]
    if item in gut.list["crypto"]:
        player_CPdata = mini_get_player(chat_id, "Coinopoly")
        return float.fromhex(player_CPdata["Coins"][item])
    if item == "protections":
        return mini_get_player(chat_id, "Ore Miner")["protections"]
    return 0


def inventory_use(chat_id, item, quantity):
    if item in ["coal", "dice", "key", "mystery_item", "investment_pass"]:
        inventory = dbr.mini_get_player(chat_id, "inventory")
        if item not in inventory:
            return False
        if inventory[item] < quantity:
            return False
        inventory[item] -= quantity
        mini_up_player(chat_id, "inventory", inventory)
        return True
    if item in gut.list["block"]:
        type_name = conv.name(block=item)["currency"]
        if not dbr.check_mmmb(chat_id, type_name, qty=quantity):
            return False
        dbw.pay_block(chat_id, type_name, qty=quantity)
        return True
    if item in gut.list["crypto"]:
        player_CPdata = mini_get_player(chat_id, "Coinopoly")
        if float.fromhex(player_CPdata["Coins"][item]) < quantity:
            return False
        player_CPdata["Coins"][item] = float.hex(
            float.fromhex(player_CPdata["Coins"][item]) - quantity
        )
        mini_up_player(chat_id, "Coinopoly", player_CPdata)
        return True
    if item == "protections":
        player_OMdata = mini_get_player(chat_id, "Ore Miner")
        if player_OMdata["protections"] < quantity:
            return False
        player_OMdata["protections"] -= quantity
        mini_up_player(chat_id, "Ore Miner", player_OMdata)
        return True


def inventory_give(chat_id, item, quantity):
    if item in ["coal", "dice", "key", "mystery_item", "investment_pass"]:
        inventory = dbr.mini_get_player(chat_id, "inventory")
        if item not in inventory:
            inventory[item] = 0
        inventory[item] += quantity
        mini_up_player(chat_id, "inventory", inventory)
    if item in gut.list["block"]:
        type_name = conv.name(block=item)["currency"]
        dbw.pay_block(chat_id, type_name, qty=-quantity)
    if item in gut.list["crypto"]:
        player_CPdata = mini_get_player(chat_id, "Coinopoly")
        player_CPdata["Coins"][item] = float.hex(
            float.fromhex(player_CPdata["Coins"][item]) + quantity
        )
        mini_up_player(chat_id, "Coinopoly", player_CPdata)
    if item == "protections":
        player_OMdata = mini_get_player(chat_id, "Ore Miner")
        player_OMdata["protections"] += quantity
        mini_up_player(chat_id, "Ore Miner", player_OMdata)


def minis_player_data_init(chat_id):
    dn_data = dbr.mini_get_player(chat_id, "Daily News")
    if len(dn_data) == 0:
        dn_data = {"chat_id": chat_id, "vote_timestamp": 0}
        dbw.mini_up_player(chat_id, "Daily News", dn_data)

    om_data = dbr.mini_get_player(chat_id, "Ore Miner")
    if len(om_data) == 0:
        om_data = {
            "chat_id": chat_id,
            "record_level": 0,
            "money_earnings": "0",
            "mined_mUSDmb": 0,
            "mined_mEmb": 0,
            "mined_mYmb": 0,
            "mined_mAUDmb": 0,
            "mined_mBRmb": 0,
            "mined_mIRmb": 0,
            "mined_mAmb": 0,
            "protections": 0
        }
        dbw.mini_up_player(chat_id, "Ore Miner", om_data)
    om_data["money_earnings"] = int(om_data["money_earnings"])

    ip_data = dbr.mini_get_player(chat_id, "Investment Plan")
    if len(ip_data) == 0:
        ip_data["last_investment_timestamp"] = 0
        ip_data["current_option"] = 0
        dbw.mini_up_player(chat_id, "Investment Plan", ip_data)

    cp_data = dbr.mini_get_player(chat_id, "Coinopoly")
    if len(cp_data) == 0:
        cp_data["Coins"] = {
            coin_name: float.hex(0.0) for coin_name in [
                "Bitcoin", "Ether", "Ada", "Dogecoin",
                "Polkadot", "Litecoin", "Solana",
                "IdleCoin", "Filecoin", "Terra",
                "Shiba", "BitTorrent", "Tether"
            ]
        }
        cp_data["position"] = 16 * (chat_id // 3) % 4
        cp_data["state"] = "landed"
        cp_data["timestamp"] = 0
        dbw.mini_up_player(chat_id, "Coinopoly", cp_data)

    update = False
    sr_data = dbr.mini_get_player(chat_id, "Global Steel Road")
    if len(sr_data) == 0:
        sr_data["Slots"] = ""
        sr_data["last_viewed_menu"] = "Market"
        update = True
    if ("investments_in_last_station" not in sr_data or
       "last_investment_timestamp" not in sr_data):
        sr_data["investments_in_last_station"] = 0
        sr_data["last_investment_timestamp"] = 0
        update = True
    if update:
        dbw.mini_up_player(chat_id, "Global Steel Road", sr_data)

    sc_data = dbr.mini_get_player(chat_id, "Shop Chain")
    if len(sc_data) == 0:
        sc_data["game_timestamp"] = 0
        sc_data["employees"] = 3
        for faction in gut.list["membership"]:
            sc_data["shops_" + faction] = 0
        sc_data["shops_" + dbr.login(chat_id)["membership"]] = 1
        sc_data["payment_amount"] = "10000"
        sc_data["history"] = ["0"] * 6
        sc_data["highscore"] = "0"
        sc_data["capital"] = "0"
        sc_data["sale_timestamp"] = 0
        dbw.mini_up_player(chat_id, "Shop Chain", sc_data)
    # The following changes will override the cache!
    sc_data["payment_amount"] = int(sc_data["payment_amount"])
    sc_data["highscore"] = int(sc_data["highscore"])
    sc_data["history"] = [int(el) for el in sc_data["history"]]
    for faction in gut.list["membership"]:
        sc_data["shops_" + faction] = int(sc_data["shops_" + faction])
    sc_data["employees"] = int(sc_data["employees"])


def mini_get_player(chat_id, game_name):
    minis_player_data_init(chat_id)
    return dbr.mini_get_player(chat_id, game_name)  # Gets cached copy


def mini_up_player(chat_id, game_name, player_data):
    dbw.mini_up_player(chat_id, game_name, player_data)


def season_upget():
    data = dbr.get_season_info()
    new_ts = tv.time_check(data["variations_timestamp"])
    if new_ts == data["variations_timestamp"]:
        # Don't write on db
        return data
    data["variations_timestamp"] = new_ts
    if gut.current_season() == data["current_season"]:
        dbw.up_season_info(data)
        return data

    # Season switch!
    data["current_season"] = gut.current_season()
    faction_ranking = gut.sort({
        i: data["faction"][i]["blocks_used"]
        for i in data["faction"]
    })
    if faction_ranking[0][1] == 0:
        for faction in data["faction"]:
            data["faction"][faction]["current_badge"] = ""
        dbw.up_season_info(data)
        return data  # nothing happened during this season
    # if something happened instead
    data1st = data["faction"][faction_ranking[0][0]]
    data2nd = data["faction"][faction_ranking[1][0]]
    data3rd = data["faction"][faction_ranking[2][0]]

    if data1st["top_contributor"] > 0:
        inventory_give(
            data1st["top_contributor"],
            "mystery_item",
            10 * (len(data1st["current_badge"]) + 1))
    data1st["current_badge"] = gut.faction_badge_increase(
        data1st["current_badge"])

    if data2nd["blocks_used"] > 0 and data2nd["top_contributor"] > 0:
        inventory_give(
            data2nd["top_contributor"],
            "mystery_item",
            3 * (len(data2nd["current_badge"]) + 1))

    if data3rd["blocks_used"] > 0 and data3rd["top_contributor"] > 0:
        inventory_give(
            data3rd["top_contributor"],
            "mystery_item",
            1 * (len(data3rd["current_badge"]) + 1))

    for i in range(1, len(faction_ranking)):
        data["faction"][faction_ranking[i][0]]["current_badge"] = ""

    for faction in data["faction"]:
        data["faction"][faction]["blocks_used"] = 0
        data["faction"][faction]["top_contributor"] = 0
    dbw.up_season_info(data)

    # Daily News Agencies Reset
    dn_data = dbr.mini_get_general("Daily News")
    dn_data["Agencies"] = {}
    dbw.mini_up_general(dn_data)
    return data


def season_ranking_point_tax(chat_id,  blocks,  levels=1):
    faction_ranking = tv.get_faction_ranking()
    faction = get_types_of(chat_id)["membership"]
    season_data = season_upget()
    self_points = season_data["faction"][faction]["blocks_used"]
    first_points = season_data["faction"][faction_ranking[0][0]]["blocks_used"]
    return gut.season_ranking_point_tax(blocks,  self_points,  first_points,  levels)


def upgrade_extra_costs(chat_id, new_level, faction):
    base_blocks = gut.block_cost_formula(new_level)
    points = season_ranking_point_tax(chat_id, base_blocks)
    extra_blocks_base = max(0, (points - 10) // 10)
    if extra_blocks_base < 1:
        return {}
    data = season_upget()
    badgelen = len(data["faction"][faction]["current_badge"])
    faction_rotation = gut.list["membership"].copy()
    faction_rotation.remove(faction)
    week = (gut.time_s() - gut.season_to_ts("3_2019")  # 1stJuly2019 = Monday
            ) // (60 * 60 * 24 * 7)
    extra_blocks = {
        conv.name(membership=f)["block"]: 0 for f in faction_rotation
    }
    for i in range(badgelen):
        extra_blocks[
            conv.name(membership=faction_rotation[
                (week + i) % len(faction_rotation)]
            )["block"]
        ] += extra_blocks_base
    return extra_blocks


def bulk_extra_costs_upgradability(chat_id, base_level, faction, blocks):
    base_blocks = gut.block_cost_formula(base_level)
    points = season_ranking_point_tax(chat_id, base_blocks)
    extra_blocks_base = max(0, (points - 10) // 10)
    if extra_blocks_base < 1:
        return math.inf
    data = season_upget()
    badgelen = len(data["faction"][faction]["current_badge"])
    faction_rotation = gut.list["membership"].copy()
    faction_rotation.remove(faction)
    week = (gut.time_s() - gut.season_to_ts("3_2019")  # 1stJuly2019 = Monday
            ) // (60 * 60 * 24 * 7)

    multipliers = {
        conv.name(membership=f)["currency"]: 0 for f in faction_rotation
    }
    for i in range(badgelen):
        multipliers[
            conv.name(membership=faction_rotation[
                (week + i) % len(faction_rotation)]
            )["currency"]
        ] += 1
    upgradability = int(min([
        blocks[conv.name(membership=f)["currency"]] / (
            extra_blocks_base *
            multipliers[conv.name(membership=f)["currency"]]
        )
        for f in faction_rotation
        if multipliers[conv.name(membership=f)["currency"]] > 0
    ]))
    return upgradability + base_level


def bulk_upgrade_extra_costs(chat_id, base_level, faction, levels):
    base_blocks = gut.block_cost_formula(base_level)
    points = season_ranking_point_tax(chat_id, base_blocks)
    extra_blocks_base = max(0, (points - 10) // 10)
    if extra_blocks_base < 1:
        return {}
    data = season_upget()
    badgelen = len(data["faction"][faction]["current_badge"])
    faction_rotation = gut.list["membership"].copy()
    faction_rotation.remove(faction)
    week = (gut.time_s() - gut.season_to_ts("3_2019")  # 1stJuly2019 = Monday
            ) // (60 * 60 * 24 * 7)

    extra_blocks = {
        conv.name(membership=f)["block"]: 0 for f in faction_rotation
    }
    for i in range(badgelen):
        extra_blocks[
            conv.name(membership=faction_rotation[
                (week + i) % len(faction_rotation)]
            )["block"]
        ] += extra_blocks_base * levels

    return extra_blocks


def user_season_squash(chat_id):
    # Check if user is not "new"
    if dbr.login(chat_id)["gear_level"] < 3 and dbr.login(chat_id)["production_level"] < 100:
        return
    if dbr.login(chat_id)["production_level"] == 0:  # safeguard
        return
    # Money Squash (can be upwards)
    pre_balance = dbr.login(chat_id)["balance"]
    new_balance = min(pre_balance, get_base_production(chat_id) * 24)
    new_balance += int(get_base_production(chat_id) * math.log10(pre_balance))
    dbw.pay_money(chat_id, pre_balance - new_balance)

    # Block Squash (can be upwards)
    pre_blocks = dbr.login(chat_id)["blocks"].copy()
    for block_type in pre_blocks:
        new_quantity = min(1000, pre_blocks[block_type])
        if block_type == get_types_of(chat_id)["currency"]:
            new_quantity += int(100 * math.log10(sum(pre_blocks.values())))
        dbw.pay_block(chat_id, block_type, qty=(pre_blocks[block_type] - new_quantity))

    # Items Squash (cannot be upwards)
    base_quantities = {  # How many you need to get 1000 blocks on the Flea Market
        "protections": 85,
        "coal": 70,
        "key": 30,
        "dice": 10,
        "investment_pass": 150
    }
    for crypto in gut.list["crypto"]:
        base_quantities[crypto] = 300

    for item in base_quantities:
        pre_quantity = inventory_get(chat_id, item)
        new_quantity = min(base_quantities[item], pre_quantity)
        new_quantity += int(base_quantities[item] / 10 * max(0, math.log10(base_quantities[item])))
        if new_quantity < pre_quantity:
            inventory_use(chat_id, item, pre_quantity - new_quantity)

    # SC Workers Squash (cannot be upwards)
    # Not implemented for now


def user_season_upget(chat_id):
    season_data = season_upget()
    user_sd = dbr.get_user_season_data(chat_id)
    if user_sd["season"] != season_data["current_season"]:
        user_sd["season"] = season_data["current_season"]
        user_sd["blocks_contributed"] = 0
        user_season_squash(chat_id)
        dbw.up_user_season_data(chat_id, user_sd)
    return user_sd


def season_add_blocks(chat_id, block_cost, extra_costs):
    data = season_upget()
    membership = dbr.login(chat_id)["membership"]
    data["faction"][membership]["blocks_used"] += block_cost

    # Checking and updating user contributions to own faction
    user_sd = user_season_upget(chat_id)
    user_sd["blocks_contributed"] += block_cost
    dbw.up_user_season_data(chat_id, user_sd)

    # Checking and updating top contributor data
    if data["faction"][membership]["top_contributor"] == 0:
        current_top_contribution = 0
    else:
        top_contr_sd = user_season_upget(
            data["faction"][membership]["top_contributor"])
        current_top_contribution = top_contr_sd["blocks_contributed"]

    # Checking and updating identification of top contributor
    if user_sd["blocks_contributed"] > current_top_contribution:
        data["faction"][membership]["top_contributor"] = chat_id

    # Adding blocks due to extra costs
    for block_type in extra_costs:
        data["faction"][
            conv.name(block=block_type)["membership"]
        ]["blocks_used"] += extra_costs[block_type]

    dbw.up_season_info(data)


def season_points(faction):
    season_data = season_upget()
    if faction == "first":
        faction_ranking = tv.get_faction_ranking()
        faction = faction_ranking[0][0]
    return season_data["faction"][faction]["blocks_used"]


def mystery_item_base_probability(chat_id):
    player_level = dbr.login(chat_id)["production_level"]
    player_gear = dbr.login(chat_id)["gear_level"]
    player_virtual_level = (player_gear**2 // 2) * 100 + player_level

    # top_level = dbr.get_multiplayer_info()["top_production"]["level"]
    top_gear = max(2, dbr.get_multiplayer_info()["top_gear"]["level"])
    top_virtual_level = (top_gear**2 // 2) * 100  # + top_level

    return 1 - player_virtual_level / top_virtual_level


def mystery_item_on_level_up(chat_id, lvl):
    user_data = dbr.login(chat_id)
    user_data["gear_level"]
    ref_level = 50 * (user_data["gear_level"] + 1)
    return lvl % ref_level == 0 and random.random() < (
        .25 * mystery_item_base_probability(chat_id))


def mystery_items_on_bulk_upgrade(chat_id, fromlvl, tolvl):
    user_data = dbr.login(chat_id)
    user_data["gear_level"]
    ref_level = 50 * (user_data["gear_level"] + 1)
    base_prob = mystery_item_base_probability(chat_id)

    start_level = (fromlvl // ref_level) * ref_level
    current_level = start_level + ref_level
    mitems = 0
    while current_level < tolvl:
        mitems += int(random.random() < (
            .25 * base_prob
        ))
        current_level += ref_level
    return mitems


def get_valves(chat_id):
    return dbr.login(chat_id)["shut_valves"]


def get_all_valve_values():
    cur_status = dbr.get_currencies_status()
    cur_order = [(i, cur_status[i]) for i in cur_status]
    cur_order = sorted(cur_order, key=lambda item: item[1], reverse=True)
    cur_order = [i[0] for i in cur_order]

    return {
        cur_order[0]: 2 * (10 ** 9),
        cur_order[1]: 15 * (10 ** 8),
        cur_order[2]: 10 ** 9,
        cur_order[3]: 7 * (10 ** 8),
        cur_order[4]: 5 * (10 ** 8),
        cur_order[5]: 4 * (10 ** 8),
        cur_order[6]: 35 * (10 ** 7)
    }


def get_valve_value(chat_id):
    user_currency = get_types_of(chat_id)["currency"]
    valve_value = get_all_valve_values()[user_currency]
    return valve_value


def get_level_opening_valves(chat_id):
    level = dbr.login(chat_id)["production_level"]
    level += get_valves(chat_id) * get_valve_value(chat_id)
    return level


def get_valve_operation_price(chat_id):
    return get_production(chat_id) * 100


def get_max_valve_closing(chat_id):
    valve_value = get_valve_value(chat_id)
    level = dbr.login(chat_id)["production_level"]
    return max(0, (level - (10**6)) // valve_value)
