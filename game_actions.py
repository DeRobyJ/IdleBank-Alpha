# Elaborates and retrieves data, following specific user actions
import game_dbwrite as dbw
import game_dbread as dbr
import back_end_sub_tasks as best
import game_util as gut
import conversions as conv
import temporal_variations as tv
import uistr
import time
import random
import print_util as put
import math


# Checks wether an account exists with that ID.
# If it doesn't, it returns a list of factions for the player to choose from
def check_account(chat_id):
    r = dbr.login(chat_id)
    if r["account_status"] == "Not Activated":
        return {
            "status": r["account_status"],
            # don't use gut.list because faction ACB doesn't go here!
            "data": ["FED", "ECB", "PBC", "RBA", "CBB", "RBI"]
        }
    return {
        "status": r["account_status"],
        "data": None
    }


# Checks the type of balance for the account, for migration of users
# coming from the pre-single balance era
def check_balance_type(chat_id):
    return dbr.user_balance_type(chat_id)


def get_member_counts():
    r = dbr.get_member_counts()
    if len(r) < 0:
        return None
    return r


# A new account is saved in the database with the initial data and items
def activate_account(chat_id, membership):
    old_count = dbr.get_member_counts()[membership]
    r = dbw.activate_account(chat_id, membership, old_count + 1)
    if r != "Ok":
        print("Account activation error")
        return False
    else:
        return True


# Upgrades old accounts to single balance
def upgrade_to_single_balance(chat_id):
    r = load_main_menu(chat_id)
    user_data = r["user"]

    # this call also creates "saved_balance" record on db and ch
    dbw.consolidate_balance(chat_id)
    for cur in ["Dollar", "Euro", "Yuan"]:  # only need these
        dbw.give_money(chat_id, best.cur_convert(user_data["balance"][cur],
                                                 conv.name(
            membership=user_data["membership"])["currency"], cur))
        dbw.pay_money(chat_id, user_data["balance"][cur], cur)

    return "Ok"


# Gets and processes all the information needed for the main menu
# (meaning user data and global production of all currencies)
def load_main_menu(chat_id):
    ru = dbr.login(chat_id)
    last_login_time = ru["last_login_timestamp"]
    if ru["account_status"] == "Not Activated":
        print("Loading main menu on non activated account")
        return None
    rc = dbr.get_currencies_status()

    ru = dbr.login(chat_id)
    data = {}
    data["membership"] = ru["membership"]
    data["faction_badges"] = gut.faction_badge_line(
        best.season_upget()["faction"][ru["membership"]]["current_badge"]
    )
    data["production_hrate"] = gut.hourly_production_rate_of_level(
        ru["production_level"])
    data["production_level"] = ru["production_level"]
    data["balance"] = ru["balance"]
    if data["balance"] < 0:
        dbw.consolidate_balance(chat_id)
        data["balance"] = 0
    data["blocks"] = ru["blocks"]
    data["nickname"] = ru["nickname"]
    data["production_multiplier"] = gut.total_multiplier_from_nick(
        data["nickname"])
    data["gear_level"] = ru["gear_level"]
    account_creation_struct_t = time.gmtime(ru["account_creation_timestamp"])
    data["account_creation_datastr"] = str(
        account_creation_struct_t.tm_mday) + " " + uistr.get(
        chat_id, "Month")[account_creation_struct_t.tm_mon - 1] + " " + str(
        account_creation_struct_t.tm_year
    )
    data["last_login_datestr"] = uistr.date_string(chat_id, ru["balance_timestamp"])

    '''
    # Story of this soft reset: I had created a market system with automatic
    # exponential price: it would grow by x% at each buy.
    # Long story short, the price grew to numbers with tens of digits, so players
    # suddenly had the resources to upgrade indefinitely, and gear up indefinitely,
    # forcing me to do something. Now the game economics is perfectly able to
    # sustain those numbers, it couldn't back in September 2021

    # soft reset
    if last_login_time < 1631265995:
        data["blocks"] = {i:data["gear_level"]
            for i in ["Dollar", "Euro", "Yuan"]}
        data["blocks"][conv.name(membership=data["membership"])[
                                 "currency"]] += 50
        data["balance"] = 1000
        data["balance_timestamp"] = gut.time_s()
        if data["nickname"] != "-":
            data["nickname"]["badge_line"] += conv.name(
                membership=data["membership"])["badge_letter"]
            data["nickname"]["badge_line"] =data["nickname"]["badge_line"][:10]
            data["gear_level"] = min(10, data["gear_level"]+1)
            data["production_multiplier"] = gut.total_multiplier_from_nick(
                data["nickname"])
        else:
            data.pop("nickname")
        data["production_level"] = 0
        data["production_hrate"] = gut.hourly_production_rate_of_level(0)
        data["last_login_timestamp"] = gut.time_s()

        dbw.soft_reset(chat_id, data)
    '''

    badge_line = ""
    if "nickname" in data and "badge_line" in data["nickname"]:
        badge_line = data["nickname"]["badge_line"]
    block_growth = gut.check_block_growth(
        badge_line,
        ru["last_login_timestamp"],
        ru["account_creation_timestamp"]
    )
    blocks_per_type = {i: 0 for i in gut.list["currency"]}
    for block in block_growth:
        blocks_per_type[block[0]] += block[1]
    for blocktype in blocks_per_type:
        if blocks_per_type[blocktype] > 0:
            dbw.add_block(chat_id, blocktype, count=blocks_per_type[blocktype], logtime=block_growth[-1][2])

    return {
        "user": data,
        "currencies": rc
    }


# To be used exclusively for the "time left" upgrading information text
def get_float_balance(chat_id):
    user_data = dbr.login(chat_id)
    return gut.float_balance(
        user_data["membership"],
        user_data["production_level"],
        user_data["gear_level"],
        gut.get_badge_line(user_data["nickname"]),
        user_data["saved_balance"],
        user_data["balance_timestamp"]
    )


def get_settings(chat_id):
    return dbr.login(chat_id)["settings"]


def get_membership(chat_id):
    return dbr.login(chat_id)["membership"]


def toggle_setting(chat_id, setting):
    settings = dbr.login(chat_id)["settings"]
    settings[setting] = not settings[setting]
    dbw.up_settings(chat_id, settings)
    return uistr.get(chat_id, "Done")


# intended to be used when loading Main Menu
def can_upgrade(chat_id):
    user_data = dbr.login(chat_id)
    market_general_update()
    costs = gut.production_upgrade_costs(user_data["production_level"] + 1)
    costs["Blocks"] *= tv.block_upgrade_cost_multiplier(
        chat_id, best.season_upget())

    cur = conv.name(membership=user_data["membership"])["currency"]

    extra_costs = best.upgrade_extra_costs(
        user_data["production_level"] + 1,
        user_data["membership"])

    can = True
    if check_balance_type(chat_id) == "new":
        balance = user_data["balance"]
    else:
        balance = user_data["balance"][cur]

    if costs["Money"] > balance:
        can = False
    if costs["Blocks"] > user_data["blocks"][cur]:
        can = False
    missing_extra = {}
    for block_type in extra_costs:
        if extra_costs[block_type] > user_data["blocks"][
                conv.name(block=block_type)["currency"]]:
            missing_extra[
                conv.name(block=block_type)["currency"]] = (
                extra_costs[block_type] - user_data["blocks"][
                    conv.name(block=block_type)["currency"]]
            )
            can = False
    points, _, _ = gut.season_ranking_point_tax(costs["Blocks"])
    points += int((min(10000, costs["Blocks"]) - points) * best.season_pity_rate(
        user_data["membership"]
    ))
    return can, costs, extra_costs, missing_extra, points


# Back then, when a faction would overtake another one in the production leadeboard,
# it would reward that faction by restocking the market.
def check_and_reward_factions(increasing_currency, delta_increase):
    return  # FEATURE DISCONTINUED
    currencies_status = dbr.get_currencies_status().copy()
    cur_order_new = [(i, currencies_status[i]) for i in currencies_status]
    cur_order_new = sorted(
        cur_order_new, key=lambda item: item[1], reverse=True)
    cur_order_new = [i[0] for i in cur_order_new]

    currencies_status[increasing_currency] -= delta_increase
    cur_order_old = [(i, currencies_status[i]) for i in currencies_status]
    cur_order_old = sorted(
        cur_order_old, key=lambda item: item[1], reverse=True)
    cur_order_old = [i[0] for i in cur_order_old]
    changed = False
    new_winner = False  # if the first position was changed
    for i in range(len(currencies_status)):
        if cur_order_new[i] != cur_order_old[i]:
            changed = True
            if i == 0:
                new_winner = True
            break
    if new_winner:
        for currency in currencies_status:
            if currency != cur_order_new[0]:
                section = conv.name(currency=currency)["block"]
                market_restock(section, pcent=75)
    elif changed:
        for currency in currencies_status:
            if currency != cur_order_new[0]:
                section = conv.name(currency=currency)["block"]
                market_restock(section, pcent=50)


def upgrade_money_printer(chat_id):
    multiplayer_info_upget(chat_id)
    user_data = dbr.login(chat_id)
    new_level = user_data["production_level"] + 1
    type = conv.name(membership=user_data["membership"])["currency"]
    costs = gut.production_upgrade_costs(new_level)
    costs["Blocks"] *= tv.block_upgrade_cost_multiplier(
        chat_id, best.season_upget())

    r = dbr.check_payment(chat_id, costs["Money"])
    if not r:
        return uistr.get(chat_id, "Insufficient balance")
    if not can_upgrade(chat_id)[0]:
        return uistr.get(chat_id, "Insufficient blocks")
    dbw.up_money_printer(chat_id, costs, check_balance_type(chat_id))
    extra_costs = best.upgrade_extra_costs(new_level, user_data["membership"])
    for block_type in extra_costs:
        dbw.pay_block(
            chat_id,
            conv.name(block=block_type)["currency"],
            extra_costs[block_type])

    production_delta = best.get_production_for_level(
        chat_id, new_level) - best.get_production_for_level(
            chat_id, new_level - 1)
    new_global_production = dbr.get_currencies_status()[
        type] + production_delta
    dbw.up_global_production(type, new_global_production)

    points, blocks_self, blocks_last = gut.season_ranking_point_tax(costs["Blocks"])
    best.season_add_blocks(chat_id, points, extra_costs)
    if blocks_self > 0:
        self_section = conv.name(membership=user_data["membership"])["block"]
        best.market_put_blocks(self_section, blocks_self)
    if blocks_last > 0:
        faction_ranking = tv.get_faction_ranking()
        last_section = conv.name(
            membership=faction_ranking[-1][0])["block"]
        best.market_put_blocks(last_section, blocks_last)
    points += int((min(10000, costs["Blocks"]) - points) * best.season_pity_rate(
        user_data["membership"]
    ))

    if best.mystery_item_on_level_up(chat_id, new_level):
        best.inventory_give(chat_id, "mystery_item", 1)
        return uistr.get(chat_id, "found mystery item")
    return uistr.get(chat_id, "Done")


calculated_bulk_upgrades = {}
calculated_point_tax = {}
time_allowed = {}


def calculate_bulk_upgrade(chat_id):
    user_data = dbr.login(chat_id)
    start_level = user_data["production_level"]
    if start_level < 35 and user_data["gear_level"] < 1:
        return {"levels_done": 0}
    player_cur = conv.name(membership=user_data["membership"])["currency"]
    if check_balance_type(chat_id) == "new":
        start_balance = user_data["balance"]
    else:
        start_balance = user_data["balance"][player_cur]
    start_blocks = user_data["blocks"][player_cur]

    hash_id = (str(chat_id) + "_" +
               str(start_level) + "_" +
               str(user_data["balance_timestamp"]) + "." +
               str(len(str(start_balance))) + "_" +
               str(start_blocks) + "." + str(len(str(start_blocks))) + "_"
               )
    if hash_id in calculated_bulk_upgrades:
        # print("bulk up found ", hash_id)
        return calculated_bulk_upgrades[hash_id]
    # print("bulk up creating ", hash_id)

    start_time = time.time()
    calculated_bulk_upgrades[hash_id] = {}

    calculated_bulk_upgrades[hash_id]["can"] = True
    tot_costs = {"Money": 0, "Blocks": 0}
    tot_extra_costs = {bt: 0 for bt in gut.list["block"]}
    levels_done = 0
    balance = start_balance
    blocks = start_blocks
    calculated_bulk_upgrades[hash_id]["season_points"] = 0
    calculated_bulk_upgrades[hash_id]["self_market_input"] = 0
    calculated_bulk_upgrades[hash_id]["last_market_input"] = 0

    if start_level < 5100:
        time_limit = 1.5
        if chat_id in time_allowed:
            time_limit = time_allowed[chat_id]
        while time.time() - start_time < time_limit and calculated_bulk_upgrades[
                hash_id]["can"] and start_level + levels_done < 5100:
            # print("Bulk up processing for", chat_id, ":",
            #       levels_done, time.time() - start_time)
            costs = gut.production_upgrade_costs(start_level + 1 + levels_done)
            costs["Blocks"] *= tv.block_upgrade_cost_multiplier(
                chat_id, best.season_upget())
            if costs["Money"] > balance - tot_costs["Money"]:
                calculated_bulk_upgrades[hash_id]["can"] = False
            if costs["Blocks"] > blocks - tot_costs["Blocks"]:
                calculated_bulk_upgrades[hash_id]["can"] = False
            extra_costs = best.upgrade_extra_costs(
                start_level + levels_done + 1,
                user_data["membership"])
            for block_type in extra_costs:
                if extra_costs[block_type] + tot_extra_costs[
                        block_type] > user_data["blocks"][
                        conv.name(block=block_type)["currency"]]:
                    calculated_bulk_upgrades[hash_id]["can"] = False
                else:
                    tot_extra_costs[block_type] += extra_costs[block_type]
            if calculated_bulk_upgrades[hash_id]["can"]:
                levels_done += 1
                tot_costs["Money"] += costs["Money"]
                tot_costs["Blocks"] += costs["Blocks"]
                if costs["Blocks"] not in calculated_point_tax:
                    calculated_point_tax[costs["Blocks"]] = (
                        gut.season_ranking_point_tax(costs["Blocks"])
                    )
                points, blocks_s, blocks_l = calculated_point_tax[costs["Blocks"]]
                points += int(
                    (min(10000, costs["Blocks"]) - points) * best.season_pity_rate(
                        user_data["membership"], tot_costs["Blocks"] - costs["Blocks"]
                    )
                )
                calculated_bulk_upgrades[hash_id]["season_points"] += points
                calculated_bulk_upgrades[hash_id]["self_market_input"] += blocks_s
                calculated_bulk_upgrades[hash_id]["last_market_input"] += blocks_l
    else:  # Start lvl >= 5100
        block_cost_mult = tv.block_upgrade_cost_multiplier(
            chat_id, best.season_upget())
        normal_upgradable_level = gut.bulk_upgradability(
            start_level, start_balance, start_blocks, block_cost_mult)
        if len(best.season_upget()["faction"][user_data["membership"]]["current_badge"]) > 0:
            extra_costs_upgradable_level = best.bulk_extra_costs_upgradability(
                start_level,
                user_data["membership"],
                user_data["blocks"]
            )
            levels_done = min(
                normal_upgradable_level,
                extra_costs_upgradable_level
            ) - start_level
            tot_extra_costs = best.bulk_upgrade_extra_costs(
                start_level,
                user_data["membership"],
                levels_done
            )
        else:
            levels_done = normal_upgradable_level - start_level
        if levels_done == 0:
            return {"levels_done": 0}
        costs = gut.bulk_upgrade_costs(start_level, start_level + levels_done, block_cost_mult)
        tot_costs["Money"] = costs["Money"]
        tot_costs["Blocks"] = costs["Blocks"]
        points, blocks_s, blocks_l = gut.bulk_season_ranking_point_tax(
            costs["Blocks"],
            levels_done
        )
        points += int(
            (min(10000 * levels_done, costs["Blocks"]) - points) * best.season_pity_rate(
                user_data["membership"], costs["Blocks"]
            )
        )
        calculated_bulk_upgrades[hash_id]["season_points"] = points
        calculated_bulk_upgrades[hash_id]["self_market_input"] = blocks_s
        calculated_bulk_upgrades[hash_id]["last_market_input"] = blocks_l

    calculated_bulk_upgrades[hash_id]["money"] = tot_costs["Money"]
    calculated_bulk_upgrades[hash_id]["blocks"] = tot_costs["Blocks"]
    calculated_bulk_upgrades[hash_id]["levels_done"] = levels_done
    calculated_bulk_upgrades[hash_id]["level"] = start_level + levels_done
    calculated_bulk_upgrades[hash_id]["start_level"] = start_level
    calculated_bulk_upgrades[hash_id]["tot_extra_costs"] = tot_extra_costs

    return calculated_bulk_upgrades[hash_id]


def bulk_upgrade(chat_id):
    data = calculate_bulk_upgrade(chat_id)
    player_cur = conv.name(
        membership=dbr.login(chat_id)["membership"])["currency"]

    if "levels_done" not in data:
        return "."
    if data["levels_done"] == 0:
        return "."
    if chat_id not in time_allowed:
        time_allowed[chat_id] = 1.5
    time_allowed[chat_id] = max(time_allowed[chat_id] * .9, .02)

    dbw.up_money_printer(
        chat_id,
        {"Money": data["money"], "Blocks": data["blocks"]},
        check_balance_type(chat_id),
        data["levels_done"])
    for block_type in data["tot_extra_costs"]:
        dbw.pay_block(
            chat_id,
            conv.name(block=block_type)["currency"],
            data["tot_extra_costs"][block_type])

    production_delta = (best.get_production_for_level(
        chat_id, data["level"]) -
        best.get_production_for_level(chat_id, data["start_level"]))
    new_global_production = (dbr.get_currencies_status()[player_cur] +
                             production_delta)
    dbw.up_global_production(player_cur, new_global_production)

    best.season_add_blocks(
        chat_id, data["season_points"], data["tot_extra_costs"]
    )
    if data["self_market_input"] > 0:
        self_section = conv.name(
            membership=dbr.login(chat_id)["membership"])["block"]
        best.market_put_blocks(self_section, data["self_market_input"])
    if data["last_market_input"] > 0:
        faction_ranking = tv.get_faction_ranking()
        last_section = conv.name(
            membership=faction_ranking[-1][0])["block"]
        best.market_put_blocks(last_section, data["last_market_input"])

    multiplayer_info_upget(chat_id)
    mystery_items = best.mystery_items_on_bulk_upgrade(
        chat_id, data["start_level"], data["level"]
    )

    if mystery_items > 0:
        best.inventory_give(chat_id, "mystery_item", mystery_items)
        return uistr.get(chat_id, "found mystery items").format(
            qty=mystery_items
        )
    return uistr.get(chat_id, "Done")


def check_and_get_leaderboards(chat_id):
    order = {}
    for currency in gut.list["currency"]:
        raw_data = dbr.get_leaderboard_raw_data()[currency]
        order[currency] = [
            (int(i), best.get_production(int(i)))
            for i in raw_data
            if conv.name(membership=load_main_menu(int(i))
                         ["user"]["membership"])
            ["currency"] == currency
        ]
        order[currency] = sorted(
            order[currency], key=lambda item: item[1], reverse=True)

    reader_production = best.get_production(chat_id)
    reader_currency = conv.name(membership=load_main_menu(chat_id)[
                                "user"]["membership"])["currency"]
    update = False
    if len(order[reader_currency]) < 3:
        update = True
    elif reader_production >= order[reader_currency][2][1]:
        update = True
    if update and (str(chat_id)
                   not in dbr.get_leaderboard_raw_data()[reader_currency]):
        raw_data = dbr.get_leaderboard_raw_data()[reader_currency] + [chat_id]
        order[reader_currency] = [
            (int(i), best.get_production(int(i)))
            for i in raw_data
            if conv.name(membership=load_main_menu(int(i))
                         ["user"]["membership"])
            ["currency"] == reader_currency
        ]
        order[reader_currency] = sorted(
            order[reader_currency], key=lambda item: item[1], reverse=True)[:3]
        new_raw_data = [str(i[0]) for i in order[reader_currency]]
        dbw.up_leaderboard(reader_currency, new_raw_data)
    return order


def multiplayer_info_upget(chat_id):
    data = dbr.get_multiplayer_info().copy()
    current_time = gut.time_s()
    if "global_production_timestamp" not in data:
        data["global_production_timestamp"] = current_time - 60 * 60 * 24 * 31
    if int(time.time() * 100) % 99 < 3:  # raughly check 1/33 of the times
        for ci in list(data["players_activity"].keys()):
            if data["players_activity"][ci] <= current_time - 60 * 60 * 24 * 30:
                data["players_activity"].pop(ci)

    player_return = False
    if str(chat_id) not in data["players_activity"]:
        player_return = True
    data["players_activity"][str(chat_id)] = current_time

    player_gear_level = dbr.login(chat_id)["gear_level"]
    if (len(data["top_gear"]) == 0 or
       data["top_gear"]["level"] < player_gear_level):
        data["top_gear"]["level"] = player_gear_level
        data["top_gear"]["chat_id"] = chat_id

    player_prod_level = dbr.login(chat_id)["production_level"]
    if (len(data["top_production"]) == 0 or
       data["top_production"]["level"] < player_prod_level):
        data["top_production"]["level"] = player_prod_level
        data["top_production"]["chat_id"] = chat_id

    dbw.up_multiplayer_info(data)
    if current_time - data["global_production_timestamp"
                           ] > 60 * 60 * 24 * 25 or player_return:
        recalculate_global_production()

    minfo = {
        "tot_player_count": 0,
        "top_gear": data["top_gear"],
        "top_production": data["top_production"],
        "last_day_active_count": 0,
        "last_week_active_count": 0,
        "last_month_active_count": 0
    }
    minfo["tot_player_count"] = 0
    counts = get_member_counts()
    for memb in counts:
        minfo["tot_player_count"] += counts[memb]

    for ci in data["players_activity"]:
        minfo["last_month_active_count"] += 1
        if data["players_activity"][ci] > current_time - 60 * 60 * 24 * 7:
            minfo["last_week_active_count"] += 1
        if data["players_activity"][ci] > current_time - 60 * 60 * 24:
            minfo["last_day_active_count"] += 1

    return minfo


last_target_sr_check_ts = 0
target_storage_rate = 1000


# Main function of market updating
# This fuction was carefully crafted over 2 years to work well both in a
# stagnant metagame and in an explosive one, with sudden exponential growths
def market_general_update(force_target=False):
    global last_target_sr_check_ts, target_storage_rate
    if gut.time_s() - last_target_sr_check_ts > 3 * 60 or force_target:
        target_storage_rate = gut.prod_mean(
            {section: (dbr.get_market_data(section)["money_limit"] /
                       dbr.get_market_data(section)["block_limit"])
                for section in gut.list["block"]}
        )
        target_storage_rate = max(1000, target_storage_rate)
        last_target_sr_check_ts = gut.time_s()

    for section in gut.list["block"]:
        data = dbr.get_market_data(section)
        if data == "Create Market":
            data = {
                "type": section,
                "money": 5 * 10**8,
                "money_limit": 10**9,
                "blocks": 5000,
                "block_limit": 10000,
                "current_price_multiplier_pcent": 100,
                "timestamp": 1630703700
            }
        if "money_limit" not in data:  # migration shield
            data["money_limit"] = 10**9
            data["block_limit"] = 10000
        data["money_limit"] = max(1000000, data["money_limit"])
        data["block_limit"] = max(1000, data["block_limit"])
        target = {
            "money": data["money_limit"] // 2,
            "blocks": data["block_limit"] // 2
        }
        Vmoney = min(data["money"], 2 * target["money"]) / target["money"]
        Vblocks = min(data["blocks"], 2 * target["blocks"]) / target["blocks"]
        target_price_multiplier_pcent = int(
            100 - Vblocks * 46 *                          # Stays in [8,100]
            min(1,  # (only takes action if visualized pcent in 0-24 or 76-100)
                (1 - (abs(1 - Vmoney) - 0.5) * 2 * 3 / 8))  # disco upto -37.5%
        )
        temperature = best.get_market_temperature()
        temperature = min(1, temperature * 2)  # in [0 (0% markets), 1 (>50%)]
        # multiplier for money storage shrinking
        temperature_mult = (
            temperature * 1 +
            (1 - temperature) * .1**(1 / (24 * 12))
        )  # maximum shrinking: 90% a day
        up_period = 5 * 60

        any_update = False
        while gut.time_s() - data["timestamp"] >= up_period:
            data["current_price_multiplier_pcent"] = (
                data["current_price_multiplier_pcent"] +
                target_price_multiplier_pcent) // 2

            money_rate = data["money"] / data["money_limit"]
            block_rate = data["blocks"] / data["block_limit"]
            if money_rate > .55:
                qty = int(max(50, data["money"] * money_rate / 50))
                qty = min(qty, data["money_limit"] // 2)
                data["money_limit"] += qty
                data["money"] -= qty
            if money_rate < .45 and data["money_limit"] > 1000000:
                qty = int(max(50, (data["money_limit"] - data["money"]) * (1 - money_rate) / 50))
                data["money_limit"] -= qty
                data["money"] += qty
            if block_rate > .55:
                qty = int(data["blocks"] * block_rate / 50)
                qty = min(qty, data["block_limit"] // 2)
                data["block_limit"] += qty
                data["blocks"] -= qty
            if block_rate < .45 and data["block_limit"] > 1000:
                qty = int((data["block_limit"] - data["blocks"]) * (1 - block_rate) / 50)
                data["block_limit"] -= qty
                data["blocks"] += qty
            data["money_limit"] = max(data["money_limit"], 1000000)
            data["block_limit"] = max(data["block_limit"], 1000)

            # Market rate alignment (invisible hand)
            if random.random() * 7 < 1:
                self_rate = data["money_limit"] / max(data["block_limit"], 1)
                rate_step_mult = (target_storage_rate / self_rate) ** .03
                data["money_limit"] = int(data["money_limit"] * rate_step_mult)
                data["block_limit"] = int(data["block_limit"] / rate_step_mult)

            data["money_limit"] = int(data["money_limit"] * temperature_mult)

            # Automatic Cooling
            for v in ["money", "money_limit"]:  # , "blocks", "block_limit"]:
                data[v] -= int(data[v] * random.random() * 0.002)

            data["timestamp"] += up_period
            any_update = True
        if any_update:
            data["money_limit"] = max(data["money_limit"], 1000000)
            data["block_limit"] = max(data["block_limit"], 1000)
            data["blocks"] = max(data["blocks"], 0)
            data["money"] = max(data["money"], 0)
            dbw.market_update(section, data)


# Updates the market and gets info about a single section
def market_upget(chat_id, section):
    market_general_update()
    data = dbr.get_market_data(section)
    target = {
        "money": data["money_limit"] // 2,
        "blocks": data["block_limit"] // 2
    }
    data["blocks"] = max(data["blocks"], 0)
    data["money"] = max(data["money"], 0)
    Vmoney = min(data["money"], 2 * target["money"]) / target["money"]
    Vblocks = min(data["blocks"], 2 * target["blocks"]) / target["blocks"]
    target_price_multiplier_pcent = int(
        100 - Vblocks * 46 *                          # Stays in [8,100]
        min(1,  # (only takes action if visualized pcent in 0-24 or 76-100)
            (1 - (abs(1 - Vmoney) - 0.5) * 2 * 3 / 8))  # disco upto -37.5%
    )
    impulse = target_price_multiplier_pcent - \
        data["current_price_multiplier_pcent"]
    final_price = best.get_market_final_price(chat_id, section)
    return (final_price, impulse, data["money"], data["blocks"],
            data["money_limit"], data["block_limit"])


# Some events restock the market to a certain percentage
def market_restock(section, pcent=50):
    data = dbr.get_market_data(section)
    target_blocks = data["block_limit"] // 2
    data["blocks"] = max(
        data["blocks"],
        (target_blocks * 2 * pcent) // 100
    )
    dbw.market_update(section, data)


def market_reset(section):
    data = dbr.get_market_data(section)
    data["blocks"] = data["block_limit"] // 2
    data["money"] = data["money_limit"] // 2
    data["current_price_multiplier_pcent"] = 50
    dbw.market_update(section, data)


# When the market has too much or too few money, upgrading players contribute
# to bringing it back to the range between 25% and 75%
# DEPRECATED
def upgrade_tax(chat_id, cached=None):
    if cached:  # Checks for a dictionary with at least 1 key
        cur_money = cached["cur_money"]
        target_money = cached["target_money"]
    else:
        user_data = dbr.login(chat_id)
        if user_data["gear_level"] == 0:
            if user_data["production_level"] < 40:
                return 0
        _, _, cur_money, _, money_limit, _ = market_upget(
            chat_id, conv.name(membership=user_data["membership"])["block"])
        target_money = money_limit // 2
        if cached is not None:  # cached is an empty dictionary
            cached["cur_money"] = cur_money
            cached["target_money"] = target_money
    if cur_money / target_money < 0.5:  # ranges from 0% to 10% of up cost
        return 0.2 * (0.5 - cur_money / target_money)
    if cur_money / target_money > 1.5:  # ranges from -0% to -40% of up cost
        return max(-0.8 * (cur_money / target_money - 1.5), -0.99)
    return 0


# DEPRECATED
def market_put_tax(chat_id, tax):
    user_data = dbr.login(chat_id)
    section = conv.name(membership=user_data["membership"])["block"]
    best.market_put_money(section, tax)


def can_sell(chat_id, section, quantity=1):
    block_type = conv.name(block=section)["currency"]
    if not dbr.check_mmmb(chat_id, block_type, quantity):
        return False
    # if not tv.can_use_market(chat_id, best.season_upget()):
    #    return False

    _, _, _, _, _, block_limit = market_upget(chat_id, section)
    data = dbr.get_market_data(section)
    general_subtotal = best.get_price_for_market(chat_id, section) * quantity
    if data["money"] - general_subtotal < 0:
        return False
    if data["blocks"] + quantity > block_limit * 10:
        return False

    return True


def can_buy(chat_id, section, quantity=1):
    user_price, _, _, _, money_limit, _ = market_upget(chat_id, section)
    r = dbr.check_payment(chat_id, user_price * quantity)
    if not r:
        return False
    if not tv.can_use_market(chat_id, best.season_upget()):
        return False

    data = dbr.get_market_data(section)
    general_subtotal = best.get_price_for_market(chat_id, section) * quantity
    if data["money"] + general_subtotal >= money_limit:
        return False
    if data["blocks"] - quantity < 0:
        return False

    return True


def market_buysell_limits(chat_id, section):
    (user_price, _, stored_money, stored_blocks,
     money_limit, block_limit) = market_upget(chat_id, section)
    market_price = best.get_price_for_market(chat_id, section)
    player_balance = dbr.login(chat_id)["balance"]
    player_blocks = dbr.login(chat_id)["blocks"][
        conv.name(block=section)["currency"]]

    buy_limit = max(0, min([
        stored_blocks,  # blocks in the market
        (money_limit - stored_money) // market_price,  # money market can take
        player_balance // user_price  # blocks player can afford
    ]))
    if not tv.can_use_market(chat_id, best.season_upget()):
        buy_limit = 0

    sell_limit = max(0, min([
        block_limit * 10 - stored_blocks,  # space left
        stored_money // market_price,  # blocks  market can afford
        player_blocks  # blocks currently owned by the player
    ]))

    return buy_limit, sell_limit


def market_sell(chat_id, section, quantity):
    user_price, _, _, _, money_limit, block_limit = market_upget(
        chat_id, section)
    data = dbr.get_market_data(section)
    general_subtotal = best.get_price_for_market(chat_id, section) * quantity
    if data["money"] - general_subtotal < 0:
        return uistr.get(chat_id, "Market empty money")
    if data["blocks"] + quantity > block_limit * 10:
        return uistr.get(chat_id, "Market full blocks")
    block_type = conv.name(block=section)["currency"]
    if not dbr.check_mmmb(chat_id, block_type, quantity):
        return uistr.get(chat_id, "No MMMB found")
    # if not tv.can_use_market(chat_id, best.season_upget()):
    #    return "Nah"

    user_money_gain = user_price * quantity
    data["money"] -= general_subtotal
    data["blocks"] += quantity

    dbw.market_update(section, data)
    dbw.give_money(chat_id, user_money_gain)
    dbw.add_block(chat_id, block_type, -quantity)
    return uistr.get(chat_id, "Done")


def market_buy(chat_id, section, quantity):
    user_price, _, _, _, money_limit, block_limit = market_upget(
        chat_id, section)
    data = dbr.get_market_data(section)
    general_subtotal = best.get_price_for_market(chat_id, section) * quantity
    if data["money"] + general_subtotal >= money_limit:
        return uistr.get(chat_id, "Market full money")
    if data["blocks"] - quantity < 0:
        return uistr.get(chat_id, "Market empty blocks")
    money_payment = user_price * quantity
    if not dbr.check_payment(chat_id, money_payment):
        return uistr.get(chat_id, "Insufficient balance")
    if not tv.can_use_market(chat_id, best.season_upget()):
        return "Nah"

    data["money"] += general_subtotal
    data["blocks"] -= quantity

    block_type = conv.name(block=section)["currency"]
    dbw.pay_money(chat_id, money_payment)
    dbw.add_block(chat_id, block_type, quantity)
    return uistr.get(chat_id, "Done")


# Every item is a bidirectional offer
# key is tuple of item names or types
# value is quantities in forward and backward directions
# NOTE: in second item of value, order is same as key
# example: ("coal", "investment_pass"): [[5, 3], [3, 5]]
# means 5 coal for 3 invpass, and 5 invpass for 3 coal
def flea_market_offer_prepare(chat_id, turn):
    flea_market_offers = {
        ("coal", "protections"): [[5, 4], [7, 10]],
        ("coal", "key"): [[10, 2], [15, 5]],
        ("coal", "dice"): [[6, 1], [5, 2]],
        ("coal", "crypto"): [[10, 50], [10, 100]],
        ("coal", "block"): [[5, 70], [5, 100]],
        ("coal", "investment_pass"): [[5, 3], [3, 5]],
        ("protections", "key"): [[10, 1], [70, 10]],
        ("protections", "dice"): [[15, 4], [10, 5]],
        ("protections", "crypto"): [[2, 10], [15, 100]],
        ("protections", "block"): [[5, 60], [2, 30]],
        ("protections", "investment_pass"): [[10, 5], [5, 5]],
        ("key", "dice"): [[10, 10], [1, 3]],
        ("key", "crypto"): [[1, 40], [1, 50]],
        ("key", "block"): [[3, 100], [1, 75]],
        ("key", "investment_pass"): [[30, 50], [2, 5]],
        ("dice", "crypto"): [[1, 20], [1, 50]],
        ("dice", "block"): [[1, 50], [2, 140]],
        ("dice", "investment_pass"): [[5, 10], [2, 5]],
        ("crypto", "block"): [[5, 15], [80, 80]],
        ("crypto", "investment_pass"): [[25, 1], [100, 5]],
        ("block", "investment_pass"): [[75, 5], [35, 5]]
    }
    block_type = None
    crypto_type = None
    rgen = random.Random(turn)
    offer = rgen.choice(list(flea_market_offers.keys()))
    quantities = flea_market_offers[offer].copy()
    if "block" in offer:
        block_type = rgen.choice(gut.list["block"])
        player_prod = best.get_production(chat_id)
        if offer[0] == "block":
            quantities[0][0] = max(
                quantities[0][0],
                best.get_market_blocks_for(
                    chat_id,
                    quantities[0][0] * player_prod // 60,
                    block_type
                )
            )
            ''' # Only requesting for more blocks to be put in, not getting them out!
            quantities[1][0] = max(
                quantities[1][0],
                best.get_market_blocks_for(
                    chat_id,
                    quantities[1][0] * player_prod // 60,
                    block_type
                )
            )
            '''
        else:
            quantities[1][1] = max(
                quantities[1][1],
                best.get_market_blocks_for(
                    chat_id,
                    quantities[1][1] * player_prod // 60,
                    block_type
                )
            )
            ''' # Only requesting for more blocks to be put in, not getting them out!
            quantities[0][1] = max(
                quantities[0][1],
                best.get_market_blocks_for(
                    chat_id,
                    quantities[0][1] * player_prod // 60,
                    block_type
                )
            )
            '''
    if "crypto" in offer:
        crypto_type = rgen.choice(gut.list["crypto"])

    return offer, quantities, block_type, crypto_type


def flea_market_get(chat_id, qty=1):
    data = {
        "hot": {"period_sec": (1 + (4 + 5 * 24 * 60) * 60)},
        "mid": {"period_sec": (15 + (1 + 12 * 60) * 60)},
        "ins": {"period_sec": (90 * 60)}
    }
    for sec in ["hot", "mid", "ins"]:
        data[sec]["turn"] = gut.time_s() // data[sec]["period_sec"]
        data[sec]["seconds_left"] = (
            data[sec]["period_sec"] * (data[sec]["turn"] + 1) - gut.time_s()
        )
        data[sec]["offer"], data[sec]["offer_quantities"], data[sec][
            "block_type"], data[sec]["crypto_type"] = flea_market_offer_prepare(
            chat_id, data[sec]["turn"])

    player_prod = best.get_production(chat_id)
    data["hot"]["price"] = player_prod // 20
    data["mid"]["price"] = player_prod // 33
    data["ins"]["price"] = player_prod // 100
    predicted_money_rate = best.get_section_money_rate(
        best.get_types_of(chat_id)["block"],
        after_variation=(-data["hot"]["price"] * qty)
    )
    if predicted_money_rate > .5:
        data["payment"] = "Market"
    else:
        data["payment"] = "Player"
    return data


# "direction" can be 0 or 1, the first and second item in the key tuple
def flea_market_deal(chat_id, offer, direction, qty):
    data = flea_market_get(chat_id, qty)
    item0 = data[offer]["offer"][direction]
    if item0 == "block":
        item0 = data[offer]["block_type"]
    elif item0 == "crypto":
        item0 = data[offer]["crypto_type"]
    item1 = data[offer]["offer"][(direction + 1) % 2]
    if item1 == "block":
        item1 = data[offer]["block_type"]
    elif item1 == "crypto":
        item1 = data[offer]["crypto_type"]

    items_to_spend = data[offer]["offer_quantities"][direction][direction] * qty
    items_to_get = data[offer]["offer_quantities"][direction][(direction + 1) % 2] * qty
    money_to_spend = data[offer]["price"] * qty

    if best.inventory_get(chat_id, item0) < items_to_spend:
        return uistr.get(chat_id, "error no item left")
    if data["payment"] == "Player":
        if not dbr.check_payment(chat_id, money_to_spend):
            return uistr.get(chat_id, "Insufficient balance")
        dbw.pay_money(chat_id, money_to_spend)
    else:
        _, money_limits = best.get_all_market_limits()
        highest_cur = gut.sort(money_limits)[0][0]
        section = conv.name(currency=highest_cur)["block"]
        best.market_give_money(section, money_to_spend)

    best.inventory_use(
        chat_id,
        item0,
        items_to_spend
    )
    best.inventory_give(
        chat_id,
        item1,
        items_to_get
    )
    return uistr.get(chat_id, "Done")


def change_language(chat_id, language_selected):
    r = dbw.change_language(chat_id, language_selected)
    if r != "Ok":
        return uistr.get(chat_id, "Internal error")
    return uistr.get(chat_id, "Done")


def set_random_nickname(chat_id):
    r = dbw.set_nickname(chat_id, gut.nickname_randomize(chat_id))
    if r != "Ok":
        return uistr.get(chat_id, "Internal error")
    return uistr.get(chat_id, "Done")


def get_nickname(chat_id):
    r = dbr.get_nickname(chat_id)
    if r == "-":
        return uistr.get(chat_id, "Internal error")
    else:
        return r


def set_nickname(chat_id, nick_data):
    if "badge_line" not in nick_data:
        cur_data = get_nickname(chat_id)
        if "badge_line" not in cur_data:
            nick_data["badge_line"] = ""
        else:
            nick_data["badge_line"] = cur_data["badge_line"]
    r = dbw.set_nickname(chat_id, nick_data)
    if r != "Ok":
        return uistr.get(chat_id, "Internal error")
    return uistr.get(chat_id, "Done")


# The game featured a money cap, now it doesn't,
# but the code isn't all clean yet, so this is kept just in case
def is_money_capped(chat_id):
    return False  # disables money cap
    data = load_main_menu(chat_id)["user"]
    if data["gear_level"] > 0:
        return False
    if check_balance_type(chat_id) == "new":
        player_balance = data["balance"]
    else:
        return False
    if player_balance == gut.money_cap(data["production_level"], 0,
                                       get_cap=True):
        return True
    return False


gear_cost_cache = {}


def gear_up_level_cost(base, to):
    level_cost = 0
    for g in range(base + 1, to + 1):
        if g not in gear_cost_cache:
            gear_cost_cache[g] = 0
            supergears = (g - 1) // 100
            gear_cost_cache[g] += 100 * 100 * (supergears ** ((supergears // 10) + 1)) * (supergears + 1) // 2
            if (g - 1) % 100 == 0:
                gear_cost_cache[g] += 50 * (supergears + 1)
            gear_cost_cache[g] += ((g - 1) % 100) * 100 * (supergears + 1)
        level_cost += gear_cost_cache[g]
    return level_cost


def can_gear_up(chat_id):
    user_data = dbr.login(chat_id)
    cur_gear_level = user_data["gear_level"]

    level_cost = gear_up_level_cost(cur_gear_level, cur_gear_level + 1)

    cur_prod_level = user_data["production_level"]

    if check_balance_type(chat_id) == "old":
        return False, level_cost
    if cur_prod_level <= level_cost:
        return False, level_cost
    return True, level_cost


def check_max_gear_up(chat_id):
    if not can_gear_up(chat_id)[0]:
        return 0
    user_data = dbr.login(chat_id)
    cur_gear_level = user_data["gear_level"]
    cur_prod_level = user_data["production_level"]
    if cur_gear_level < 30:
        return 0
    if user_data["membership"] == "ACB":
        return 0

    next_cost = gear_up_level_cost(cur_gear_level, cur_gear_level + 1)
    estimate = min(cur_prod_level // next_cost, 10000)

    done = False
    halving = True
    while not done:
        cost = gear_up_level_cost(cur_gear_level, cur_gear_level + estimate)
        if cost + 1 > cur_prod_level:
            done = False
            if halving:
                halfcost = gear_up_level_cost(
                    cur_gear_level,
                    cur_gear_level + estimate // 2
                )
                if halfcost + 1 > cur_prod_level:
                    estimate //= 2
                else:
                    halving = False
            estimate -= 1
        else:
            done = True
    return estimate


# When gearing up, all money goes to player's faction market
# This checks whether it would put too much money into it, reaching over 200%
# It returns the excess money, so we can tell the user how much to spend
# Deprecated
def gearup_market_absorption(chat_id):
    section = conv.name(membership=dbr.login(chat_id)["membership"])["block"]
    _, _, cur_money, _, money_limit, _ = market_upget(chat_id, section)
    cur_balance = dbr.login(chat_id)["balance"]
    return max(0, cur_money + cur_balance - money_limit * 2)


def gearup_money_to_market(chat_id):
    section = conv.name(membership=dbr.login(chat_id)["membership"])["block"]
    _, _, _, _, money_limit, _ = market_upget(chat_id, section)
    cur_balance = max(1, dbr.login(chat_id)["balance"])
    money_limit = max(1, money_limit)
    k = max(0, min(50,
                   math.log10(cur_balance) - math.log10(money_limit)
                   ))
    return int(
        cur_balance ** (1 - k / 100)
    )


def passes_season_gearup_limit(chat_id):
    season_data = best.season_upget()
    best.user_season_upget(chat_id)  # Almost no cost, checks for squash!
    if gut.time_s() < gut.season_to_ts(season_data[
       "current_season"]) + 60 * 60 * 24 * 14:
        return True
    user_data = dbr.login(chat_id)
    faction_ranking = tv.get_faction_ranking()
    if user_data["membership"] not in [
       faction_ranking[0][0], faction_ranking[1][0]]:
        return True
    if chat_id != season_data["faction"][user_data["membership"]][
       "top_contributor"]:
        return True
    return False


# This performs the soft-reset feature of the game
def gear_up(chat_id, new_membership):
    player_can, level_cost = can_gear_up(chat_id)
    if not player_can:
        return uistr.get(chat_id, "Gearup not available")
    if level_cost is None:
        return "WIP"
    # if gearup_market_absorption(chat_id) > 0:
    #    return uistr.get(chat_id, "Gearup not available")
    user_data = dbr.login(chat_id)
    if not passes_season_gearup_limit(chat_id):
        return uistr.get(chat_id, "Gearup season top")

    if new_membership == "ACB":
        if new_membership == user_data["membership"]:
            return uistr.get(chat_id, "Gearup ACB rule")

    # Donating money to market
    best.market_put_money(
        conv.name(membership=user_data["membership"])["block"],
        gearup_money_to_market(chat_id)
    )
    dbw.pay_money(chat_id, user_data["balance"])

    # Updating global production and member counts
    if new_membership != user_data["membership"]:
        cur_status = dbr.get_currencies_status()
        new_prod_for_old_memb = (
            cur_status[conv.name(membership=user_data["membership"])
                       ["currency"]] -
            best.get_production(chat_id))
        dbw.up_global_production(conv.name(membership=user_data["membership"])[
                                 "currency"], new_prod_for_old_memb)

        # adding badge
        nick_data = get_nickname(chat_id)
        if "badge_line" not in nick_data:
            nick_data["badge_line"] = ""
        nick_data["badge_line"] += conv.name(
            membership=user_data["membership"])["badge_letter"]
        set_nickname(chat_id, nick_data)

        new_prod_for_new_memb = (
            cur_status[conv.name(membership=new_membership)["currency"]] +
            best.get_production_for_level(
                chat_id, user_data["production_level"] - level_cost))
        dbw.up_global_production(conv.name(membership=new_membership)[
                                 "currency"], new_prod_for_new_memb)

        general_season_data = best.season_upget()
        if chat_id == general_season_data["faction"][user_data["membership"]][
                "top_contributor"]:
            general_season_data["faction"][user_data["membership"]][
                "top_contributor"] = 0
            dbw.up_season_info(general_season_data)
        dbw.member_switch(user_data["membership"],
                          new_membership,
                          dbr.get_member_counts()[user_data["membership"]] - 1,
                          dbr.get_member_counts()[new_membership] + 1)
        user_season_data = best.user_season_upget(chat_id)
        user_season_data["blocks_contributed"] = 0
        dbw.up_user_season_data(chat_id, user_season_data)

    else:
        old_production = best.get_production(chat_id)

        nick_data = get_nickname(chat_id)
        if "badge_line" not in nick_data:
            nick_data["badge_line"] = ""
        nick_data["badge_line"] += conv.name(
            membership=user_data["membership"])["badge_letter"]
        set_nickname(chat_id, nick_data)

        new_production = best.get_production_for_level(
            chat_id, user_data["production_level"] - level_cost)

        production_delta = new_production - old_production
        new_global_prod = dbr.get_currencies_status()[conv.name(
            membership=new_membership)["currency"]] + production_delta
        dbw.up_global_production(conv.name(membership=new_membership)[
                                 "currency"], new_global_prod)

    # Paying levels,upgrading gear and changing membership
    new_gear_level = user_data["gear_level"] + 1
    new_production_level = user_data["production_level"] - level_cost
    dbw.gear_up(chat_id, new_membership, new_gear_level, new_production_level)

    # Adding bonus blocks
    dbw.add_block(chat_id, conv.name(membership=new_membership)
                  ["currency"], count=level_cost)

    top_gear = multiplayer_info_upget(chat_id)["top_gear"]["level"]
    if new_gear_level <= top_gear - 10:
        best.inventory_give(chat_id, "mystery_item", 1)
        return uistr.get(chat_id, "found mystery item") + "\n"
    return uistr.get(chat_id, "Done")


def bulk_gear_up(chat_id, gears):
    if not can_gear_up(chat_id)[0]:
        return uistr.get(chat_id, "Gearup not available")
    # if gearup_market_absorption(chat_id) > 0:
    #    return uistr.get(chat_id, "Gearup not available")
    if not passes_season_gearup_limit(chat_id):
        return uistr.get(chat_id, "Gearup season top")

    user_data = dbr.login(chat_id)
    cur_gear_level = user_data["gear_level"]
    cur_prod_level = user_data["production_level"]
    if user_data["membership"] == "ACB":
        return uistr.get(chat_id, "Gearup ACB rule")

    level_cost = gear_up_level_cost(cur_gear_level, cur_gear_level + gears)
    if level_cost + 1 > cur_prod_level:
        return uistr.get(chat_id, "Gearup not available")

    # Donating money to market
    best.market_put_money(
        conv.name(membership=user_data["membership"])["block"],
        gearup_money_to_market(chat_id)
    )
    dbw.pay_money(chat_id, user_data["balance"])

    # Gearing up on same faction
    old_production = best.get_production(chat_id)
    nick_data = get_nickname(chat_id)
    nick_data["badge_line"] += gears * conv.name(
        membership=user_data["membership"])["badge_letter"]
    set_nickname(chat_id, nick_data)

    # update global production
    recalculate_global_production()

    # Paying levels and upgrading gear
    new_gear_level = cur_gear_level + gears
    new_production_level = cur_prod_level - level_cost
    dbw.gear_up(
        chat_id,
        user_data["membership"],
        new_gear_level,
        new_production_level
    )

    # Adding bonus blocks
    dbw.add_block(chat_id, conv.name(membership=user_data["membership"])
                  ["currency"], count=level_cost)

    top_gear = multiplayer_info_upget(chat_id)["top_gear"]["level"]
    if cur_gear_level < top_gear - 10:
        qty = min(new_gear_level, top_gear - 10) - cur_gear_level
        best.inventory_give(chat_id, "mystery_item", qty)
        return uistr.get(chat_id, "found mystery items").format(
            qty=qty
        ) + "\n"
    return uistr.get(chat_id, "Done")


# Calculates all the benefits/changes if the player gears up
def gearup_effects(chat_id):
    _, level_cost = can_gear_up(chat_id)
    user_data = dbr.login(chat_id)

    effects = {}
    effects["Prod_level"] = (
        user_data["production_level"],
        user_data["production_level"] - level_cost)
    effects["hourly_production_rate"] = (
        gut.hourly_production_rate_of_level(
            user_data["production_level"]),
        gut.hourly_production_rate_of_level(
            max(0, user_data["production_level"] - level_cost))
    )
    effects["bonus_blocks"] = level_cost
    effects["block_rate"] = (
        gut.gear_blocks(user_data["nickname"]["badge_line"]),
        {conv.name(membership=user_data["membership"])["currency"]:
            gut.gear_blocks(user_data["nickname"]["badge_line"] + conv.name(
                membership=user_data["membership"])["badgemoji"])[
            conv.name(membership=user_data["membership"])["currency"]]}
    )
    if user_data["gear_level"] % 100 != 99:
        effects["new_badge"] = conv.name(
            membership=user_data["membership"])["badgemoji"]
    else:
        new_supergear = (user_data["gear_level"] + 1) // 100
        if new_supergear % 3 == 1:
            effects["new_superbadge"] = "💍"
        elif new_supergear % 3 == 2:
            effects["new_superbadge"] = "💍 → 👑"
        else:
            effects["new_superbadge"] = "👑 → ???"
        effects["super_multiplier"] = 1 + 2 * new_supergear
    return effects


# Exchange, Discount and Bonus screen info
def edb_screen(chat_id, money_qty, block_qty, faction):
    if faction not in gut.list["membership"]:
        faction = get_membership(chat_id)
    base_currency = conv.name(membership=faction)["currency"]
    base_block_type = conv.name(membership=faction)["block"]

    conversions = {}
    for to_cur in gut.list["currency"]:
        conversions[to_cur] = best.exchange_cur(
            money_qty, base_currency, to_cur)

    discounted = best.apply_discount(money_qty, base_currency)
    bonussed = best.apply_block_bonus(block_qty, base_block_type)

    player_prod = best.get_production(chat_id)
    prices = {}

    prices["market"] = best.get_market_final_price(chat_id, base_block_type)

    prices["IP_capitalist"] = best.apply_discount(
        (player_prod * 3) * 100, chat_id=chat_id) // best.apply_block_bonus(
        (4) * 100, chat_id=chat_id)

    currencies_status = dbr.get_currencies_status()
    cur_order = [(i, currencies_status[i]) for i in currencies_status]
    cur_order = sorted(cur_order, key=lambda item: item[1], reverse=True)
    denominators = {}
    for i in range(len(cur_order)):
        denominators[cur_order[i][0]] = i + 1
    player_cur = best.get_types_of(chat_id)["currency"]
    faction_denominator = denominators[player_cur]
    prices["IP_socialist"] = best.apply_discount(
        (player_prod * 3 / faction_denominator) * 100, chat_id=chat_id
    ) // best.apply_block_bonus((4) * 100, chat_id=chat_id)

    prices["GSRF_nobonus"] = best.apply_discount(
        (player_prod * 45 // 60) * 100, chat_id=chat_id
    ) // best.apply_block_bonus((1) * 100, chat_id=chat_id)
    prices["GSRF_withbonus"] = best.apply_discount(
        (player_prod * 45 // 60) * 100, chat_id=chat_id
    ) // best.apply_block_bonus((1.1) * 100, chat_id=chat_id)
    prices["GSRF_withbonus_S"] = best.apply_discount(
        (player_prod * 45 // 60) * 100, chat_id=chat_id
    ) // best.apply_block_bonus((1.3) * 100, chat_id=chat_id)
    return conversions, discounted, bonussed, prices


mystery_item_prizes = {
    "blocks_self": [50, 100],
    "blocks_random": [80, 120],
    "blocks_eachtype": [10, 15],
    "money_prodh": [5, 20],
    "item_coal": [5, 15],
    "item_protections": [5, 10],
    "item_keys": [2, 5],
    "item_dice": [2, 5],
    "crypto_random": [50, 100],
    "crypto_each": [10, 25],
    "item_investment_pass": [10, 30],
    "item_mysteryitem": [2, 5]  # midpoint should be below 8
}


def get_available_prizes(chat_id):
    best.minis_player_data_init(chat_id)
    prizes = mystery_item_prizes.copy()
    player_OMdata = dbr.mini_get_player(chat_id, "Ore Miner")
    if len(player_OMdata) == 0:
        prizes.pop("item_protections")
    player_CPdata = dbr.mini_get_player(chat_id, "Coinopoly")
    if len(player_CPdata) == 0:
        prizes.pop("crypto_random")
        prizes.pop("crypto_each")
    return prizes


def mystery_item_info(chat_id):
    available = best.inventory_get(chat_id, "mystery_item")
    info = get_available_prizes(chat_id)
    info["money"] = [best.get_production(chat_id) * h
                     for h in info["money_prodh"]]
    return available, info


def use_mystery_item(chat_id, qty=1):
    if qty == "all":
        qty = best.inventory_get(chat_id, "mystery_item")
    if not best.inventory_use(chat_id, "mystery_item", qty) or qty == 0:
        return uistr.get(chat_id, "error no item left")

    message = ''
    notifications = []
    prizes = {}
    for _ in range(qty):
        prize = random.choice(list(get_available_prizes(chat_id).keys()))
        quantity = random.randint(
            mystery_item_prizes[prize][0],
            mystery_item_prizes[prize][1]
        )
        if prize not in prizes:
            prizes[prize] = []
        prizes[prize].append(quantity)

    if "blocks_eachtype" in prizes:
        dbr.login(chat_id)
        quantity = {i: 0 for i in gut.list["block"]}
        if "blocks_self" in prizes:
            type = best.get_types_of(chat_id)["block"]
            quantity[type] += sum(prizes["blocks_self"])
        if "blocks_random" in prizes:
            for i in range(len(prizes["blocks_random"])):
                type = random.choice(gut.list["block"])
                quantity[type] += prizes["blocks_random"][i]

        for type in gut.list["block"]:
            quantity[type] += sum([random.randint(
                mystery_item_prizes[prize][0],
                mystery_item_prizes[prize][1]
            ) for _ in range(len(prizes["blocks_eachtype"]))
            ])
            dbw.add_block(
                chat_id,
                conv.name(block=type)["currency"],
                count=quantity[type]
            )
        message += uistr.get(chat_id, "mystery prize blocks each").format(
            mUSDmb=quantity["mUSDmb"],
            mEmb=quantity["mEmb"],
            mYmb=quantity["mYmb"],
            mAUDmb=quantity["mAUDmb"],
            mBRmb=quantity["mBRmb"],
            mIRmb=quantity["mIRmb"],
            mAmb=quantity["mAmb"]
        ) + "\n"
    else:
        if "blocks_self" in prizes:
            type = best.get_types_of(chat_id)["block"]
            quantity = sum(prizes["blocks_self"])
            dbw.add_block(
                chat_id,
                best.get_types_of(chat_id)["currency"],
                count=quantity
            )
            message += uistr.get(chat_id, "mystery prize blocks 1type").format(
                qty=quantity,
                type=type
            ) + "\n"
        if "blocks_random" in prizes:
            dbr.login(chat_id)
            quantity = {i: 0 for i in gut.list["block"]}
            for i in range(len(prizes["blocks_random"])):
                type = random.choice(gut.list["block"])
                quantity[type] += prizes["blocks_random"][i]
            for type in quantity:
                if quantity[type] > 0:
                    dbw.add_block(
                        chat_id,
                        conv.name(block=type)["currency"],
                        count=quantity[type]
                    )
                    message += uistr.get(chat_id, "mystery prize blocks 1type").format(
                        qty=quantity[type],
                        type=type
                    ) + "\n"

    if "money_prodh" in prizes:
        quantity = int(best.get_production(chat_id) * sum(prizes["money_prodh"]))
        cur_sym = best.get_types_of(chat_id)["symbol"]
        dbw.give_money(chat_id, quantity)
        message += uistr.get(chat_id, "mystery prize money").format(
            qty=put.pretty(quantity),
            sym=cur_sym
        ) + "\n"
    if "item_coal" in prizes:
        quantity = sum(prizes["item_coal"])
        best.inventory_give(chat_id, "coal", quantity)
        message += uistr.get(chat_id, "mystery prize coal").format(
            qty=quantity
        ) + "\n"
    if "item_protections" in prizes:
        quantity = sum(prizes["item_protections"])
        player_OMdata = dbr.mini_get_player(chat_id, "Ore Miner")
        player_OMdata["protections"] += quantity
        best.mini_up_player(chat_id, "Ore Miner", player_OMdata)
        message += uistr.get(chat_id, "mystery prize protections").format(
            qty=quantity
        ) + "\n"
    if "item_keys" in prizes:
        quantity = sum(prizes["item_keys"])
        best.inventory_give(chat_id, "key", quantity)
        message += uistr.get(chat_id, "mystery prize key").format(
            qty=quantity
        ) + "\n"
    if "item_dice" in prizes:
        quantity = sum(prizes["item_dice"])
        best.inventory_give(chat_id, "dice", quantity)
        message += uistr.get(chat_id, "mystery prize dice").format(
            qty=quantity
        ) + "\n"
    if "crypto_each" in prizes:
        player_CPdata = dbr.mini_get_player(chat_id, "Coinopoly")
        quantity = {i: 0 for i in gut.list["crypto"]}
        if "crypto_random" in prizes:
            for i in range(len(prizes["crypto_random"])):
                sel_type = random.choice(gut.list["crypto"])
                quantity[sel_type] += prizes["crypto_random"][i]
        for type in gut.list["crypto"]:
            quantity[type] += sum([random.randint(
                mystery_item_prizes[prize][0],
                mystery_item_prizes[prize][1]
            ) for _ in range(len(prizes["crypto_each"]))
            ])
            player_CPdata["Coins"][type] = float.hex(
                float.fromhex(player_CPdata["Coins"][type]) + quantity[type]
            )
        best.mini_up_player(chat_id, "Coinopoly", player_CPdata)
        message += uistr.get(
            chat_id, "mystery prize crypto each").format(
            Solana=quantity["Solana"],
            Litecoin=quantity["Litecoin"],
            Polkadot=quantity["Polkadot"],
            Terra=quantity["Terra"],
            BitTorrent=quantity["BitTorrent"],
            Shiba=quantity["Shiba"],
            Dogecoin=quantity["Dogecoin"],
            Filecoin=quantity["Filecoin"],
            IdleCoin=quantity["IdleCoin"],
            Bitcoin=quantity["Bitcoin"],
            Ada=quantity["Ada"],
            Tether=quantity["Tether"],
            Ether=quantity["Ether"]
        ) + "\n"
    elif "crypto_random" in prizes:
        quantity = {i: 0 for i in gut.list["crypto"]}
        for i in range(len(prizes["crypto_random"])):
            type = random.choice(gut.list["crypto"])
            quantity[type] += prizes["crypto_random"][i]
        player_CPdata = dbr.mini_get_player(chat_id, "Coinopoly")
        for type in quantity:
            if quantity[type] > 0:
                player_CPdata["Coins"][type] = float.hex(
                    float.fromhex(player_CPdata["Coins"][type]) + quantity[type]
                )
                message += uistr.get(
                    chat_id, "mystery prize crypto random").format(
                    coin_type=type,
                    coins=quantity[type]
                ) + "\n"
        best.mini_up_player(chat_id, "Coinopoly", player_CPdata)

    if "item_investment_pass" in prizes:
        quantity = sum(prizes["item_investment_pass"])
        best.inventory_give(chat_id, "investment_pass", quantity)
        message += uistr.get(chat_id, "mystery prize investment_pass").format(
            qty=quantity
        ) + "\n"
    if "item_mysteryitem" in prizes:
        quantity = sum(prizes["item_mysteryitem"])
        best.inventory_give(chat_id, "mystery_item", quantity)
        message += uistr.get(chat_id, "mystery prize mystery_item").format(
            qty=quantity
        ) + "\n"
        dn_data_agencies = dbr.mini_get_general("Daily News")["Agencies"]
        player_agency = None
        for ag in dn_data_agencies:
            if chat_id in dn_data_agencies[ag]:
                player_agency = ag
                break
        if player_agency:
            if len(dn_data_agencies[player_agency]) >= int(player_agency.split("_")[0]):
                if player_agency.split("_")[0] == "2":
                    dna_quantity = int(quantity / 2.0 + .5)
                else:
                    dna_quantity = (quantity // 4) + 1
                for member_id in dn_data_agencies[player_agency]:
                    if chat_id == member_id:
                        continue
                    best.inventory_give(member_id, "mystery_item", dna_quantity)
                    notifications.append({
                        "chat_id": member_id,
                        "message": uistr.get(member_id, "DN Agencies notify jackpot").format(
                            sender=uistr.nickname(member_id, chat_id, dbr.get_nickname(chat_id)),
                            quantity=dna_quantity
                        )
                    })

    return message, notifications


def get_season_leaderboard(chat_id):
    general_sd = best.season_upget()
    player_faction = get_membership(chat_id)
    user_sd = best.user_season_upget(chat_id)
    block_data = {}
    for fact in general_sd["faction"]:
        block_data[fact] = general_sd["faction"][fact]["blocks_used"]
    sorted = gut.sort(block_data)
    ordered_data = []
    for element in sorted:
        top_contr_nick = "-"
        top_contr_blocks = 0
        if general_sd["faction"][element[0]]["top_contributor"] > 0:
            top_contr_nick = uistr.nickname(
                chat_id,
                general_sd["faction"][element[0]]["top_contributor"],
                get_nickname(
                    general_sd["faction"][element[0]]["top_contributor"]
                )
            )
            top_contr_blocks = best.user_season_upget(
                general_sd["faction"][element[0]]["top_contributor"]
            )["blocks_contributed"]
        ordered_data.append({
            "faction": element[0],
            "blocks": element[1],
            "top_contributor_nick": top_contr_nick,
            "top_contributor_id": general_sd["faction"][
                element[0]]["top_contributor"],
            "top_contributor_blocks": top_contr_blocks
        })
        if element[0] == player_faction:
            ordered_data[-1]["viewer_contribution"] = user_sd[
                "blocks_contributed"]
    season_name = uistr.get(chat_id, "season " + str(
        general_sd["current_season"][0])) + " " + str(
        general_sd["current_season"][2:]) + "\n("
    seconds_nexts = gut.time_till_next_season()
    days_nexts = seconds_nexts // (60 * 60 * 24)
    hours_nexts = (seconds_nexts // (60 * 60)) % 24
    minutes_nexts = (seconds_nexts // 60) % 60
    seconds_nexts = seconds_nexts % 60
    if days_nexts >= 7:
        season_name += "-" + str(days_nexts) + "d"
    elif days_nexts >= 1:
        season_name += "-" + str(days_nexts) + "d" + str(hours_nexts) + "h"
    elif hours_nexts >= 1:
        season_name += "-" + str(hours_nexts) + "h" + str(minutes_nexts) + "m"
    else:
        season_name += "-0h" + str(
            minutes_nexts) + "m" + str(seconds_nexts) + "s"
    season_name += ")"
    return season_name, ordered_data


def get_season_name_at_month(chat_id, delta_month):
    struct_t = time.gmtime(gut.time_s())
    month = (struct_t.tm_mon - 1 + delta_month) % 12
    year = struct_t.tm_year + (struct_t.tm_mon - 1 + delta_month) // 12
    if month < 3:
        season = uistr.get(chat_id, "season 1")
    elif month < 6:
        season = uistr.get(chat_id, "season 2")
    elif month < 9:
        season = uistr.get(chat_id, "season 3")
    else:
        season = uistr.get(chat_id, "season 4")
    return season + " " + str(year)


def get_faction_badgeline(faction):
    return gut.faction_badge_line(
        best.season_upget()["faction"][faction]["current_badge"]
    )


def recalculate_global_production():
    multi_data = dbr.get_multiplayer_info()

    new_global_productions = {i: 0 for i in gut.list["currency"]}
    for chat_id in list(multi_data["players_activity"].keys()):
        user_data = load_main_menu(chat_id)
        player_production = best.get_production(chat_id)
        type = conv.name(membership=user_data["user"]["membership"])[
            "currency"]
        new_global_productions[type] += player_production
    for type in new_global_productions:
        dbw.up_global_production(type, new_global_productions[type])

    multi_data["global_production_timestamp"] = gut.time_s()
    dbw.up_multiplayer_info(multi_data)


def get_valve_screen_data(chat_id):
    player_valves = best.get_valves(chat_id)
    player_level = dbr.login(chat_id)["production_level"]
    level_after_opening_valves = best.get_level_opening_valves(chat_id)
    all_valve_values = best.get_all_valve_values()
    user_currency = best.get_types_of(chat_id)["currency"]
    op_price = best.get_valve_operation_price(chat_id)

    can_gear_normally, gear_level_cost = can_gear_up(chat_id)
    can_gear_after_opening = level_after_opening_valves > gear_level_cost

    max_valve_closing = best.get_max_valve_closing(chat_id)
    return (
        player_valves, player_level, level_after_opening_valves, all_valve_values,
        user_currency, op_price, can_gear_normally, gear_level_cost, can_gear_after_opening,
        max_valve_closing
    )


def can_operate_valves(chat_id):
    if best.get_valves(chat_id) > 0:
        return True
    if best.get_max_valve_closing(chat_id) > 0:
        return True
    return False


def operate_valves(chat_id, op):
    user_data = dbr.login(chat_id)
    cur_valves = best.get_valves(chat_id)
    valve_value = best.get_valve_value(chat_id)
    price = best.get_valve_operation_price(chat_id)
    if not dbr.check_payment(chat_id, price):
        return uistr.get(chat_id, "Insufficient balance")
    cur_level = user_data["production_level"]

    if op == "close":
        valve_closing = best.get_max_valve_closing(chat_id)
        levels_frozen = valve_closing * valve_value
        if cur_level - levels_frozen < (10**6):
            return "Uh?"
        dbw.set_valves(chat_id, cur_valves + valve_closing, cur_level - levels_frozen)
    elif op == "open":
        level_unfrozen = cur_valves * valve_value
        dbw.set_valves(chat_id, 0, cur_level + level_unfrozen)

    dbw.pay_money(chat_id, price)

    best.market_put_money(
        conv.name(membership=user_data["membership"])["block"],
        gearup_money_to_market(chat_id)
    )
    # Re-getting user data after first payment, just to be sure
    dbw.pay_money(chat_id, dbr.login(chat_id)["balance"])

    recalculate_global_production()
    return uistr.get(chat_id, "Done")


# admin actions ====================================
def admin_action(actionstr):
    if actionstr == "delch":
        dbw.ch.active_users = {}
        dbw.ch.market_data = {}
        dbw.ch.global_production = {}
        dbw.ch.events_data = {}
        dbw.ch.leaderboard_data = {}
        dbw.ch.member_count = {}
        dbw.ch.mini_general = {}
        dbw.ch.mini_player = {}
        dbw.ch.multiplayer_info = {}
        dbw.ch.season_info = {}
        return "Done"
    if "reglob" in actionstr:
        # pretty sure this will fail when too many players get processed
        if "\n" in actionstr:
            chat_ids = [int(id)
                        for id in actionstr[len("reglob\n"):].split('\n')]
            new_global_productions = {i: 0 for i in gut.list["currency"]}
            for chat_id in chat_ids:
                data = load_main_menu(chat_id)
                if dbr.login(chat_id)["last_login_timestamp"] >= 1631265995:
                    player_production = best.get_production(chat_id)
                    type = conv.name(membership=data["user"]["membership"])[
                        "currency"]
                    new_global_productions[type] += player_production
            for type in new_global_productions:
                dbw.up_global_production(type, new_global_productions[type])
            return "Done, " + str(new_global_productions)
        else:
            recalculate_global_production()
            return "Done"
    if "login" in actionstr:  # used to fix wrong stuff
        if len(actionstr) < len("login") + 2:
            return "Where's the ID??"
        chat_id = int(actionstr[len("login "):])
        res = check_account(chat_id)
        if res["status"] == "Not Activated":
            return "This account doesn't exist!"
        data = load_main_menu(chat_id)["user"]
        if check_balance_type(chat_id) == "old":
            upgrade_to_single_balance(chat_id)
            return "Player upgraded to single balance"
        if data["nickname"] != "-":
            if "badge_line" in data["nickname"]:
                if data["gear_level"] != len(data["nickname"]["badge_line"]):
                    data["gear_level"] = len(data["nickname"]["badge_line"])
                    # just sets the changed gear level
                    dbw.set_specific(
                        chat_id, "N", "gear_level", data["gear_level"])
                    return "Fixed gear level"
        return "Done"
    if actionstr == "restock":
        for section in gut.list["block"]:
            market_restock(section, pcent=75)
        return "Done"
    if actionstr == "markres":
        for section in gut.list["block"]:
            market_reset(section)
        return "Done"
    if actionstr == "°":
        market_general_update(force_target=True)
        return "Temperature: " + str(
            best.get_market_temperature()) + "\nImpulse: " + str(
            best.get_market_impulse()) + "\nTarget money/block Rate: " + str(
            target_storage_rate)
    if actionstr == "active":
        data = dbr.get_multiplayer_info()
        message = "Active players\n"
        for pid in data["players_activity"]:
            pdata = load_main_menu(pid)["user"]
            message += "/view@" + pid + " " + put.readable(
                pdata["gear_level"]) + " - " + pdata[
                "account_creation_datastr"] + "\n"
        return message
    return "Wrong command"
