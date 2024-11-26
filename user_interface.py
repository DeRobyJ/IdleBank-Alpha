# Main code of the game, that accesses and uses the rest of it
# Basically, it is the front-end
import game_actions as game
import game_events
import uistr
import game_minis as minis
import os
import conversions as conv
import print_util as put
import random
import temporal_variations as tv
import math
import time
start_time = time.time()


def lvl_limit(lvl, gear, name, get_level=False):
    if name == "Shop Chain":
        if gear < 3:
            if get_level:
                return 3
            return False
    if gear > 0:
        return True
    limits = {
        "Block Selling": 2,
        "Global Production": 5,  # deprecated
        "Leaderboard and Minis": 5,  # Was 8 before
        "Mini DN": 10,
        "Mini CP": 15,
        "Mini OM": 20,
        "Mini SR": 25,
        "Block Requesting": 30,
        "Mini IP": 35
    }
    if get_level:
        return limits[name]

    if lvl >= limits[name]:
        return True
    return False


def get_titlecode_forlvl(level):
    code = 0
    for tier_level in [
            10, 20, 30, 40, 50, 70, 100, 150, 200, 300, 450, 600, 1000]:
        if level < tier_level:
            return code
        code += 1
    return code


def format_main_menu(chat_id, user_data, currencies_data):
    player_level = user_data["production_level"]
    player_gear = user_data["gear_level"]
    player_cursym = conv.name(membership=user_data["membership"])["symbol"]
    cur_order = [(i, currencies_data[i]) for i in currencies_data]
    cur_order = sorted(cur_order, key=lambda item: item[1], reverse=True)
    cur_order = [i[0] for i in cur_order]
    pos_symbols = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }
    player_cur = conv.name(membership=game.load_main_menu(
        chat_id)["user"]["membership"])["currency"]
    position = cur_order.index(player_cur) + 1

    message = ""
    if not game.passes_season_gearup_limit(chat_id):
        message += "🚩 "
    message += uistr.nickname(chat_id, chat_id, user_data["nickname"]) + " - "
    if position <= 3:
        message += pos_symbols[position] + " "
    message += user_data["membership"] + " " + user_data[
        "faction_badges"] + "\n"

    message += "[" + put.readable(player_level) + " - " + uistr.get(
        chat_id, "MM titles")[get_titlecode_forlvl(player_level)] + "]\n\n"
    user_can_upgrade, costs, extra_costs, missing_extra, _ = game.can_upgrade(
        chat_id)
    money_to_up = costs["Money"] - user_data["balance"]
    blocks_to_up = costs["Blocks"] - user_data["blocks"][player_cur]
    if user_data["balance"] < 10**10:
        money_print = put.readable(user_data["balance"])
    else:
        money_print = put.pretty(user_data["balance"])
    if game.is_money_capped(chat_id):
        message += uistr.get(chat_id, "MM main balance").format(
            value=user_data["balance"], sym=player_cursym + " \[ ! ]")  # noqa: W605
    else:
        message += uistr.get(chat_id, "MM main balance").format(
            value=money_print, sym=player_cursym)

    others = cur_order.copy()
    others.remove(player_cur)
    message += uistr.get(chat_id, "MM blocks")
    message += (put.pretty(user_data["blocks"][player_cur]) + " " +
                conv.name(currency=player_cur)["block"])
    list_count = 0
    for block_type in others:  # Note: here block_type is currency name
        if user_data["blocks"][block_type] > 0:
            if list_count % 3 > 0:
                message += " | "
            else:
                message += "\n"
            extra_text = ""
            if conv.name(currency=block_type)[
               "block"] in extra_costs and extra_costs[
                    conv.name(currency=block_type)["block"]] > 0:
                extra_text = " / " + put.readable(extra_costs[
                    conv.name(currency=block_type)["block"]])
            message += (put.pretty(user_data["blocks"][block_type]) +
                        " " + conv.name(currency=block_type)["block"] +
                        extra_text)
            list_count += 1
    message += "\n\n"

    prod_rate = int(user_data["production_hrate"] *
                    user_data["production_multiplier"])
    if prod_rate / 3600 >= 0.1:
        psint = prod_rate // 3600
        pscent = ((prod_rate + 18) // 36) % 100
        if psint < 100:
            if pscent < 10:
                pscent = "0" + str(pscent)
            persec_rate_str = str(psint) + "." + str(pscent)
        else:
            psint += int((pscent + 50) / 100)
            persec_rate_str = put.pretty(psint)
        message += uistr.get(chat_id, "MM production w sec").format(
            hourly_rate=put.pretty(prod_rate),
            sym=player_cursym,
            persec_rate=persec_rate_str)
    else:
        pmint = prod_rate // 60
        pmcent = ((prod_rate * 10 + 3) // 6) % 100
        if pmcent < 10:
            pmcent = "0" + str(pmcent)
        permin_rate_str = str(pmint) + "." + str(pmcent)
        message += uistr.get(chat_id, "MM production w min").format(
            hourly_rate=put.pretty(prod_rate),
            sym=player_cursym,
            permin_rate=permin_rate_str)

    ''' # Deprecated
    if lvl_limit(player_level, player_gear, "Global Production"):
        message += uistr.get(chat_id, "MM global production")
        message += put.pretty(
            currencies_data[player_cur]) + player_cursym + " / h"
        list_count = 0
        for currency in others:
            if list_count % 2 == 0:
                message += "\n"
            else:
                message += " | "
            message += put.pretty(currencies_data[currency]) + conv.name(
                currency=currency)["symbol"] + " / h"
            list_count += 1
    '''

    if not user_can_upgrade:
        message += "\n" + uistr.get(chat_id, "MM needed to upgrade")
        if money_to_up > 0 and prod_rate > 0:
            time_left = (costs["Money"] - game.get_float_balance(chat_id)) / prod_rate
            message += uistr.get(
                chat_id, "MM needed money").format(
                val=put.pretty(money_to_up),
                sym=player_cursym)
            if time_left * 60 < 3:
                message += random.choice(uistr.get(
                    chat_id, "MM needed money seconds")).format(
                    time=int(time_left * 60 * 60))
            elif time_left * 60 < 90:
                message += uistr.get(
                    chat_id, "MM needed money minutes").format(
                    val=put.pretty(money_to_up),
                    sym=player_cursym,
                    time=int(time_left * 60))
            elif time_left < 120:
                message += uistr.get(chat_id, "MM needed money hours").format(
                    val=put.pretty(money_to_up),
                    sym=player_cursym,
                    time=int(time_left + 0.5))
            else:
                message += uistr.get(chat_id, "MM needed money days").format(
                    val=put.pretty(money_to_up),
                    sym=player_cursym,
                    time=int(time_left / 24))
        if blocks_to_up > 0:
            message += uistr.get(chat_id, "MM needed blocks").format(
                val=put.pretty(blocks_to_up)
            )
        if True in [missing_extra[cur] > 0 for cur in missing_extra]:
            message += uistr.get(chat_id, "MM missing extras")
            for cur in missing_extra:
                if missing_extra[cur] > 0:
                    message += "|" + put.pretty(missing_extra[cur]) + " " + conv.name(
                        currency=cur)["block"] + "| "
    if player_gear == 0:
        message += "\n\n"
        message += uistr.get_tutorial_line(chat_id, player_level)

    return message


def main_menu_keyboard_for(chat_id, user_data, minis_emoji):
    player_level = user_data["production_level"]
    player_gear = user_data["gear_level"]
    print(time.time() - start_time, "MMK data got")

    keyboard = []
    user_can_upgrade, costs, _, _, up_points = game.can_upgrade(chat_id)
    if user_can_upgrade:
        # currency = conv.name(membership=user_data["membership"])["currency"]
        cur_sym = conv.name(membership=user_data["membership"])["symbol"]
        block_name = conv.name(membership=user_data["membership"])["block"]
        if player_gear == 0:
            button_string = "🔼 " + uistr.get(
                chat_id, "button upgrade prod").format(
                money_cost=put.pretty(costs["Money"]),
                sym=cur_sym,
                block_cost=costs["Blocks"],
                type=block_name)
        else:
            button_string = (
                "🔼 " + put.pretty(costs["Money"]) + cur_sym +
                " & " + put.pretty(costs["Blocks"]) + " " + block_name +
                " (" + put.pretty(up_points) + ")"
            )

        keyboard.append({button_string: "Upgrade Production"})
        if game.check_balance_type(chat_id) == "new":
            bulk_calculation = game.calculate_bulk_upgrade(chat_id)
            if "levels_done" in bulk_calculation:
                if bulk_calculation["levels_done"] > 1:
                    keyboard.append(
                        {"⏫ " + uistr.get(chat_id, "button upgrade prod bulk").format(
                            levels=bulk_calculation["levels_done"]
                        ):
                            "Upgrade Production Bulk"})
    print(time.time() - start_time, "MMK Upgrades done")

    if lvl_limit(player_level, player_gear, "Block Selling"):
        markets_row = {uistr.get(chat_id, "button block market"): "Market"}
        if lvl_limit(player_level, player_gear, "Block Requesting"):
            markets_row[uistr.get(chat_id, "button flea market")] = "Flea Mart 1"
        keyboard.append(markets_row)

    if lvl_limit(player_level, player_gear, "Leaderboard and Minis"):
        keyboard.append({
            minis_emoji + " " + uistr.get(
                chat_id, "button minigames") + " 🎲": "Games menu",
            uistr.get(chat_id, "button leaderboard"): "Leaderboard"})

    print(time.time() - start_time, "MMK Market, minis and leaderboard")

    if lvl_limit(player_level, player_gear, "Mini SR"):
        state_emoji, station_emoji = minis.check_status_SR()
        print(time.time() - start_time, "MMK GSR status")
        sr_button_text = state_emoji + " " + uistr.get(chat_id, "button minis SR") + " " + station_emoji
        if lvl_limit(player_level, player_gear, "Shop Chain"):
            items = ["🚗", "🛹", "🧹", "🎁", "🥾", "🏐",
                     "🎮", "🎧", "🎹", "📱", "🍕", "🍒",
                     "🌻", "📚", "🧸", "🧩", "🥪", "🧻"]
            item_emoji = items[(int(time.time()) // minis.sc_period) % len(items)]
            keyboard.append(
                {"🏪 " + uistr.get(chat_id, "button Shop Chain") + " " + item_emoji: "SC main",
                 sr_button_text: "SR main"
                 }
            )
        else:
            keyboard.append(
                {sr_button_text: "SR main"})

    print(time.time() - start_time, "MMK OM and GSR")

    checkevent, _ = game_events.check_event(chat_id)
    if checkevent:
        upbutton = ("button event", "Event")
    else:
        upbutton = ("button update", "Main menu")

    if game.mystery_item_info(chat_id)[0] > 0:  # quantity of mystery items
        keyboard.append({
            "IBTV 📺": "Temporal Variations 0",
            "❕ ❓ ❕": "Mystery Item Screen",
            uistr.get(chat_id, upbutton[0]): upbutton[1]
        })
    elif game.can_gear_up(chat_id)[0]:
        keyboard.append({
            "IBTV 📺": "Temporal Variations 0",
            "⚙️ 📦 ⚙️": "Gear",
            uistr.get(chat_id, upbutton[0]): upbutton[1]
        })
    elif game.can_operate_valves(chat_id):
        keyboard.append({
            "IBTV 📺": "Temporal Variations 0",
            "⚙️ 🔧 ⚙️": "Valve Screen",
            uistr.get(chat_id, upbutton[0]): upbutton[1]
        })
    else:
        if lvl_limit(player_level, player_gear, "Mini IP"):
            keyboard.append({"IBTV 📺": "Temporal Variations 0",
                            uistr.get(chat_id, upbutton[0]): upbutton[1]})
        else:
            keyboard.append({
                uistr.get(chat_id, "button settings"): "Settings",
                uistr.get(chat_id, upbutton[0]): upbutton[1]
            })

    print(time.time() - start_time, "MMK Settings, Gear and Events")
    return keyboard


def bulk_confirm_screen(chat_id):
    user_types = conv.name(game.load_main_menu(
        chat_id)["user"]["membership"])
    data = game.calculate_bulk_upgrade(chat_id)
    message = uistr.get(chat_id, "upgrade prod bulk confirmation").format(
        money_cost=put.pretty(data["money"]),
        sym=user_types["symbol"],
        block_cost=put.pretty(data["blocks"]),
        block_type=user_types["block"],
        final_level=put.readable(data["level"]),
        points=put.readable(data["season_points"])
    )
    message += uistr.get(chat_id, "MM main balance").format(
        value=put.readable(
            game.load_main_menu(chat_id)["user"]["balance"]),
        sym=user_types["symbol"])
    message += (uistr.get(chat_id, "MM blocks") + put.readable(
        game.load_main_menu(chat_id)["user"]["blocks"][
            user_types["currency"]]) + " " + user_types["block"])

    keyboard = [
        {uistr.get(
            chat_id,
            "settings Bulk_confirm"): "Upgrade Production Bulk confirm"},
        {uistr.get(chat_id, "button back"): "Main menu"}]
    return message, keyboard


def nickname_setting(chat_id, tnd, operation):  # tnd: temporary nickname data
    if not tnd:
        tnd = {}
    if len(tnd) == 0:
        tnd = game.get_nickname(chat_id)
        tnd = {i: tnd[i]
               for i in ["adjective_1", "adjective_2", "noun", "language"]}
    message = uistr.get(chat_id, "nickname settings current").format(
        nickname=uistr.nickname(chat_id, chat_id, tnd))
    keyboard = [{
            uistr.get(chat_id, "button nickchange adj1").format(dice="🎲"): uistr.nick_query_pack(uistr.nick_change(chat_id, tnd, "adjective_1"), operation),  # noqa
            uistr.get(chat_id, "button nickchange adj2").format(dice="🎲"): uistr.nick_query_pack(uistr.nick_change(chat_id, tnd, "adjective_2"), operation),  # noqa
            uistr.get(chat_id, "button nickchange noun").format(dice="🎲"): uistr.nick_query_pack(uistr.nick_change(chat_id, tnd, "noun"), operation)  # noqa
        }]

    if tnd["language"] == "Translate":
        message += uistr.get(chat_id, "nickname settings translate")
        keyboard.append({uistr.get(chat_id, "button nickchange forcelang"):
                         uistr.nick_query_pack(
            uistr.nick_change(chat_id, tnd, "language"), operation)})
    else:
        message += uistr.get(chat_id, "nickname settings force")
        keyboard.append({uistr.get(chat_id, "button nickchange translang"):
                         uistr.nick_query_pack(
            uistr.nick_change(chat_id, tnd, "language"), operation)})

    keyboard.append({uistr.get(chat_id, "button discard"): "Main menu",
                     uistr.get(
        chat_id, "button save"): uistr.nick_query_pack(tnd, "Nicksave")})
    return message, keyboard


def leaderboard(chat_id):
    ordered_data = game.check_and_get_leaderboards(chat_id)
    currencies_status = game.load_main_menu(chat_id)["currencies"]
    member_count = game.get_member_counts()
    cur_order = [(i, currencies_status[i]) for i in currencies_status]
    cur_order = sorted(cur_order, key=lambda item: item[1], reverse=True)
    cur_order = [i[0] for i in cur_order]
    message = ""
    position = 1
    pos_symbols = {
        1: "🥇",
        2: "🥈",
        3: "🥉",
        4: "4",
        5: "5",
        6: "6",
        7: "7"
    }
    pp_buttons = [{}, {}, {}]
    for currency in cur_order:
        cur_sym = conv.name(currency=currency)["symbol"]
        membership = conv.name(currency=currency)["membership"]
        faction_name = (uistr.get(chat_id, "faction " + membership) +
                        " " + game.get_faction_badgeline(membership))
        message += pos_symbols[position]
        if member_count[membership] == 0:
            message += "- " + faction_name + " (0 👥)\n"
        else:
            message += ("- " + faction_name + " (" +
                        put.readable(member_count[membership]) + " 👥)\n")
        message += uistr.get(chat_id, "MM global production") + put.pretty(
            currencies_status[currency]) + conv.name(
            currency=currency)["symbol"] + " / h\n"
        if position <= 3:
            player_in_faction = 1
            for entry in ordered_data[currency]:
                message += (
                    put.pretty(entry[1]) + cur_sym + " / h - " +
                    uistr.nickname(
                        chat_id,
                        entry[0],
                        game.get_nickname(entry[0])) + "\n")
                pp_buttons[position - 1][
                    membership + " " + str(player_in_faction)
                ] = "Player Page " + str(entry[0]) + " 0"
                player_in_faction += 1
        message += "\n"
        position += 1

    keyboard = []
    for pp_row in pp_buttons:
        if len(pp_row) > 0:
            keyboard.append(pp_row)
    keyboard.append({
        uistr.get(
            chat_id, "button season leaderboard"): "Season Leaderboard",
        uistr.get(
            chat_id, "button multiplayer_info"): "Multiplayer Info"
    })
    keyboard.append({
        uistr.get(chat_id, "button personal page"): "Personal Page 0",
        uistr.get(chat_id, "button back"): "Main menu"
    })
    return message, keyboard


def season_leaderboard(chat_id):
    season_name, ordered_data = game.get_season_leaderboard(chat_id)
    message = season_name + "\n\n"
    pp_buttons = [{}, {}]
    cur_element = 0
    for element in ordered_data:
        faction_name = (uistr.get(chat_id, "faction " + element["faction"]) +
                        " " + game.get_faction_badgeline(element["faction"]))
        block_type = "p."  # conv.name(membership=element["faction"])["block"]
        message += faction_name + ": "
        message += put.pretty(element["blocks"]) + " " + block_type + "\n"
        if element["top_contributor_blocks"] > 0:
            message += "🚩 " + element["top_contributor_nick"] + ": "
            message += put.readable(element[
                "top_contributor_blocks"]) + " " + block_type + "\n"
            pp_buttons[0 if cur_element < 3 else 1][
                element["faction"]
            ] = "Player Page " + str(element["top_contributor_id"]) + " 0"
        if "viewer_contribution" in element:
            message += uistr.get(chat_id, "faction you") + ": "
            message += put.readable(element[
                "viewer_contribution"]) + " " + block_type + "\n"
        message += "\n"
        cur_element += 1

    keyboard = []
    for pp_row in pp_buttons:
        if len(pp_row) > 0:
            keyboard.append(pp_row)
    keyboard.append({
        uistr.get(
            chat_id, "button leaderboard"): "Leaderboard",
        uistr.get(
            chat_id, "button multiplayer_info"): "Multiplayer Info"
    })
    keyboard.append({
        uistr.get(chat_id, "button personal page"): "Personal Page 0",
        uistr.get(chat_id, "button back"): "Main menu"
    })
    return message, keyboard


def multiplayer_info(chat_id):
    minfo = game.multiplayer_info_upget(chat_id)
    scinfo = minis.SC_get_points_record(chat_id)
    message = uistr.get(chat_id, "multiplayer info").format(
        last_24h=minfo["last_day_active_count"],
        last_7d=minfo["last_week_active_count"],
        last_30d=minfo["last_month_active_count"],
        tot_accounts=minfo["tot_player_count"],
        top_gear=minfo["top_gear"]["level"],
        top_gear_nick=uistr.nickname(
            chat_id,
            minfo["top_gear"]["chat_id"],
            game.get_nickname(minfo["top_gear"]["chat_id"]),
            compress=False
        ),
        shopchain_highscore=put.pretty(scinfo["highscore"]),
        shopchain_highscore_nick=scinfo["highscore_player_nick"]
    )
    return message


def settings_menu(chat_id):
    message = uistr.get(chat_id, "settings menu")
    keyboard = []

    settings = game.get_settings(chat_id)

    for setting in settings:
        set_line = uistr.get(chat_id, "settings " + setting) + " "
        if settings[setting]:
            set_line += "🟢"
        else:
            set_line += "🔴"
        keyboard += [{set_line: "Settings toggle " + setting}]

    keyboard += [{"Language": "Language selection",
                  uistr.get(chat_id, "button back"): "Main menu"}]
    return message, keyboard


def games_menu(chat_id):
    player_level = game.load_main_menu(chat_id)["user"]["production_level"]
    player_gear = game.load_main_menu(chat_id)["user"]["gear_level"]
    notifications = []
    keyboard = []
    if lvl_limit(player_level, player_gear, "Mini DN"):
        action_emoji_DN, winners_DN = minis.check_action_DN(chat_id)
        notifications += winners_DN
        keyboard.append({action_emoji_DN + " " + uistr.get(chat_id, "button minis DN"): "DN main"})  # noqa: E501
        DN_info = uistr.get(chat_id, "games menu DN")
    else:
        DN_info = "🔓 " + uistr.get(chat_id, "Level lock").format(
            lvl=lvl_limit(player_level, player_gear, "Mini DN", get_level=True)
        )

    if lvl_limit(player_level, player_gear, "Mini CP"):
        action_emoji_CP = minis.check_action_CP(chat_id)
        keyboard.append({action_emoji_CP + " " + uistr.get(chat_id, "button minis CP"): "CP main"})  # noqa: E501
        CP_info = uistr.get(chat_id, "games menu CP")
    else:
        CP_info = "🔓 " + uistr.get(chat_id, "Level lock").format(
            lvl=lvl_limit(player_level, player_gear, "Mini CP", get_level=True)
        )

    if lvl_limit(player_level, player_gear, "Mini OM"):
        keyboard.append({"⚒" + uistr.get(chat_id, "button minis OM") + "✨": "OM main"})
        OM_info = uistr.get(chat_id, "games menu OM")
    else:
        OM_info = "🔓 " + uistr.get(chat_id, "Level lock").format(
            lvl=lvl_limit(player_level, player_gear, "Mini OM", get_level=True)
        )

    if lvl_limit(player_level, player_gear, "Mini SR"):
        SR_info = uistr.get(chat_id, "games menu SR")
    else:
        SR_info = "🔓 " + uistr.get(chat_id, "Level lock").format(
            lvl=lvl_limit(player_level, player_gear, "Mini SR", get_level=True)
        )

    if lvl_limit(player_level, player_gear, "Mini IP"):
        action_emoji_IP = minis.check_action_IP(chat_id)
        keyboard.append({action_emoji_IP + " " + uistr.get(chat_id, "button minis IP"): "IP main"})  # noqa
        IP_info = uistr.get(chat_id, "games menu IP")
    else:
        IP_info = "🔓 " + uistr.get(chat_id, "Level lock").format(
            lvl=lvl_limit(player_level, player_gear, "Mini IP", get_level=True)
        )

    if lvl_limit(player_level, player_gear, "Shop Chain"):
        SC_info = uistr.get(chat_id, "games menu SC")
    else:
        SC_info = "🔓 " + uistr.get(chat_id, "Gear lock").format(
            gear=lvl_limit(player_level, player_gear, "Shop Chain", get_level=True)
        )

    keyboard.append({uistr.get(chat_id, "button back"): "Main menu"})

    message = uistr.get(chat_id, "games menu welcome").format(
        DN_info=DN_info,
        CP_info=CP_info,
        OM_info=OM_info,
        SR_info=SR_info,
        IP_info=IP_info,
        SC_info=SC_info
    )

    return message, keyboard, notifications


def gear_menu(chat_id):
    message = ""
    can, level_cost, _ = game.can_gear_up(chat_id)
    if level_cost is None:
        return "WIP", [{uistr.get(chat_id, "button back"): "Main menu"}]
    if not can:
        can = False
        message += uistr.get(chat_id, "Gearup not ready").format(
            needed_level=put.readable(level_cost + 1)
        )
        message += "\n" + "-" * 30 + "\n"
    excess_money = game.gearup_market_absorption(chat_id)
    if False:  # excess_money > 0:
        can = False
        message += uistr.get(chat_id, "Gearup too much money").format(
            excess=put.pretty(excess_money),
            sym=conv.name(membership=game.load_main_menu(
                chat_id)["user"]["membership"])["symbol"]
        )
        message += "\n" + "-" * 30 + "\n"
    if not game.passes_season_gearup_limit(chat_id):
        can = False
        message += uistr.get(chat_id, "Gearup season top")
        message += "\n" + "-" * 30 + "\n"

    message += uistr.get(chat_id, "Gearup info")
    message += "\n"

    effects = game.gearup_effects(chat_id)
    message += uistr.get(chat_id, "Gearup effect Prod_level") + put.readable(
        effects["Prod_level"][0]) + " → " + put.readable(
        effects["Prod_level"][1]) + "\n"
    message += uistr.get(chat_id, "Gearup effect Prod_rate") + put.pretty(
        effects["hourly_production_rate"][0]) + "M / h → " + put.pretty(
        effects["hourly_production_rate"][1]) + "M / h\n"
    message += uistr.get(chat_id, "Gearup effect bonus_blocks") + \
        put.pretty(effects["bonus_blocks"]) + "\n"
    if "new_badge" in effects:
        message += uistr.get(chat_id, "Gearup effect new_badge") + \
            effects["new_badge"] + "\n"
    elif "new_superbadge" in effects:
        message += uistr.get(chat_id, "Gearup effect new_superbadge") + \
            effects["new_superbadge"] + "\n"

    message += uistr.get(chat_id, "Gearup effect block_rate")
    for cur in effects["block_rate"][0]:
        message += conv.name(currency=cur)["badgemoji"] + " "
        message += conv.name(currency=cur)["block"] + " "
        message += put.readable(effects["block_rate"][0][cur])
        if cur in effects["block_rate"][1]:
            message += " → " + put.readable(effects["block_rate"][1][cur])
        message += "\n"

    message += uistr.get(chat_id, "Gearup effect multipliers")
    # baaad
    user_data = game.load_main_menu(chat_id)["user"]
    current_multiplier = game.gut.total_multiplier(
        user_data["nickname"]["badge_line"])
    new_multiplier = game.gut.total_multiplier(
        user_data["nickname"]["badge_line"] + "_")
    message += "x" + str(current_multiplier) + " → x" + str(
        new_multiplier)
    keyboard = []
    if can:
        current_membership = user_data["membership"]
        others = game.gut.list["membership"].copy()
        others.remove(current_membership)
        if current_membership != "ACB":
            keyboard.append(
                {uistr.get(
                 chat_id, "Gearup button keep memb") + conv.name(
                 membership=current_membership)[
                 "badgemoji"]: "Gear " + current_membership})
        keyboard.append({uistr.get(
            chat_id, "Gearup button change memb").format(
                memb=memb) + conv.name(
                membership=memb)["badgemoji"]: "Gear " + memb
            for memb in others[:2]})
        keyboard.append({uistr.get(
            chat_id, "Gearup button change memb").format(
                memb=memb) + conv.name(
                membership=memb)["badgemoji"]: "Gear " + memb
            for memb in others[2:4]})
        keyboard.append({uistr.get(
            chat_id, "Gearup button change memb").format(
                memb=memb) + conv.name(
                membership=memb)["badgemoji"]: "Gear " + memb
            for memb in others[4:]})
        max_gu = game.check_max_gear_up(chat_id)
        if max_gu > 1:
            keyboard.append({uistr.get(
                chat_id, "Gearup button max").format(qty=max_gu) + conv.name(
                membership=current_membership)["badgemoji"]: "Gear max"
            })

    keyboard.append({uistr.get(chat_id, "button back"): "Main menu"})
    return message, keyboard


def info_upgrade_account_to_single_balance(chat_id):
    r = game.load_main_menu(chat_id)
    user_data = r["user"]
    cur_status = r["currencies"]

    message = ""
    message += uistr.get(chat_id, "accup new market general info")

    cur_order = [(i, cur_status[i]) for i in cur_status]
    cur_order = sorted(cur_order, key=lambda item: item[1], reverse=True)
    cur_order = [i[0] for i in cur_order]
    highest_cur = cur_order[0]
    change_rate = {
        i: max(0.001, (cur_status[i] / cur_status[highest_cur]))
        for i in cur_status}
    cur_sym = [conv.name(currency=currency)["symbol"]
               for currency in cur_order]

    sum_of_bal = 0
    for i in range(3):
        old_bal = user_data["balance"][cur_order[i]]
        new_bal = (max(1, int(int(old_bal / change_rate[cur_order[i]]) *
                   change_rate[cur_order[0]])))
        sum_of_bal += new_bal
        message += uistr.get(chat_id, "accup balance").format(
            old_balance=str(old_bal) + cur_sym[i],
            new_balance=str(new_bal) + cur_sym[0])
    message += uistr.get(chat_id, "accup total").format(
        total_new_balance=str(sum_of_bal) + cur_sym[0])

    return message


def market_screen(chat_id, section_selection):
    sections = []
    if section_selection == "all":
        sections = game.gut.list["block"]  # bad
    else:
        sections = [section_selection]
    cur_sym = conv.name(membership=game.load_main_menu(
        chat_id)["user"]["membership"])["symbol"]

    message = uistr.get(chat_id, "Market info")
    for section in sections:
        (converted_price, impulse, instock_money, instock_blocks, limit_money,
         limit_blocks) = game.market_upget(chat_id, section)
        if impulse < -10:
            direction_emoji = "⏬"
        elif impulse < -1:
            direction_emoji = "🔽"
        elif impulse <= 1:
            direction_emoji = "⏹"
        elif impulse <= 10:
            direction_emoji = "🔼"
        else:
            direction_emoji = "⏫"
        money_pcent = (instock_money * 100) // limit_money
        block_pcent = (instock_blocks * 100) // limit_blocks
        if len(sections) < 4:
            uistr_line = "Market section status"
        else:
            uistr_line = "Market section status short"
        message += uistr.get(chat_id, uistr_line).format(
            block=section,
            price=put.pretty(converted_price),
            cur_sym=cur_sym,
            direction_emoji=direction_emoji,
            money_pcent=money_pcent,
            block_pcent=block_pcent)
    if len(sections) == 1:
        if game.is_money_capped(chat_id):
            message += uistr.get(chat_id, "MM main balance").format(
                value=put.readable(
                    game.load_main_menu(chat_id)["user"]["balance"]),
                sym=cur_sym + " \[ ! ]")  # noqa
        else:
            message += uistr.get(chat_id, "MM main balance").format(
                value=put.readable(
                    game.load_main_menu(chat_id)["user"]["balance"]),
                sym=cur_sym)

        block_type = conv.name(block=section)["currency"]
        message += (uistr.get(chat_id, "MM blocks") + put.readable(
            game.load_main_menu(chat_id)["user"]["blocks"][block_type]) +
            " " + section)

    return message


def market_absolute_screen(chat_id):
    sections = game.gut.list["block"]
    message = ""
    for section in sections:
        (converted_price, impulse, instock_money, instock_blocks, limit_money,
         limit_blocks) = game.market_upget(chat_id, section)
        cur_sym = conv.name(block=section)["symbol"]
        message += conv.name(block=section)["badgemoji"] + " "
        message += conv.name(block=section)["membership"] + "\n"
        message += put.pretty(instock_money) + " / " + put.pretty(
            limit_money) + cur_sym + "\n"
        message += put.pretty(instock_blocks) + " / " + put.pretty(
            limit_blocks) + " " + section + "\n\n"

    message += "\n" + uistr.get(chat_id, "Market EDB command").format(
        command=" /edb"
    )
    return message


def market_section_selection(chat_id):
    player_main_section = conv.name(membership=game.load_main_menu(
        chat_id)["user"]["membership"])["block"]
    main_badge = conv.name(membership=game.load_main_menu(
        chat_id)["user"]["membership"])["badgemoji"]
    # [{i: "Market "+i for i in game.gut.list["block"]}]
    keyboard = []
    keyboard.append(
        {main_badge + " " + player_main_section + " " + main_badge:
         "Market " + player_main_section})
    others = game.gut.list["block"].copy()
    others.remove(player_main_section)
    keyboard.append({i: "Market " + i for i in others[:3]})
    keyboard.append({i: "Market " + i for i in others[3:]})
    return keyboard


def market_keyboard_options(limit):
    if limit == 0:
        options = []
    elif limit == 1:
        options = [1]
    elif limit <= 5:
        options = [1, limit]
    elif limit <= 10:
        options = [1, 3, limit]
    elif limit <= 50:
        options = [1, 3, 10, limit]
    elif limit <= 100:
        options = [1, 7, 30, limit]
    elif limit <= 500:
        options = [1, 10, 50, 100, limit]
    elif limit <= 1000:
        options = [1, 10, 70, 400, limit]
    elif limit <= 10000:
        options = [1, 10, 100, 800, limit]
    elif limit <= 1000000000:
        options = [1, limit // 100, limit // 10, limit // 4, limit]
    else:
        options = [
            1,
            int(math.pow(limit, 1 / 8)),
            int(math.pow(limit, 1 / 4)),
            int(math.pow(limit, 1 / 2)),
            limit // 2,
            limit
        ]
    return options


def market_action_buttons(chat_id, section):
    user_data = game.load_main_menu(chat_id)["user"]
    sell_row = {}
    keyboard = []
    if lvl_limit(
            user_data["production_level"],
            user_data["gear_level"],
            "Block Requesting"):
        buy_limit, sell_limit = game.market_buysell_limits(chat_id, section)
    else:
        buy_limit = sell_limit = 1
    sell_options = market_keyboard_options(sell_limit)
    for i in sell_options:
        if i == 1:
            sell_row[uistr.get(chat_id, "button market sell") +
                     " " + str(i)] = "Mkt s " + section + " " + str(i)
        else:
            sell_row[put.pretty(i)] = "Mkt s " + section + " " + str(i)
    if len(sell_row) > 0:
        keyboard.append(sell_row)
    current_blocks = user_data["blocks"][conv.name(
        membership=user_data["membership"])["currency"]]
    if lvl_limit(
            user_data["production_level"],
            user_data["gear_level"],
            "Block Requesting") or current_blocks < 5:
        buy_options = market_keyboard_options(buy_limit)
        buy_row = {}
        for i in buy_options:
            if i == 1:
                buy_row[uistr.get(chat_id, "button market buy") +
                        " " + str(i)] = "Mkt b " + section + " " + str(i)
            else:
                buy_row[put.pretty(i)] = "Mkt b " + section + " " + str(i)
        if len(buy_row) > 0:
            keyboard.append(buy_row)
    keyboard.append({
        uistr.get(chat_id, "Market button back"): "Market",
        uistr.get(chat_id, "button back"): "Main menu"})
    return keyboard


def quick_time_left(seconds):
    string = ""
    days = seconds // (60 * 60 * 24)
    hours = (seconds // (60 * 60)) % 24
    minutes = (seconds // 60) % 60
    seconds = seconds % 60
    if days >= 7:
        string += str(days) + "d"
    elif days >= 1:
        string += str(days) + "d" + str(hours) + "h"
    elif hours >= 1:
        string += str(hours) + "h" + str(minutes) + "m"
    else:
        string += "0h" + str(
            minutes) + "m" + str(seconds) + "s"
    return string


def flea_market_screen(chat_id, qty):
    qty = max(1, qty)
    data = game.flea_market_get(chat_id, qty)
    user_data = game.load_main_menu(chat_id)["user"]
    player_cursym = conv.name(membership=user_data["membership"])["symbol"]

    message = uistr.get(chat_id, "Flea Market Info")
    keyboard = []
    items_to_show = set()
    if data["payment"] == "Market":
        message += uistr.get(chat_id, "Flea Market Fee not due")
    else:
        items_to_show.add("money")

    for offer in ["hot", "mid", "ins"]:
        item0 = data[offer]["offer"][0]
        if item0 == "block":
            item0 = data[offer]["block_type"]
            item0name = data[offer]["block_type"]
        elif item0 == "crypto":
            item0 = data[offer]["crypto_type"]
            item0name = data[offer]["crypto_type"]
        else:
            item0name = uistr.get(chat_id, "FM item " + item0)
        item1 = data[offer]["offer"][1]
        if item1 == "block":
            item1 = data[offer]["block_type"]
            item1name = data[offer]["block_type"]
        elif item1 == "crypto":
            item1 = data[offer]["crypto_type"]
            item1name = data[offer]["crypto_type"]
        else:
            item1name = uistr.get(chat_id, "FM item " + item1)
        items_to_show.add(item0)
        items_to_show.add(item1)
        message += uistr.get(chat_id, "Flea Market Offer").format(
            offer_name=uistr.get(chat_id, "Flea Market Offer Name " + offer),
            time_left=quick_time_left(data[offer]["seconds_left"]),
            item_0=item0name,
            item_1=item1name
        )
        if data["payment"] == "Player":
            message += uistr.get(chat_id, "Flea Market Fee").format(
                price=put.pretty(data[offer]["price"] * qty),
                cur_sym=player_cursym
            )
        message += "\n"

        keyboard.append({(
            put.pretty(qty * data[offer]["offer_quantities"][0][0]) + " " +
            item0name + " -> " +
            put.pretty(qty * data[offer]["offer_quantities"][0][1]) + " " +
            item1name
        ): "FM deal0 " + offer + " " + str(qty),
            (
            put.pretty(qty * data[offer]["offer_quantities"][1][1]) + " " +
            item1name + " -> " +
            put.pretty(qty * data[offer]["offer_quantities"][1][0]) + " " +
            item0name
        ): "FM deal1 " + offer + " " + str(qty),
        })
    if "money" in items_to_show:
        message += uistr.get(chat_id, "MM main balance").format(
            value=put.pretty(user_data["balance"]), sym=player_cursym)
    for block_type in game.gut.list["block"]:
        if block_type in items_to_show:
            message += put.pretty(game.best.inventory_get(chat_id, block_type)
                                  ) + " " + block_type + "\n"
    for crypto_type in game.gut.list["crypto"]:
        if crypto_type in items_to_show:
            message += minis.ui_CP_cryptoprint(game.best.inventory_get(chat_id, crypto_type)
                                               ) + " " + crypto_type + "\n"
    for item in ["coal", "dice", "key", "investment_pass", "protections"]:
        if item in items_to_show:
            message += put.pretty(
                game.best.inventory_get(chat_id, item)
            ) + " " + uistr.get(chat_id, "FM item " + item) + "\n"
    keyboard.append({
        "++": "Flea Mart " + str(min(10 ** 18, qty * 10)),
        "+": "Flea Mart " + str(min(10 ** 18, qty + 1)),
        put.pretty(qty): "Flea Mart " + str(qty),
        "-": "Flea Mart " + str(max(1, qty - 1)),
        "--": "Flea Mart " + str(max(1, qty // 10))
    })
    keyboard.append({uistr.get(chat_id, "button back"): "Main menu"})
    return message, keyboard


def edb_screen(chat_id, money_qty, block_qty, faction="No"):
    if faction == "No":
        faction = game.get_membership(chat_id)
    conversions, discounted, bonussed, prices = game.edb_screen(
        chat_id, money_qty, block_qty, faction)

    message = uistr.get(chat_id, "EDB exchange")
    for cur in conversions:
        message += cur + ": " + put.readable(conversions[cur])
        message += conv.name(currency=cur)["symbol"] + "\n"
    message += "\n"

    cur_sym = conv.name(membership=faction)["symbol"]
    block_type = conv.name(membership=faction)["block"]
    message += uistr.get(
        chat_id, "EDB discount") + put.readable(
        discounted) + cur_sym + "\n"
    message += uistr.get(
        chat_id, "EDB bonus") + put.readable(
        bonussed) + " " + block_type + "\n"
    unit = (conv.name(membership=faction)["symbol"] + " / " +
            conv.name(membership=faction)["block"])
    message += uistr.get(chat_id, "EDB block prices").format(
        market=put.pretty(prices["market"]) + unit,
        IPcap=put.pretty(prices["IP_capitalist"]) + unit,
        IPsoc=put.pretty(prices["IP_socialist"]) + unit,
        GSRFbase=put.pretty(prices["GSRF_nobonus"]) + unit,
        GSRFwbonus=put.pretty(prices["GSRF_withbonus"]) + unit,
        GSRFwbonusS=put.pretty(prices["GSRF_withbonus_S"]) + unit
    )

    keyboard = []
    keyboard.append({
        "++": "EDB " + faction + " " + str(
            min(10 ** 18, money_qty * 10)) + " " + str(block_qty),
        "+": "EDB " + faction + " " + str(
            min(10 ** 18, money_qty + 1)) + " " + str(block_qty),
        put.pretty(money_qty) + cur_sym: "EDB " + faction + " " + str(
            money_qty) + " " + str(block_qty),
        "-": "EDB " + faction + " " + str(
            max(1, money_qty - 1)) + " " + str(block_qty),
        "--": "EDB " + faction + " " + str(
            max(1, money_qty // 10)) + " " + str(block_qty)
    })
    keyboard.append({
        "++": "EDB " + faction + " " + str(money_qty) + " " + str(
            min(10 ** 18, block_qty * 10)),
        "+": "EDB " + faction + " " + str(money_qty) + " " + str(
            min(10 ** 18, block_qty + 1)),
        put.pretty(block_qty) + block_type: "EDB " + faction + " " + str(
            money_qty) + " " + str(block_qty),
        "-": "EDB " + faction + " " + str(money_qty) + " " + str(
            max(1, block_qty - 1)),
        "--": "EDB " + faction + " " + str(money_qty) + " " + str(
            max(1, block_qty // 10)),
    })
    keyboard.append({uistr.get(chat_id, "button back"): "Main menu"})
    return message, keyboard


def mystery_item_screen(chat_id):
    available, info = game.mystery_item_info(chat_id)
    message = uistr.get(chat_id, "mystery item screen").format(
        blocks_self=str(
            info["blocks_self"][0]) + "-" + str(info["blocks_self"][1]),
        self_type=conv.name(membership=game.get_membership(chat_id))["block"],
        blocks_random=str(
            info["blocks_random"][0]) + "-" + str(info["blocks_random"][1]),
        blocks_eachtype=str(info[
            "blocks_eachtype"][0]) + "-" + str(info["blocks_eachtype"][1]),
        money=put.pretty(
            info["money"][0]) + " - " + put.pretty(info["money"][1]),
        cur_sym=conv.name(membership=game.get_membership(chat_id))["symbol"],
        coal=str(info["item_coal"][0]) + "-" + str(info["item_coal"][1]),
        protections=str(info[
            "item_protections"][0]) + "-" + str(info["item_protections"][1]),
        keys=str(info["item_keys"][0]) + "-" + str(info["item_keys"][1]),
        dice=str(info["item_dice"][0]) + "-" + str(info["item_dice"][1]),
        crypto_random=str(info[
            "crypto_random"][0]) + "-" + str(info["crypto_random"][1]),
        crypto_each=str(info[
            "crypto_each"][0]) + "-" + str(info["crypto_each"][1]),
        investment_pass=str(info[
            "item_investment_pass"][0]) + "-" + str(info["item_investment_pass"][1]),
        mysteryitem=str(info[
            "item_mysteryitem"][0]) + "-" + str(info["item_mysteryitem"][1])
    )
    keyboard = [
        {uistr.get(chat_id, "button use mystery item").format(
            count=available
        ): "Mystery Item Use"},
        {uistr.get(chat_id, "button back"): "Main menu"}
    ]
    return message, keyboard


def temporal_variations_screen(chat_id, delta_month):
    current_absmonth = (time.gmtime(
        game.gut.time_s()).tm_year - 2022) * 12 + time.gmtime(
        game.gut.time_s()).tm_mon - 11
    if current_absmonth + delta_month < 0:
        delta_month = -current_absmonth
    month_name = uistr.get(chat_id, "Month")[tv.get_month(delta_month)]
    season_name = game.get_season_name_at_month(chat_id, delta_month)
    tv_season = tv.stream(delta_month)["seasonal"]
    tv_month = tv.stream(delta_month)["monthly"]
    message = season_name + " - " + month_name + "\n\n"

    if len(tv_season) > 0:
        message += uistr.get(chat_id, "TV Title Seasonal") + "\n"
        for vari in tv_season:
            message += "- " + uistr.get(chat_id, "TV Seasonal " + vari) + "\n"
        message += "\n"
    else:
        message += uistr.get(chat_id, "TV Seasonal Nothing") + "\n\n"

    if len(tv_month) > 0:
        message += uistr.get(chat_id, "TV Title Monthly") + "\n"
        for vari in tv_month:
            if tv_month[vari] is None or vari in [
                    "CP House Degrade", "CP Coin Tax", "IP Comeback"]:
                message += "- " + uistr.get(
                    chat_id, "TV Monthly " + vari) + "\n"
            elif vari == "GSRF Extra Dividends and Degrade":
                message += "- " + uistr.get(
                    chat_id, "TV Monthly " + vari).format(
                        dividends=tv_month[vari][0],
                        degrade=tv_month[vari][1]
                ) + "\n"
            elif vari == "DN Options":
                if tv_month[vari] < 0:
                    message += "- " + uistr.get(
                        chat_id, "TV Monthly DN Options -").format(
                            value=abs(tv_month[vari])
                    ) + "\n"
                else:
                    message += "- " + uistr.get(
                        chat_id, "TV Monthly DN Options +").format(
                            value=tv_month[vari]
                    ) + "\n"
            else:
                message += "- " + uistr.get(
                    chat_id, "TV Monthly " + vari).format(
                        value=tv_month[vari]
                ) + "\n"
    else:
        message += uistr.get(chat_id, "TV Monthly Nothing") + "\n\n"

    if delta_month == 0:
        ei = minis.economy_inflation(chat_id)
        if abs(ei) >= 100:
            ei_string = ("+" if ei >= 0 else "-") + put.pretty(int(abs(ei)))
        else:
            ei_string = ("+" if ei >= 0 else "-") + str(
                int(abs(ei))) + "." + str(int(abs(ei) * 10) % 10)
        message += uistr.get(chat_id, "TV Economy Inflation").format(
            inflation=ei_string
        )

    keyboard = [{
        "<": "Temporal Variations " + str(delta_month - 1),
        ">": "Temporal Variations " + str(delta_month + 1)
    }, {
        uistr.get(
            chat_id, "button season leaderboard"): "Season Leaderboard",
        uistr.get(chat_id, "button back"): "Main menu"
    }]
    return message, keyboard


def personal_page(viewer_id, chat_id, page):
    user_data = game.load_main_menu(chat_id)["user"]
    user_level = user_data["production_level"]
    user_gear = user_data["gear_level"]
    message = uistr.nickname(viewer_id, chat_id, user_data["nickname"])
    message += " - " + user_data["membership"] + " " + user_data[
        "faction_badges"] + "\n\n"
    message += uistr.get(viewer_id, "PP Levels").format(
        prod=put.readable(user_level),
        gear=put.readable(user_gear)
    )
    message += uistr.get(viewer_id, "PP SC highscore").format(
        score=put.pretty(minis.SC_get_personal_points_record(chat_id))
    )
    message += uistr.get(viewer_id, "PP Info").format(
        creation_date=user_data["account_creation_datastr"],
        lastlogin_date=user_data["last_login_datestr"])
    if viewer_id == chat_id:
        message += uistr.get(viewer_id, "PP Inventory").format(
            # Shhh, bad, very bad
            dice=game.best.inventory_get(chat_id, "dice"),
            coal=game.best.inventory_get(chat_id, "coal"),
            keys=game.best.inventory_get(chat_id, "key"),
            gsrfPass=game.best.inventory_get(chat_id, "investment_pass"),
            item=game.best.inventory_get(chat_id, "mystery_item")
        )
    message += "\n"
    badge_line = uistr.all_badges(user_data["nickname"]["badge_line"])
    lpp = 4  # lines per page
    pages = (badge_line.count("\n") - 1) // lpp + 1
    page = min(max(0, page), pages - 1)
    badge_line_per_line = badge_line.splitlines()

    if pages > 1:
        message += uistr.get(viewer_id, "PP Badges page").format(
            current=page + 1,
            total=pages
        )
    else:
        message += uistr.get(viewer_id, "PP Badges no pages")
    try:
        for i in range(lpp):
            if i + page * lpp < len(badge_line_per_line):
                message += badge_line_per_line[i + page * lpp] + "\n"
    except InxedError as e:
        message += str(badge_line_per_line)

    keyboard = []
    if chat_id == viewer_id:
        if pages > 1:
            keyboard.append({
                "<": "Personal Page " + str(page - 1),
                ">": "Personal Page " + str(page + 1)
            })
        keyboard.append({
            uistr.get(viewer_id, "button change nickname"): "Nickedit {}",
            uistr.get(viewer_id, "button back"): "Main menu"
        })
    else:
        if pages > 1:
            keyboard.append({
                "<": "Player Page " + str(chat_id) + " " + str(page - 1),
                ">": "Player Page " + str(chat_id) + " " + str(page + 1)
            })
        keyboard.append({
            uistr.get(viewer_id, "button back"): "Main menu"
        })

    return message, keyboard


def valve_screen(chat_id):
    (
        player_valves, player_level, level_after_opening_valves, all_valve_values,
        user_currency, op_price, can_gear_normally, gear_level_cost, can_gear_after_opening,
        max_valve_closing
    ) = game.get_valve_screen_data(chat_id)
    message = "൦" * 40 + "\n"
    message += uistr.get(chat_id, "Valve Info")
    for cur in all_valve_values:
        message += uistr.get(chat_id, "Valve faction value").format(
            faction=conv.name(currency=cur)["membership"],
            value=put.pretty(all_valve_values[cur])
        )

    level_after_closing_valves = player_level - max_valve_closing * all_valve_values[user_currency]
    message += uistr.get(chat_id, "Valve user options").format(
        cur_level=put.pretty(player_level),
        cur_valves=put.pretty(player_valves),
        level_after_opening=put.pretty(level_after_opening_valves),
        valves_closing=put.pretty(max_valve_closing),
        level_after_closing=put.pretty(level_after_closing_valves),
        valves_after_closing=put.pretty(max_valve_closing + player_valves),
        gear_level_cost=put.pretty(gear_level_cost)
    )

    if can_gear_normally:
        message += uistr.get(chat_id, "Valve note gear normal")
    elif can_gear_after_opening:
        message += uistr.get(chat_id, "Valve note gear after opening")

    message += uistr.get(chat_id, "Valve price").format(
        price=put.pretty(op_price),
        cur_sym=conv.name(currency=user_currency)["symbol"]
    )

    keyboard = []
    keyboard.append({
        uistr.get(chat_id, "Valve button close"): "Valve close",
        uistr.get(chat_id, "Valve button open"): "Valve open",
    })
    keyboard.append({uistr.get(chat_id, "button back"): "Main menu"})
    return message, keyboard


# hopefully AWS doesn't kill machines in seconds!
current_request_type = {}
user_last_menu = {}


def exe_and_reply(query, chat_id):
    start_time = time.time()
    message = ""
    keyboard = None
    notifications = None
    if query == "Main menu":
        r = game.check_account(chat_id)
        if r["status"] == "Not Activated":
            message = uistr.get(chat_id, "Welcome screen") + \
                uistr.get(chat_id, "help message")
            keyboard = [
                {memb: "Activate " + memb for memb in r["data"][:3]},
                {memb: "Activate " + memb for memb in r["data"][3:]},
                {uistr.get(chat_id, "Random"): "Activate " +
                 [memb for memb in r["data"]][chat_id % len(r["data"])]},
                {"Language": "Language selection"}
            ]
        else:
            user_last_menu[chat_id] = query
            r = game.load_main_menu(chat_id)
            if not r:
                message = uistr.get(chat_id, "Internal error")
            elif game.check_balance_type(chat_id) == "old":
                game.upgrade_to_single_balance(chat_id)
                return exe_and_reply("Main menu", chat_id)
            else:
                if r["user"]["nickname"] == "-":
                    message = uistr.get(chat_id, "nick not set")
                    keyboard = [{
                        uistr.get(chat_id, "button create nick"): "Nickname {}"
                    }, {
                        uistr.get(chat_id, "button random nick"):
                            "Nickname Random"}]
                else:
                    player_level = r["user"]["production_level"]
                    player_gear = r["user"]["gear_level"]
                    (minis_emoji,
                     notifications) = minis.check_action_available(
                        chat_id,
                        lvl_limit(player_level, player_gear, "Mini CP"),
                        lvl_limit(player_level, player_gear, "Mini IP")
                    )
                    print(time.time() - start_time, "MM data got")
                    message = format_main_menu(
                        chat_id, r["user"], r["currencies"])
                    print(time.time() - start_time, "MM message written")
                    keyboard = main_menu_keyboard_for(
                        chat_id, r["user"], minis_emoji)
                    print(time.time() - start_time, "MM keyboard created")
                # print(keyboard)

    elif "Activate" in query:
        r = game.check_account(chat_id)
        if r["status"] == "Activated":
            message = uistr.get(chat_id, "Activated error")
        else:
            membership = query[len("Activate "):]
            r = game.activate_account(chat_id, membership)
            if not r:
                message = uistr.get(chat_id, "Activation error")
            else:
                message = uistr.get(chat_id, "Have fun")
                notifications = [{
                    "chat_id": int(os.environ["ADMIN_CHAT_ID"]),
                    "message": f"Activated account for /view@{chat_id}"
                }]
    elif query == "Account Upgrade":
        message = info_upgrade_account_to_single_balance(chat_id)
        keyboard = [{
            uistr.get(chat_id, "button confirm"): "Account Upgrade Confirm",
            uistr.get(chat_id, "button back"): "Main menu"}]
    elif query == "Account Upgrade Confirm":
        game.upgrade_to_single_balance(chat_id)
        message = uistr.get(chat_id, "Done")
    elif query == "Nickname Random":
        message = game.set_random_nickname(chat_id)
    elif "Nickname" in query:
        game.set_random_nickname(chat_id)
        message, keyboard = nickname_setting(
            chat_id, uistr.nick_query_unpack(query, "Nickname"), "Nickname")
    elif "Nickedit" in query:
        message, keyboard = nickname_setting(
            chat_id, uistr.nick_query_unpack(query, "Nickedit"), "Nickedit")
    elif "Nicksave" in query:
        message = game.set_nickname(
            chat_id, uistr.nick_query_unpack(query, "Nicksave"))

    elif query == "Upgrade Production":
        try:
            r = game.upgrade_money_printer(chat_id)
            message = r
        except TypeError:
            message = "🔄"
    elif query == "Upgrade Production Bulk":
        if game.get_settings(chat_id)["Bulk_confirm"]:
            message, keyboard = bulk_confirm_screen(chat_id)
        else:
            return exe_and_reply("Upgrade Production Bulk confirm", chat_id)
    elif query == "Upgrade Production Bulk confirm":
        message = game.bulk_upgrade(chat_id)

    elif query == "Market":
        message = market_screen(chat_id, "all")
        keyboard = market_section_selection(chat_id)
        keyboard.append({
            uistr.get(chat_id, "Market button absolute"): "Market Absolute",
            uistr.get(chat_id, "button back"): "Main menu"})
    elif query == "Market Absolute":
        message = market_absolute_screen(chat_id)
        keyboard = market_section_selection(chat_id)
        keyboard.append({
            uistr.get(chat_id, "Market button back"): "Market",
            uistr.get(chat_id, "button back"): "Main menu"})
    elif "Market" in query:
        user_last_menu[chat_id] = query
        market_section = query[len("Market "):]
        message = market_screen(chat_id, market_section)
        keyboard = market_action_buttons(chat_id, market_section)
    elif "Mkt s " in query:
        options = query[len("Mkt s "):]
        if True in [i in options for i in ["mEmb", "mYmb", "mAmb"]]:
            section = options[:len("mMmb")]
            quantity = int(options[len("mMmb "):])
        elif True in [i in options for i in ["mBRmb", "mIRmb"]]:
            section = options[:len("mMMmb")]
            quantity = int(options[len("mMMmb "):])
        elif True in [i in options for i in ["mUSDmb", "mAUDmb"]]:
            section = options[:len("mMMMmb")]
            quantity = int(options[len("mMMMmb "):])
        else:
            pass
        user_last_menu[chat_id] = "Market " + section
        message = game.market_sell(chat_id, section, quantity)
    elif "Mkt b " in query:
        options = query[len("Mkt s "):]
        if True in [i in options for i in ["mEmb", "mYmb", "mAmb"]]:
            section = options[:len("mMmb")]
            quantity = int(options[len("mMmb "):])
        elif True in [i in options for i in ["mBRmb", "mIRmb"]]:
            section = options[:len("mMMmb")]
            quantity = int(options[len("mMMmb "):])
        elif True in [i in options for i in ["mUSDmb", "mAUDmb"]]:
            section = options[:len("mMMMmb")]
            quantity = int(options[len("mMMMmb "):])
        else:
            pass
        user_last_menu[chat_id] = "Market " + section
        message = game.market_buy(chat_id, section, quantity)

    elif "Flea Mart" in query:
        user_last_menu[chat_id] = query
        qty = int(query[len("Flea Mart "):])
        message, keyboard = flea_market_screen(chat_id, qty)
    elif "FM deal0" in query:
        qty = int(query[len("FM deal0 xxx "):])
        user_last_menu[chat_id] = "Flea Mart " + str(qty)
        offer = query[len("FM deal0 "):len("FM deal0 xxx")]
        message = game.flea_market_deal(chat_id, offer, 0, qty)
    elif "FM deal1" in query:
        qty = int(query[len("FM deal1 xxx "):])
        user_last_menu[chat_id] = "Flea Mart " + str(qty)
        offer = query[len("FM deal1 "):len("FM deal1 xxx")]
        message = game.flea_market_deal(chat_id, offer, 1, qty)

    elif query == "Settings":
        user_last_menu[chat_id] = query
        message, keyboard = settings_menu(chat_id)
    elif "Settings toggle" in query:
        setting = query[len("Settings toggle "):]
        message = game.toggle_setting(chat_id, setting)
    elif query == "Language selection":
        message = " |\nv"
        keyboard = [{li: "langsel " + li}
                    for li in ["English", "Italiano", "Português"]]
    elif "langsel" in query:
        language_selected = query[len("langsel "):]
        game.change_language(chat_id, language_selected)
        message = uistr.get(chat_id, "Language set")

    elif query == "Games menu":
        message, keyboard, notifications = games_menu(chat_id)
    elif query == "DN main":
        user_last_menu[chat_id] = query
        message, keyboard, notifications = minis.ui_DN_main_screen(chat_id)
    elif query == "DN Agencies":
        user_last_menu[chat_id] = query
        message, keyboard, notifications = minis.ui_DN_agencies_screen(chat_id)
    elif "DN Agencies" in query:
        action = query[len("DN Agencies "):]
        message, notifications = minis.ui_DN_agencies_action(chat_id, action)
    elif "DN " in query:
        sel_id = query[len("DN vote "):]
        message, notifications = minis.ui_DN_select_country(chat_id, sel_id)
    elif query == "OM main":
        user_last_menu[chat_id] = query
        message, keyboard = minis.ui_OM_main_screen(chat_id)
    elif "OM " in query:
        message, keyboard, notifications = minis.ui_OM_game(chat_id, query)
    elif query == "IP main":
        user_last_menu[chat_id] = query
        message, keyboard = minis.ui_IP_main_screen(chat_id)
    elif query == "IP info":
        user_last_menu[chat_id] = query
        message, keyboard = minis.ui_IP_info_screen(chat_id)
    elif "IP " in query:
        if chat_id not in user_last_menu:
            user_last_menu[chat_id] = "IP info"
        if "option" in query:
            option = int(query[len("IP option "):])
            message = minis.ui_IP_option_select(chat_id, option)
        if "invest" in query:
            sel_id = query[len("IP invest "):]
            message = minis.ui_IP_invest(chat_id, sel_id)
    elif query == "CP main":
        user_last_menu[chat_id] = query
        message, keyboard = minis.ui_CP_main_screen(chat_id)
    elif "CP " in query:
        user_last_menu[chat_id] = "CP main"
        action = query[len("CP "):]
        if "map" in action:
            page = int(action[len("map "):])
            message, keyboard = minis.ui_CP_menu_map(chat_id, page)
        elif "list" in action:
            page = action[len("list "):]
            message, keyboard = minis.ui_CP_menu_list(chat_id, page)
        else:
            message, notifications = minis.ui_CP_player_action(chat_id, action)
    elif query == "SR main":
        user_last_menu[chat_id] = query
        message, keyboard = minis.ui_SR_main_screen(chat_id)
    elif "SR " in query:
        user_last_menu[chat_id] = "SR main"
        action = query[len("SR "):]
        if "coal" in action:
            message = minis.ui_SR_player_action(chat_id, "--", coal=True)
        elif "manual" in action:
            page = int(action[len("manual "):])
            message, keyboard = minis.ui_SR_manual(chat_id, page)
        elif "mode switch" in action:
            message = minis.ui_SR_mode_switch(chat_id)
        elif "sell" in action:
            product = action[len("sell "):]
            message = minis.ui_SR_player_action(chat_id, product, selling=True)
        elif "invest" in action:
            factory_id = action[len("invest "):]
            message, notifications = minis.ui_SR_factories_action(
                chat_id, factory_id, "invest")
        elif "build" in action:
            factory_id = action[len("build "):]
            message, notifications = minis.ui_SR_factories_action(
                chat_id, factory_id, "build")
        else:
            message = minis.ui_SR_player_action(chat_id, action)
    elif query == "SC main":
        user_last_menu[chat_id] = query
        message, keyboard = minis.ui_SC_main_screen(chat_id)
    elif query == "SC data screen":
        message, keyboard = minis.ui_SC_data_screen(chat_id)
    elif "SC " in query:
        user_last_menu[chat_id] = "SC main"
        action = query[len("SC "):]
        if action in ["pay", "open", "maximize"]:
            message = minis.ui_SC_action(chat_id, action)
        elif True in [kw in action for kw in ["wage", "hire"]]:
            value = int(action[len("xxxx "):])
            action = action[:len("xxxx")]
            message = minis.ui_SC_action(chat_id, action, value)

    elif query == "Leaderboard":
        user_last_menu[chat_id] = query
        message, keyboard = leaderboard(chat_id)
    elif query == "Season Leaderboard":
        user_last_menu[chat_id] = query
        message, keyboard = season_leaderboard(chat_id)

    elif query == "Multiplayer Info":
        user_last_menu[chat_id] = query
        message = multiplayer_info(chat_id)
        keyboard = [
            {uistr.get(
                chat_id, "button leaderboard"): "Leaderboard"},
            {
                uistr.get(chat_id, "button personal page"): "Personal Page 0",
                uistr.get(chat_id, "button back"): "Main menu"
            }]
    elif "Personal Page" in query:
        page = int(query[len("Personal Page "):])
        message, keyboard = personal_page(chat_id, chat_id, page)
    elif "Player Page" in query:
        sel_id, page = query[len("Player Page "):].split()
        message, keyboard = personal_page(chat_id, int(sel_id), int(page))

    elif query == "Gear":
        message, keyboard = gear_menu(chat_id)
    elif query == "Gear max":
        max_gu = game.check_max_gear_up(chat_id)
        message = game.bulk_gear_up(chat_id, max_gu)
    elif "Gear" in query:
        new_membership = query[len("Gear "):]
        message = game.gear_up(chat_id, new_membership)

    elif "EDB" in query:
        _, faction, money_qty, block_qty = query.split()
        message, keyboard = edb_screen(
            chat_id,
            int(money_qty),
            int(block_qty),
            faction)

    elif query == "Mystery Item Screen":
        user_last_menu[chat_id] = query
        message, keyboard = mystery_item_screen(chat_id)
    elif query == "Mystery Item Use":
        message, notifications = game.use_mystery_item(chat_id, 'all')

    elif "Temporal Variations" in query:
        delta_month = int(query[len("Temporal Variations "):])
        message, keyboard = temporal_variations_screen(chat_id, delta_month)

    elif query == "Valve Screen":
        user_last_menu[chat_id] = query
        message, keyboard = valve_screen(chat_id)
    elif query == "Valve close":
        message = game.operate_valves(chat_id, "close")
    elif query == "Valve open":
        message = game.operate_valves(chat_id, "open")

    elif query == "Event":
        message, keyboard = game_events.do_event(chat_id)
    else:
        pass

    if game_events.check_halloween_ghost():
        message += "\n👻"
    if not notifications:
        return message, keyboard
    print(time.time() - start_time, "Returning to main")
    return message, keyboard, notifications


def last_menu(chat_id):
    if chat_id not in user_last_menu:
        return exe_and_reply("Main menu", chat_id)
    return exe_and_reply(user_last_menu[chat_id], chat_id)


def game_credits(chat_id):
    message = ""

    message += "IdleBank Alpha\n\n"
    message += "Game design and implementation: Roberto Giaconia\n"
    message += "English UI and Italian translation: Roberto Giaconia\n"
    message += "Portuguese translation: Matheus Souza\n"
    message += "\nMany thanks to friends and pioneer players for helping me test and begin this incredible adventure!\nThanks to the r / incremental\_games subreddit.\n"  # noqa
    message += "\n_Se i giovani si organizzano, si impadroniscono di ogni ramo del sapere e lottano con i lavoratori e gli oppressi, non c’è scampo per un vecchio ordine fondato sul privilegio e sull’ingiustizia._ \n(~ Enrico Berlinguer)"  # noqa
    keyboard = [{uistr.get(chat_id, "button back"): "Main menu"}]
    return message, keyboard


def handle_message(chat_id, mex):
    try:
        num = int(mex)
    except (ValueError, TypeError):
        num = None

    if not num:
        if mex == "/start":
            return exe_and_reply("Main menu", chat_id)
        elif mex in ["/⚙️", "/settings", "/language", "/set"]:
            return exe_and_reply("Settings", chat_id)
        elif mex == "/help":
            return uistr.get(chat_id, "help message"), None
        elif mex == "/event":
            return game_events.do_event(chat_id)
        elif mex == "/credits":
            return game_credits(chat_id)
        elif mex == "/gear":
            if (game.check_account(chat_id)["status"] == "Activated" and
               (game.load_main_menu(chat_id)["user"][
                "production_level"] > 35 or
               game.load_main_menu(chat_id)["user"]["gear_level"] > 0)):
                return gear_menu(chat_id)
        elif mex == "/mi":
            return mystery_item_screen(chat_id)
        elif mex == "/valve":
            if (game.check_account(chat_id)["status"] == "Activated" and
               (game.load_main_menu(chat_id)["user"][
                "production_level"] > 35 or
               game.load_main_menu(chat_id)["user"]["gear_level"] > 0)):
                return valve_screen(chat_id)
        elif "/edb" in mex:
            query_parts = mex.split()
            faction = "No"
            if len(query_parts) > 1:
                faction = query_parts[1]
            return exe_and_reply("EDB " + faction + " 1000 10", chat_id)
        elif "/fixed_" in mex and chat_id == int(os.environ["ADMIN_CHAT_ID"]):
            user_id = mex[len("/fixed_"):]
            notifications = [{
                "chat_id": user_id,
                "message": "Bugfix!"
            }]
            return "Sent bugfix confirmation to " + str(
                user_id), None, notifications
        elif "/view@" in mex and chat_id == int(os.environ["ADMIN_CHAT_ID"]):
            user_id = mex[len("/view@"):]
            return exe_and_reply("Player Page " + user_id + " 0", chat_id)
        elif "/!" in mex and chat_id == int(os.environ["ADMIN_CHAT_ID"]):
            return game.admin_action(mex[2:]), None
        else:
            return uistr.get(chat_id, "bad message"), None
    if chat_id not in current_request_type:
        return uistr.get(chat_id, "timeout"), None
    r = game.put_offer(chat_id, current_request_type[chat_id], num)
    current_request_type.pop(chat_id)
    return r, None
