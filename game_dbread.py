import dynamodb_interface as di
import game_util as gut
import conversions as conv
from db_chdata import ch


def login(chat_id):
    if chat_id not in ch().active_users:
        ch().active_users[chat_id] = di.object_get(di.pre_user,
                                                 {"key": {"S": chat_id}})
    if chat_id not in ch().active_users:
        return {"account_status": "Not Activated"}
    if not ch().active_users[chat_id]:
        return {"account_status": "Not Activated"}
    if "account_status" not in ch().active_users[chat_id]:
        return {"account_status": "Not Activated"}
    if ch().active_users[chat_id]["account_status"] == "Not Activated":
        return {"account_status": "Not Activated"}
    data = {}
    data["account_status"] = "Activated"
    data["membership"] = ch().active_users[chat_id]["membership"]
    data["production_level"] = ch().active_users[chat_id]["production_level"]

    data["blocks"] = {}
    for cur in gut.list["currency"]:
        if "blocks_" + cur not in ch().active_users[chat_id]:  # pre 0.9 shield
            ch().active_users[chat_id]["blocks_" + cur] = 0
        data["blocks"][cur] = ch().active_users[chat_id]["blocks_" + cur]

    data["last_login_timestamp"] = (ch().active_users[chat_id]
                                    ["last_login_timestamp"])
    data["account_creation_timestamp"] = (ch().active_users[chat_id]
                                          ["account_creation_timestamp"])
    data["language"] = ch().active_users[chat_id]["language"]
    if "nickname" not in ch().active_users[chat_id]:  # migration guard
        ch().active_users[chat_id]["nickname"] = "-"
    data["nickname"] = gut.nickname_unpack(
        ch().active_users[chat_id]["nickname"])
    if "gear_level" not in ch().active_users[chat_id]:  # migration guard
        ch().active_users[chat_id]["gear_level"] = 0
    data["gear_level"] = ch().active_users[chat_id]["gear_level"]
    if "shut_valves" not in ch().active_users[chat_id]:  # migration guard
        ch().active_users[chat_id]["shut_valves"] = 0
    data["shut_valves"] = ch().active_users[chat_id]["shut_valves"]
    data["balance_timestamp"] = ch().active_users[chat_id]["balance_timestamp"]
    data["balance"] = gut.balance(
        ch().active_users[chat_id]["production_level"],
        ch().active_users[chat_id]["gear_level"],
        gut.get_badge_line(data["nickname"]),
        ch().active_users[chat_id]["saved_balance"],
        ch().active_users[chat_id]["balance_timestamp"]
    )
    data["saved_balance"] = ch().active_users[chat_id]["saved_balance"]
    if "settings" not in ch().active_users[chat_id]:  # migration guard
        ch().active_users[chat_id]["settings"] = gut.default_settings
    data["settings"] = gut.settings_unpack(
        ch().active_users[chat_id]["settings"])
    return data


def get_language(chat_id):
    if chat_id not in ch().active_users:
        login(chat_id)
    if chat_id not in ch().active_users:
        return "English"
    if not ch().active_users[chat_id]:
        return "English"
    if "language" not in ch().active_users[chat_id]:
        return "English"
    return ch().active_users[chat_id]["language"]


def get_nickname(chat_id):
    if chat_id not in ch().active_users:
        login(chat_id)
    if chat_id not in ch().active_users:
        return "-"
    if not ch().active_users[chat_id]:
        return "-"
    if "nickname" not in ch().active_users[chat_id]:
        return "-"
    return gut.nickname_unpack(ch().active_users[chat_id]["nickname"])


def get_saved_balance(chat_id):
    if chat_id not in ch().active_users:
        login(chat_id)
    return ch().active_users[chat_id]["saved_balance"]


def get_user_season_data(chat_id):
    if chat_id not in ch().active_users:
        login(chat_id)
    if "season_data" not in ch().active_users[chat_id]:
        return {
            "season": "1_2019",
            "blocks_contributed": 0
        }
    return gut.user_season_data_unpack(ch().active_users[chat_id]["season_data"])


def get_currencies_status():
    if len(ch().global_production) == 0:
        for cur_name in gut.list["currency"]:
            ch().global_production[cur_name] = abs(int(di.item_get(
                di.pre_board,
                {"key": {"S": cur_name}},
                "hourly_production_rate",
                "S"
            )))
    return ch().global_production


def get_member_counts():
    if len(ch().member_count) == 0:
        for cur_name in gut.list["currency"]:
            ch().member_count[conv.name(currency=cur_name)["membership"]] = int(
                di.item_get(di.pre_board,
                            {"key": {"S": cur_name}},
                            "members", "N")
            )
    return ch().member_count


def get_leaderboard_raw_data():
    if len(ch().leaderboard_data) == 0:
        for cur_name in gut.list["currency"]:
            ch().leaderboard_data[cur_name] = di.item_get(
                di.pre_board,
                {"key": {"S": cur_name}},
                "leaderboard",
                "NS")
            if not ch().leaderboard_data[cur_name]:
                ch().leaderboard_data[cur_name] = []
    return ch().leaderboard_data


def get_multiplayer_info():
    if len(ch().multiplayer_info) == 0:
        ch().multiplayer_info = di.ezget_item(
            di.pre_board, {"key": "multiplayer_info"})
    if len(ch().multiplayer_info) == 0:  # initialization
        ch().multiplayer_info = {
            "key": "multiplayer_info",
            "players_activity": {},
            "top_gear": {},
            "top_production": {}
        }
    return ch().multiplayer_info


def get_season_info():
    if len(ch().season_info) == 0:
        ch().season_info = di.ezget_item(
            di.pre_board, {"key": "season_info"})
    if len(ch().season_info) == 0:  # initialization
        ch().season_info = {
            "key": "season_info",
            "current_season": "1_2022",
            "variations_timestamp": 0,
            "faction": {i: {
                "top_contributor": 0,
                "blocks_used": 0,
                "current_badge": ""
            } for i in gut.list["membership"]}
        }
    return ch().season_info


def check_payment(chat_id, cost, currency="unified"):
    player_balance = login(chat_id)["balance"]
    if player_balance >= cost:
        return True
    return False


def check_mmmb(chat_id, type, qty=1):
    if chat_id not in ch().active_users:
        player_blocks = login(chat_id)["blocks"][type]
        return player_blocks >= qty
    return ch().active_users[chat_id]["blocks_" + type] >= qty


def check_any_block(chat_id, qty=1):
    blocks = login(chat_id)["blocks"]
    sum = 0
    for type in blocks:
        sum += blocks[type]
    return sum >= qty


def get_market_data(section):
    if section not in ch().market_data:
        db_res = di.object_get(di.pre_market, {"key": {"S": section}})
        if not db_res:
            return "Create Market"
        if len(db_res) == 0:
            return "Create Market"
        ch().market_data[section] = db_res
    return ch().market_data[section]


def check_event_count(chat_id, event_name):
    if chat_id not in ch().events_data:
        ch().events_data[chat_id] = {}
        db_res = di.item_get(di.pre_event, {"key": {
                             "S": chat_id}}, event_name, "N")
        if db_res:
            ch().events_data[chat_id][event_name] = int(db_res)
        else:
            ch().events_data[chat_id][event_name] = 0
    return ch().events_data[chat_id][event_name]


def mini_get_general(game_name):
    if game_name not in ch().mini_general:
        ch().mini_general[game_name] = di.ezget_item(
            di.pre_minis, {"key": game_name})
        if not ch().mini_general[game_name]:
            ch().mini_general[game_name] = {}

        elif game_name == "Coinopoly" and "Money" in ch().mini_general[game_name]:
            for coin in ch().mini_general[game_name]["Money"]:
                ch().mini_general[game_name]["Money"][coin] = int(ch().mini_general[game_name]["Money"][coin])

    return ch().mini_general[game_name]


def mini_get_player(chat_id, game_name):
    if chat_id not in ch().mini_player:
        raw_data = di.ezget_item(di.pre_miniplayers, {"key": chat_id})
        ch().mini_player[chat_id] = {
            "inventory": {},
            "Daily News": {},
            "Ore Miner": {},
            "Coinopoly": {},
            "Global Steel Road": {},
            "Investment Plan": {},
            "Shop Chain": {}
        }
        for invit in ["coal", "dice", "key", "mystery_item", "investment_pass"]:
            if "in::" + invit in raw_data:
                ch().mini_player[chat_id]["inventory"][invit] = raw_data[
                    "in::" + invit]
            else:
                ch().mini_player[chat_id]["inventory"][invit] = 0
        if "DN::vote_timestamp" in raw_data:
            ch().mini_player[chat_id]["Daily News"] = {
                i: raw_data["DN::" + i] for i in ["vote_timestamp"]}
        if "OM::record_level" in raw_data:
            if "OM::protections" not in raw_data:
                raw_data["OM::protections"] = 0
            ch().mini_player[chat_id]["Ore Miner"] = {i: raw_data["OM::" + i]
                                                    for i in ["record_level",
                                                              "money_earnings",
                                                              "mined_mEmb",
                                                              "mined_mYmb",
                                                              "protections"]
                                                    }
            if "OM::mined_mDmb" in raw_data:
                ch().mini_player[chat_id]["Ore Miner"]["mined_mDmb"] = (
                    raw_data["OM::mined_mDmb"])
            if "OM::mined_mUSDmb" in raw_data:
                ch().mini_player[chat_id]["Ore Miner"]["mined_mUSDmb"] = (
                    raw_data["OM::mined_mUSDmb"])
            if "OM::mined_mAUDmb" in raw_data:
                for block_type in ["mAUDmb", "mBRmb", "mIRmb", "mAmb"]:
                    ch().mini_player[chat_id]["Ore Miner"][
                        "mined_" + block_type] = raw_data[
                        "OM::mined_" + block_type]
        if "CP::Coins" in raw_data:
            ch().mini_player[chat_id]["Coinopoly"] = {
                i: raw_data["CP::" + i] for i in ["Coins", "state", "position",
                                                  "timestamp"]
            }
        if "SR::Slots" in raw_data:
            if "SR::last_viewed_menu" not in raw_data:
                raw_data["SR::last_viewed_menu"] = "Market"
            if "SR::last_investment_timestamp" not in raw_data:
                raw_data["SR::last_investment_timestamp"] = 0
            if "SR::investments_in_last_station" not in raw_data:
                raw_data["SR::investments_in_last_station"] = 0
            ch().mini_player[chat_id]["Global Steel Road"] = {i: raw_data[
                "SR::" + i] for i in ["Slots", "last_viewed_menu",
                                      "last_investment_timestamp",
                                      "investments_in_last_station"]
            }
        if "IP::last_investment_timestamp" in raw_data:
            if "IP::current_option" not in raw_data:
                raw_data["IP::current_option"] = 0
            ch().mini_player[chat_id]["Investment Plan"] = {
                i: raw_data["IP::" + i] for i in ["last_investment_timestamp",
                                                  "current_option"]
            }
        if "SC::game_timestamp" in raw_data:
            if "SC::investment" not in raw_data:
                raw_data["SC::investment"] = "0"
            ch().mini_player[chat_id]["Shop Chain"] = {}
            for field in ["game_timestamp", "employees", "payment_amount",
                          "history", "highscore",  "investment"]:
                ch().mini_player[chat_id]["Shop Chain"][field] = raw_data["SC::" + field]
            for faction in gut.list["membership"]:
                ch().mini_player[chat_id]["Shop Chain"]["shops_" + faction] = raw_data["SC::shops_" + faction]
    return ch().mini_player[chat_id][game_name]


def get_minimal_user(chat_id):
    if chat_id not in ch().minimal_user:
        ch().minimal_user[chat_id] = di.ezget_item(di.pre_minimal_user, {"key": chat_id})
        if not ch().minimal_user[chat_id]:
            ch().minimal_user[chat_id] = {}
    return ch().minimal_user[chat_id]


def get_minimal_general_data():
    if "key" not in ch().minimal_general:
        ch().minimal_general = di.ezget_item(di.pre_minimal_general, {"key": "Game"})
        if not ch().minimal_general:
            ch().minimal_general = {}
    return ch().minimal_general
