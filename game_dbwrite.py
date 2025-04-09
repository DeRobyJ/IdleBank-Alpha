import dynamodb_interface as di
import game_util as gut
import conversions as conv
import db_chdata as ch
import copy


def add_block(chat_id, type, count=1, logtime=0):
    if chat_id not in ch.active_users:
        return "Abort"
    print("dbw", chat_id, "add_block")
    new_blocks = ch.active_users[chat_id]["blocks_" + type] + count
    di.item_update(
        di.pre_user,
        {'key': {"S": str(chat_id)}}, "blocks_" + type, {"N": new_blocks})
    ch.active_users[chat_id]["blocks_" + type] = new_blocks

    if logtime > 0:
        print(":: updating login time")
        di.item_update(
            di.pre_user,
            {'key': {"S": str(chat_id)}},
            "last_login_timestamp", {"N": logtime})
        ch.active_users[chat_id]["last_login_timestamp"] = logtime
    return "Ok"


def pay_block(chat_id, type, qty=1):
    if chat_id not in ch.active_users:
        return "Abort"
    if ch.active_users[chat_id]["blocks_" + type] < qty:
        return "Abort"
    print("dbw", chat_id, "pay_block")
    new_blocks = ch.active_users[chat_id]["blocks_" + type] - qty

    di.item_update(
        di.pre_user,
        {'key': {"S": str(chat_id)}}, "blocks_" + type, {"N": new_blocks})
    ch.active_users[chat_id]["blocks_" + type] = new_blocks

    return "Ok"


def soft_reset(chat_id, data):
    print("dbw", chat_id, "soft_reset")
    for type in gut.list["currency"]:
        di.item_update(
            di.pre_user,
            {'key': {"S": str(chat_id)}},
            "blocks_" + type, {"N": data["blocks"][type]})
        ch.active_users[chat_id]["blocks_" + type] = data["blocks"][type]

    di.item_update(
        di.pre_user,
        {'key': {"S": str(chat_id)}},
        "saved_balance", {"N": data["balance"]})
    ch.active_users[chat_id]["saved_balance"] = data["balance"]

    di.item_update(
        di.pre_user,
        {'key': {"S": str(chat_id)}},
        "balance_timestamp", {"N": data["balance_timestamp"]})
    ch.active_users[chat_id]["balance_timestamp"] = data["balance_timestamp"]

    di.item_update(
        di.pre_user,
        {'key': {"S": str(chat_id)}},
        "production_level", {"N": data["production_level"]})
    ch.active_users[chat_id]["production_level"] = data["production_level"]

    di.item_update(
        di.pre_user,
        {'key': {"S": str(chat_id)}},
        "last_login_timestamp", {"N": data["last_login_timestamp"]})
    ch.active_users[chat_id]["last_login_timestamp"] = (
        data["last_login_timestamp"])

    di.item_update(
        di.pre_user,
        {'key': {"S": str(chat_id)}},
        "gear_level", {"N": data["gear_level"]})
    ch.active_users[chat_id]["gear_level"] = data["gear_level"]

    set_nickname(chat_id, data["nickname"])


def set_specific(chat_id, type, field, data):
    print("dbw", chat_id, "set_specific", type, field)
    di.item_update(di.pre_user, {'key': {
                   "S": str(chat_id)}}, field, {type: data})
    ch.active_users[chat_id][field] = data


def up_settings(chat_id, settings):
    flag = gut.settings_pack(settings)
    set_specific(chat_id, "N", "settings", flag)


def give_money(chat_id, amount, type=None):
    if chat_id not in ch.active_users:
        return "Abort"
    print("dbw", chat_id, "give_money or pay_money")
    # consolidate_balance(chat_id)
    if type:
        new_money = ch.active_users[chat_id]["cur_" + type] + amount
        di.item_update(di.pre_user, {'key': {
                       "S": str(chat_id)}}, "cur_" + type, {"N": new_money})
        ch.active_users[chat_id]["cur_" + type] = new_money
    else:
        new_money = ch.active_users[chat_id]["saved_balance"] + amount
        di.item_update(di.pre_user, {'key': {"S": str(
            chat_id)}}, "saved_balance", {"N": new_money})
        ch.active_users[chat_id]["saved_balance"] = new_money
    return "Ok"


def pay_money(chat_id, amount, type=None):
    return give_money(chat_id, -amount, type)


def up_money_printer(chat_id, costs, levels=1):
    if chat_id not in ch.active_users:
        return "Abort"

    print("dbw", chat_id, "up_money_printer", levels, "levels")
    user_cur_name = conv.name(
        membership=ch.active_users[chat_id]["membership"])["currency"]

    consolidate_balance(chat_id)
    pay_money(chat_id, costs["Money"])

    new_blocks = ch.active_users[chat_id]["blocks_" +
                                          user_cur_name] - costs["Blocks"]
    print(":: updating number of blocks")
    di.item_update(di.pre_user, {'key': {"S": str(
        chat_id)}}, "blocks_" + user_cur_name, {"N": new_blocks})
    ch.active_users[chat_id]["blocks_" + user_cur_name] = new_blocks

    print(":: updating balance ts")
    new_time = gut.time_s()
    di.item_update(di.pre_user, {'key': {"S": str(
        chat_id)}}, "balance_timestamp", {"N": new_time})
    ch.active_users[chat_id]["balance_timestamp"] = new_time

    print(":: updating production level")
    di.item_update(
        di.pre_user, {'key': {"S": str(chat_id)}}, "production_level",
        {"N": ch.active_users[chat_id]["production_level"] + levels})
    ch.active_users[chat_id]["production_level"] += levels

    return "Ok"


def consolidate_balance(chat_id):
    if chat_id not in ch.active_users:
        return "Abort"
    print("dbw", chat_id, "consolidate_balance")
    if "saved_balance" not in ch.active_users[chat_id]:
        ch.active_users[chat_id]["saved_balance"] = 0
    nick_data = gut.nickname_unpack(ch.active_users[chat_id]["nickname"])
    if "badge_line" not in nick_data:
        badge_line = ""
    else:
        badge_line = nick_data["badge_line"]
    player_balance = gut.balance(
        ch.active_users[chat_id]["production_level"],
        ch.active_users[chat_id]["gear_level"],
        badge_line,
        ch.active_users[chat_id]["saved_balance"],
        ch.active_users[chat_id]["balance_timestamp"]
    )
    if player_balance < 0:
        player_balance = 0
        print("Warning: Negative balance")
    print(":: updating balance")
    di.item_update(di.pre_user, {'key': {"S": str(
        chat_id)}}, "saved_balance", {"N": player_balance})
    ch.active_users[chat_id]["saved_balance"] = player_balance

    print(":: updating balance timestamp")
    new_time = gut.time_s()
    di.item_update(di.pre_user, {'key': {"S": str(
        chat_id)}}, "balance_timestamp", {"N": new_time})
    ch.active_users[chat_id]["balance_timestamp"] = new_time

    return "Ok"


def up_global_production(cur, new_hourly_production_rate):
    print("dbw", cur, "up_global_production")
    di.item_update(
        di.pre_board, {'key': {"S": cur}}, "hourly_production_rate",
        {"S": str(new_hourly_production_rate)})
    ch.global_production[cur] = new_hourly_production_rate

    return "Ok"


def up_leaderboard(cur, new_raw_data):
    print("dbw", cur, "up_leaderboard")
    di.item_update(di.pre_board, {
                   'key': {"S": cur}}, "leaderboard", {"NS": new_raw_data})
    ch.leaderboard_data[cur] = new_raw_data

    return "Ok"


def up_multiplayer_info(new_data):
    print("dbw", "up_multiplayer_info")
    if len(ch.multiplayer_info) == 0 or len(new_data) == 0:
        return "Abort"
    for key in ["players_activity", "top_gear", "top_production"]:
        if key not in new_data:
            new_data[key] = ch.multiplayer_info[key]
    di.ezput_item(di.pre_board, new_data)
    ch.multiplayer_info = new_data
    return "Ok"


def up_season_info(new_data):
    print("dbw", "up_season_info")
    if len(ch.season_info) == 0 or len(new_data) == 0:
        return "Abort"
    di.ezput_item(di.pre_board, new_data)
    ch.season_info = new_data
    return "Ok"


def market_update(section, data):
    print("dbw", section, "market_update")
    di.ezput_item(di.pre_market, data)
    ch.market_data[section] = data
    return "Ok"


def activate_account(chat_id, membership, new_member_count):
    if chat_id not in ch.active_users:
        return "Abort"
    if ch.active_users[chat_id]:
        if "account_status" in ch.active_users[chat_id]:
            if ch.active_users[chat_id]["account_status"] != "Not Activated":
                return "Abort"
    else:
        ch.active_users[chat_id] = {}
    print("dbw", chat_id, "activate_account")

    for attr, val in gut.new_account_data(membership):
        di.item_update(di.pre_user, {'key': {
                       "S": str(chat_id)}}, attr, {"N": val})
        ch.active_users[chat_id][attr] = val
    di.item_update(di.pre_user, {'key': {"S": str(
        chat_id)}}, "account_status", {"S": "Activated"})
    ch.active_users[chat_id]["account_status"] = "Activated"
    if "language" not in ch.active_users[chat_id]:
        di.item_update(di.pre_user, {'key': {
                       "S": str(chat_id)}}, "language", {"S": "English"})
        ch.active_users[chat_id]["language"] = "English"
    di.item_update(di.pre_user, {'key': {
                   "S": str(chat_id)}}, "nickname", {"S": "-"})
    ch.active_users[chat_id]["nickname"] = "-"
    di.item_update(di.pre_user, {'key': {
                   "S": str(chat_id)}}, "membership", {"S": membership})
    ch.active_users[chat_id]["membership"] = membership

    currency = conv.name(membership=membership)["currency"]
    di.item_update(di.pre_board, {"key": {"S": currency}}, "members", {
                   "N": new_member_count})
    ch.member_count[membership] = new_member_count

    return "Ok"


def change_language(chat_id, language_selected):
    if chat_id not in ch.active_users:
        return "Abort"
    print("dbw", chat_id, "change_language")
    di.item_update(
        di.pre_user, {'key': {"S": str(chat_id)}},
        "language", {"S": language_selected})
    if chat_id not in ch.active_users:
        ch.active_users[chat_id] = {}
    if not ch.active_users[chat_id]:
        ch.active_users[chat_id] = {}
    ch.active_users[chat_id]["language"] = language_selected
    return "Ok"


def set_nickname(chat_id, nick_data):
    print("dbw", chat_id, "set_nickname")
    nick_ns = gut.nickname_pack(nick_data)
    di.item_update(di.pre_user, {'key': {
                   "S": str(chat_id)}}, "nickname", {"M": nick_ns})
    ch.active_users[chat_id]["nickname"] = nick_ns
    return "Ok"


def up_user_season_data(chat_id, data):
    print("dbw", chat_id, "up_user_season_data")
    data_packed = gut.user_season_data_pack(data)
    if chat_id not in ch.active_users:
        return "Abort"
    di.item_update(di.pre_user, {'key': {
                   "S": str(chat_id)}}, "season_data", {"M": data_packed})
    ch.active_users[chat_id]["season_data"] = data_packed
    return "Ok"


def up_event_count(chat_id, event_name, new_count):
    if chat_id not in ch.events_data:
        "Abort"
    if event_name not in ch.events_data[chat_id]:
        "Abort"
    print("dbw", chat_id, "up_event_count")
    di.item_update(di.pre_event, {'key': {
                   "S": str(chat_id)}}, event_name, {"N": new_count})
    ch.events_data[chat_id][event_name] = new_count
    return "Ok"


def mini_up_general(game_data):
    if game_data["key"] not in ch.mini_general:
        return "Abort"
    print("dbw", game_data["key"], "mini_up_general")

    put_data = copy.deepcopy(game_data)
    if put_data["key"] == "Coinopoly":
        for coin in put_data["Money"]:
            put_data["Money"][coin] = str(put_data["Money"][coin])

    di.ezput_item(di.pre_minis, put_data)
    ch.mini_general[game_data["key"]] = game_data
    return "Ok"


def mini_up_player(chat_id, game_name, player_data):
    if chat_id not in ch.mini_player:
        return "Abort"
    print("dbw", chat_id, game_name, "mini_up_player")
    ch.mini_player[chat_id][game_name] = player_data

    minis_data_copy = copy.deepcopy(ch.mini_player[chat_id])
    item = {"key": chat_id}
    if len(minis_data_copy["inventory"]) > 0:
        item = {**item,
                **{"in::" + i: minis_data_copy["inventory"][i]
                   for i in ["coal", "dice", "key", "mystery_item", "investment_pass"]}
                }
    if len(minis_data_copy["Daily News"]) > 0:
        item = {**item,
                **{"DN::" + i: minis_data_copy["Daily News"][i]
                   for i in ["vote_timestamp"]}
                }
    if len(minis_data_copy["Ore Miner"]) > 0:
        if "mined_mUSDmb" not in minis_data_copy["Ore Miner"]:
            minis_data_copy["Ore Miner"]["mined_mUSDmb"] = (
                minis_data_copy["Ore Miner"].pop("mined_mDmb"))
        if "mined_mAUDmb" not in minis_data_copy["Ore Miner"]:
            for block in ["mined_mAUDmb", "mined_mBRmb",
                          "mined_mIRmb", "mined_mAmb"]:
                minis_data_copy["Ore Miner"][block] = 0
        item = {**item,
                **{"OM::" + i: minis_data_copy["Ore Miner"][i]
                   for i in ["record_level",
                             "money_earnings",
                             "mined_mUSDmb",
                             "mined_mEmb",
                             "mined_mYmb",
                             "mined_mAUDmb",
                             "mined_mBRmb",
                             "mined_mIRmb",
                             "mined_mAmb",
                             "protections"]}
                }
        for field in ["OM::money_earnings"]:
            item[field] = str(item[field])
    if len(minis_data_copy["Coinopoly"]) > 0:
        item = {**item,
                **{"CP::" + i: minis_data_copy["Coinopoly"][i]
                   for i in ["Coins", "state", "position", "timestamp"]}
                }
    if len(minis_data_copy["Global Steel Road"]) > 0:
        item = {**item,
                **{"SR::" + i: minis_data_copy["Global Steel Road"][i]
                   for i in ["Slots", "last_viewed_menu",
                             "last_investment_timestamp",
                             "investments_in_last_station"]}
                }
    if len(minis_data_copy["Investment Plan"]) > 0:
        item = {**item,
                **{"IP::" + i: minis_data_copy["Investment Plan"][i]
                   for i in ["last_investment_timestamp",
                             "current_option"]}
                }
    if len(minis_data_copy["Shop Chain"]) > 0:
        item = {**item,
                **{"SC::" + i: minis_data_copy["Shop Chain"][i]
                   for i in [
                       "game_timestamp", "employees", "payment_amount",
                       "history", "highscore"] + [
                       ("shops_" + f) for f in gut.list["membership"]]}
                }
        for field in ["SC::employees", "SC::payment_amount", "SC::highscore"] + [
                ("SC::shops_" + f) for f in gut.list["membership"]]:
            item[field] = str(item[field])
        for id in range(len(item["SC::history"])):
            item["SC::history"][id] = str(item["SC::history"][id])
    di.ezput_item(di.pre_miniplayers, item)
    return "Ok"


def gear_up(chat_id, new_membership, new_gear_level, new_production_level):
    if chat_id not in ch.active_users:
        return "Abort"
    consolidate_balance(chat_id)
    print("dbw", chat_id, "gear_up")
    print(":: updating gear level")
    di.item_update(di.pre_user, {'key': {"S": str(
        chat_id)}}, "gear_level", {"N": new_gear_level})
    ch.active_users[chat_id]["gear_level"] = new_gear_level
    print(":: updating production level")
    di.item_update(di.pre_user, {'key': {"S": str(
        chat_id)}}, "production_level", {"N": new_production_level})
    ch.active_users[chat_id]["production_level"] = new_production_level
    print(":: updating membership")
    di.item_update(di.pre_user, {'key': {"S": str(
        chat_id)}}, "membership", {"S": new_membership})
    ch.active_users[chat_id]["membership"] = new_membership

    return "Ok"


def up_member_count(curname, new_count):
    di.item_update(
        di.pre_board,
        {"key": {"S": curname}},
        "members",
        {"N": new_count}
    )
    ch.member_count[
        conv.name(currency=curname)["membership"]
    ] = new_count


def member_switch(old_memb, new_memb, old_ship_count, new_ship_count):
    print("dbw", old_memb, new_memb, "member_switch")
    up_member_count(conv.name(membership=old_memb)["currency"], old_ship_count)
    up_member_count(conv.name(membership=new_memb)["currency"], new_ship_count)
    return "Ok"


def set_valves(chat_id, new_valve_count, new_production_level):
    if chat_id not in ch.active_users:
        return "Abort"
    consolidate_balance(chat_id)
    print("dbw", chat_id, "set_valves")
    di.item_update(di.pre_user, {'key': {"S": str(
        chat_id)}}, "shut_valves", {"N": new_valve_count})
    ch.active_users[chat_id]["shut_valves"] = new_valve_count
    di.item_update(di.pre_user, {'key': {"S": str(
        chat_id)}}, "production_level", {"N": new_production_level})
    ch.active_users[chat_id]["production_level"] = new_production_level
    return "Ok"


def up_minimal_user(chat_id, user_data):
    print("dbw", chat_id, "minimal_user")
    user_data["key"] = chat_id
    ch.minimal_user[chat_id] = user_data
    di.ezput_item(di.pre_minimal_user, user_data)


def up_minimal_general_data(data):
    print("dbw", "minimal_general")
    data["key"] = "Game"
    ch.minimal_general = data
    di.ezput_item(di.pre_minimal_general, data)
