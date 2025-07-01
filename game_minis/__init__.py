from game_minis.daily_news import ui_DN_main_screen,  ui_DN_agencies_screen,  ui_DN_agencies_action,  ui_DN_select_country,  DN_check_game
from game_minis.ore_miner import ui_OM_main_screen,  ui_OM_game
from game_minis.global_steel_road import SR_position,  sr_data,  ui_SR_main_screen,  ui_SR_player_action,  ui_SR_manual,  ui_SR_mode_switch,  ui_SR_factories_action
from game_minis.investment_plan import IP_check_game,  IP_game_emoji,  ui_IP_main_screen,  ui_IP_info_screen,  ui_IP_option_select,  ui_IP_invest
from game_minis.shop_chain import sc_period,  SC_get_points_record,  economy_inflation,  SC_get_personal_points_record,  ui_SC_main_screen,  ui_SC_data_screen,  ui_SC_action
from game_minis.coinopoly import cp_map,  cp_period,  ui_CP_cryptoprint,  ui_CP_main_screen,  ui_CP_menu_map,  ui_CP_menu_list,  ui_CP_player_action
import conversions as conv
import back_end_sub_tasks as best
import game_util as gut

def check_status_SR():
    station_number, state = SR_position()
    if state == "going":
        station_number = (station_number + 1) % len(sr_data["itinerary"])
    station_name = sr_data["itinerary"][station_number]["name"]
    station_emoji = {
        "New York": conv.name(membership="FED")["badgemoji"],
        "Philadelphia": "🇺🇸",
        "Los Angeles": "🇺🇸",
        "Bogotá": "🇨🇴",
        "Santiago": "🇨🇱",
        "Buenos Aires": "🇦🇷",
        "São Paulo": conv.name(membership="CBB")["badgemoji"],
        "Rio de Janeiro": "🇧🇷",
        "Mexico City": "🇲🇽",
        "Toronto": "🇨🇦",
        "Glasgow": "🇬🇧",
        "London": "🇬🇧",
        "Paris": conv.name(membership="ECB")["badgemoji"],
        "Amsterdam": "🇳🇱",
        "Rhine-Ruhr": "🇩🇪",
        "Moscow": "🇷🇺",
        "Milan": "🇮🇹",
        "Madrid": "🇪🇸",
        "Lagos": conv.name(membership="ACB")["badgemoji"],
        "Johannesburg": "🇿🇦",
        "Cairo": "🇪🇬",
        "Jerusalem": "🇮🇱🇵🇸",
        "Istanbul": "🇹🇷",
        "Almaty": "🇰🇿",
        "Delhi": conv.name(membership="RBI")["badgemoji"],
        "Mumbai": "🇮🇳",
        "Kolkata": "🇮🇳",
        "Singapore": "🇸🇬",
        "Jakarta": "🇮🇩",
        "Melbourne": "🇦🇺",
        "Sydney": conv.name(membership="RBA")["badgemoji"],
        "Bangkok": "🇹🇭",
        "Ho Chi Minh City": "🇻🇳",
        "Guangzhou": "🇨🇳",
        "Shenzhen": "🇨🇳",
        "Hong Kong": "🇭🇰",
        "Shanghai": conv.name(membership="PBC")["badgemoji"],
        "Osaka": "🇯🇵",
        "Tokyo": "🇯🇵",
        "Seoul": "🇰🇷",
        "Beijing": "🇨🇳",
        "Chicago": "🇺🇸"
    }[station_name]
    if state == "stop":
        state_emoji = "📦"
        if sr_data["itinerary"][station_number]["type"] == "capital":
            state_emoji = "⭐️"
    else:
        if station_number <= 8 or station_number in [
                18, 19, 20, 21, 22, 29, 41]:
            state_emoji = "🚛"
        elif station_number in [9, 26, 27, 28, 30, 36, 38, 40]:
            state_emoji = "🛳"
        else:
            state_emoji = "🚂"

    return state_emoji, station_emoji


def check_action_DN(chat_id):
    game_data, winners = DN_check_game()
    player_data = best.mini_get_player(chat_id, "Daily News")
    if "vote_timestamp" not in player_data:
        return "🗞", winners
    if player_data["vote_timestamp"] <= game_data["game_timestamp"]:
        return "🗞", winners
    return "", winners


def check_action_IP(chat_id):
    game_data = IP_check_game()
    if game_data == "WIP":
        return "🚧"
    if IP_game_emoji(chat_id, game_data["game_timestamp"]):
        return "🏭"
    return ""


def check_action_CP(chat_id):
    player_data = best.mini_get_player(chat_id, "Coinopoly")
    player_time = player_data["timestamp"]
    if gut.time_s() // cp_period != player_time // cp_period:
        return "🏠"
    if (player_data["state"] == "landed" and
       cp_map[player_data["position"]] != "storehouse"):
        return "🏠"
    return ""


def check_action_available(chat_id, limit_CP, limit_IP):
    DN_action, DN_winners = check_action_DN(chat_id)
    if limit_CP:
        CP_action = check_action_CP(chat_id)
    else:
        CP_action = ""
    if limit_IP:
        IP_action = check_action_IP(chat_id)
    else:
        IP_action = ""
    notifications = DN_winners
    action_emoji = DN_action + CP_action + IP_action
    return action_emoji, notifications
