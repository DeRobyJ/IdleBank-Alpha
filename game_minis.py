# All the code for the minigames.
# Should be refactored in more files? Yes. Will I do it? No.

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


# == DAILY NEWS ==
'''
Global data
    Game timestamp: N
    Countries: M
        Vote count for country: N
        First voter chat_id: N
        Last voter chat_id: N
        All voters: [<chat_id>..]
    Agencies: M
        key: "<size>_<id>"
        value: [<chat_id>..]

User data
    Vote timestamp: N
'''

dn_extra_prizes = [
    "CP_crypto",  # Canada
    "OM_protection",  # France
    "money",  # Germany
    "OM_key",  # Japan
    "blocks",  # Italy
    "OM_coal",  # United Kingdom
    "money",  # USA
    "CP_extraturn",  # Brazil
    "SR_gas",  # Russia
    "OM_coal",  # China
    "CP_crypto",  # India
    "OM_key",  # South Africa
    "OM_coal",  # Australia
    "blocks",  # Saudi Arabia
    "money",  # Argentina
    "None_x2prizes",  # South Korea
    "None_mystery",  # Indonesia
    "OM_protection",  # Mexico
    "OM_protection",  # Turkey
    "CP_crypto"  # Spain
]


def DN_game_start(timestamp, countries_count):
    prev_data = dbr.mini_get_general("Daily News")
    if "Agencies" not in prev_data:
        agencies = {}
    else:
        agencies = prev_data["Agencies"]

    countries_count += tv.DN_options_increment()
    game_data = {
        "Agencies": agencies
    }
    game_data["key"] = "Daily News"
    game_data["game_timestamp"] = timestamp
    game_data["Countries"] = {}

    country_ids = [i for i in range(20)]
    random.shuffle(country_ids)
    for i in range(countries_count):
        game_data["Countries"][str(country_ids[i])] = {
            "vote_count": 0,
            "first_voter_chat_id": -1,
            "last_voter_chat_id": -1,
            "all_voters": [],
        }
    dbw.mini_up_general(game_data)
    return game_data


def DN_prize(game_data):
    total_players = 0
    most_votes = 0
    least_votes = float('inf')
    for country in game_data["Countries"]:
        total_players += game_data["Countries"][country]["vote_count"]
        if game_data["Countries"][country]["vote_count"] > most_votes:
            most_votes = game_data["Countries"][country]["vote_count"]
        if game_data["Countries"][country]["vote_count"] < least_votes:
            least_votes = game_data["Countries"][country]["vote_count"]
    if total_players < 8:
        prize_money_mult = 4 * total_players
    elif total_players < 14:
        prize_money_mult = 5 * total_players
    elif total_players < 21:
        prize_money_mult = 6 * total_players
    else:
        prize_money_mult = (6 + (total_players // 10)) * total_players
    prize_blocks = 100 * total_players
    return prize_money_mult, prize_blocks, most_votes, least_votes, total_players


def DN_player_money_prize(chat_id, prize_money_mult):
    return gut.cutify_number(
        prize_money_mult * best.get_production(chat_id),
        3)


def ui_DN_extra_prize_onwin(chat_id, country_id):
    extra = dn_extra_prizes[int(country_id)]
    if extra == "money":
        prize_money = int(best.get_production(chat_id) * 2)
        player_cursym = best.get_types_of(chat_id)["symbol"]

        dbw.give_money(chat_id, prize_money)
        return uistr.get(
            chat_id, "DN extra money").format(
                money=put.pretty(prize_money),
                cur_sym=player_cursym
        )
    if extra == "blocks":
        blocks = best.apply_block_bonus(50, chat_id=chat_id, deal=True)
        player_cur = best.get_types_of(chat_id)["currency"]
        dbw.add_block(chat_id, player_cur, count=blocks)
        return uistr.get(
            chat_id, "DN extra blocks").format(
                blocks=blocks
        )
    if extra == "CP_crypto":
        prize_qty = 100
        player_CPdata = best.mini_get_player(chat_id, "Coinopoly")
        if len(player_CPdata) != 0:
            crypto_types = list(set(cp_map))  # gets all unique types of cells
            crypto_types.remove(cp_map[0])  # removes the storehouse
            timestamp = dbr.mini_get_general("Daily News")["game_timestamp"]
            sel_type = crypto_types[
                (timestamp + int(country_id)) % len(crypto_types)]

            player_CPdata["Coins"][sel_type] = float.hex(
                float.fromhex(player_CPdata["Coins"][sel_type]) + prize_qty
            )
            best.mini_up_player(chat_id, "Coinopoly", player_CPdata)
            return uistr.get(
                chat_id, "DN extra CP_crypto").format(
                coin_type=sel_type,
                coins=prize_qty
            )
    if extra == "CP_extraturn":
        best.inventory_give(chat_id, "dice", 10)
        return uistr.get(
            chat_id, "DN extra onwin CP_extraturn")
    if extra == "OM_protection":
        player_OMdata = best.mini_get_player(chat_id, "Ore Miner")
        if len(player_OMdata) != 0:
            player_OMdata["protections"] += 30
            best.mini_up_player(chat_id, "Ore Miner", player_OMdata)
            return uistr.get(
                chat_id, "DN extra onwin OM_protection")
    if extra == "OM_key":
        best.inventory_give(chat_id, "key", 3)
        return uistr.get(
            chat_id, "DN extra onwin OM_key")
    if extra == "OM_coal":
        best.inventory_give(chat_id, "coal", 20)
        return uistr.get(
            chat_id, "DN extra OM_coal")
    if extra == "SR_gas":
        market_section = best.get_types_of(chat_id)["block"]
        market_data = dbr.get_market_data(market_section)
        target = {
            "money": market_data["money_limit"] // 2,
            "blocks": market_data["block_limit"] // 2
        }
        market_data["blocks"] = int(target["blocks"] + target["blocks"] // 2)
        market_data["money"] = int(target["money"] + target["money"] // 2)
        dbw.market_update(market_section, market_data)
        return uistr.get(
            chat_id, "DN extra onwin SR_gas")
    if extra == "None_mystery":
        best.inventory_give(chat_id, "mystery_item", 1)
        return uistr.get(
            chat_id, "DN extra onwin None_mystery")
        pass
    return " "


def DN_game_end(game_data):
    (prize_money_mult, prize_blocks, most_votes,
        least_votes, total_players) = DN_prize(game_data)
    winners = []
    for country in game_data["Countries"]:
        prize_multiplier = 1
        extra = dn_extra_prizes[int(country)]
        if extra == "None_x2prizes":
            prize_multiplier = 2
        # print(country)
        if game_data["Countries"][country]["vote_count"] == most_votes and (
           game_data["Countries"][country]["first_voter_chat_id"] >= 0):
            actual_winner_id = game_data["Countries"][country]["first_voter_chat_id"]
            winners_to_add = [actual_winner_id]
            winner_agency = DN_agencies_player(actual_winner_id, game_data["Agencies"])
            if winner_agency:
                if len(game_data["Agencies"][winner_agency]) >= int(winner_agency.split("_")[0]):
                    winners_to_add = game_data["Agencies"][winner_agency]
            for winner_id in winners_to_add:
                memb = best.get_types_of(winner_id)["membership"]
                if prize_money_mult > 0:
                    custom_prize_money = DN_player_money_prize(
                        winner_id,
                        prize_money_mult)
                    custom_prize_money = int(custom_prize_money * prize_multiplier)
                    dbw.give_money(
                        winner_id,
                        custom_prize_money)
                if prize_blocks > 0:
                    prize_blocks = int(prize_blocks * prize_multiplier)
                    prize_blocks = best.apply_block_bonus(
                        prize_blocks,
                        chat_id=winner_id,
                        deal=True
                    )
                    dbw.add_block(
                        winner_id,
                        conv.name(membership=memb)["currency"],
                        count=prize_blocks)
                extra_message = ui_DN_extra_prize_onwin(winner_id, country)
                winners.append({
                    "chat_id": winner_id,
                    "message": uistr.get(winner_id, "DN notify most").format(
                        prize=ui_game_prizes_message(
                            chat_id=winner_id,
                            owntype_blocks=prize_blocks,
                            owntype_money=custom_prize_money
                        )
                    ) + "\n" + extra_message
                })
        elif game_data["Countries"][country]["vote_count"] == least_votes and (
                game_data["Countries"][country]["last_voter_chat_id"] >= 0):
            actual_winner_id = game_data["Countries"][country]["last_voter_chat_id"]
            winners_to_add = [actual_winner_id]
            winner_agency = DN_agencies_player(actual_winner_id, game_data["Agencies"])
            if winner_agency:
                if len(game_data["Agencies"][winner_agency]) >= int(winner_agency.split("_")[0]):
                    winners_to_add = game_data["Agencies"][winner_agency]
            for winner_id in winners_to_add:
                memb = best.get_types_of(winner_id)["membership"]
                if prize_money_mult > 0:
                    custom_prize_money = DN_player_money_prize(
                        winner_id,
                        prize_money_mult)
                    custom_prize_money = int(custom_prize_money * prize_multiplier)
                    dbw.give_money(
                        winner_id,
                        custom_prize_money)
                if prize_blocks > 0:
                    prize_blocks = int(prize_blocks * prize_multiplier)
                    prize_blocks = best.apply_block_bonus(
                        prize_blocks,
                        chat_id=winner_id,
                        deal=True
                    )
                    dbw.add_block(
                        winner_id,
                        conv.name(membership=memb)["currency"],
                        count=prize_blocks)
                    extra_message = ui_DN_extra_prize_onwin(winner_id, country)
                winners.append({
                    "chat_id": (game_data["Countries"][country]
                                ["last_voter_chat_id"]),
                    "message": uistr.get(winner_id, "DN notify least").format(
                        prize=ui_game_prizes_message(
                            chat_id=winner_id,
                            owntype_blocks=prize_blocks,
                            owntype_money=custom_prize_money
                        )
                    ) + "\n" + extra_message
                })
    for win_notification in winners:
        if random.random() * 100 < 1:
            win_notification["message"] += "\n" + "-" * 20 + "\n" + uistr.get(
                win_notification["chat_id"], "DN thanks message")
            win_notification["context_keyboard"] = [
                {emj: "feedback " + emj for emj in ["💚", "🎉", "📈"]},
                {emj: "feedback " + emj for emj in ["💩", "😁", "👀"]}
            ]
    return total_players, winners


def DN_country_keyboard(chat_id, countries):
    if len(countries) < 4:  # 3,4,5
        return [{uistr.dn_country(chat_id, i): (
            "DN vote " + str(i)) for i in countries}]
    elif len(countries) % 2 == 0:  # 4,6,8,10
        return [
            {uistr.dn_country(chat_id, i): "DN vote " + str(i)
                for i in countries[:len(countries) // 2]},
            {uistr.dn_country(chat_id, i): "DN vote " + str(i)
                for i in countries[len(countries) // 2:]}
        ]
    elif len(countries) == 5:
        return [
            {uistr.dn_country(chat_id, i): "DN vote " + str(i)
                for i in countries[:3]},
            {uistr.dn_country(chat_id, i): "DN vote " + str(i)
                for i in countries[3:]}
        ]
    elif len(countries) == 7:
        return [
            {uistr.dn_country(chat_id, i): "DN vote " + str(i)
                for i in countries[:4]},
            {uistr.dn_country(chat_id, i): "DN vote " + str(i)
                for i in countries[4:]}
        ]
    else:  # 9
        return [
            {uistr.get(chat_id, "DN countries")[
                int(i)]: "DN vote " + str(i) for i in countries[:3]},
            {uistr.get(chat_id, "DN countries")[
                int(i)]: "DN vote " + str(i) for i in countries[3:6]},
            {uistr.get(chat_id, "DN countries")[
                int(i)]: "DN vote " + str(i) for i in countries[6:]}
        ]


dn_period = (24 * 60 + 58) * 60  # 24h 58m
# dn_period = 2*60 #2 minutes test


def ui_DN_time_left(chat_id):
    dn_last_update = dbr.mini_get_general("Daily News")["game_timestamp"]
    current_sec_left = dn_period - (gut.time_s() - dn_last_update)
    hours = int(current_sec_left // (60 * 60))
    if hours > 0:
        return uistr.get(chat_id, "IP time about").format(h1=hours, h2=hours + 1)
    else:
        return uistr.get(chat_id, "IP time less1h")


def DN_check_game():
    game_data = dbr.mini_get_general("Daily News")
    if len(game_data) == 0:
        game_data = DN_game_start(gut.time_s(), 3)
    winners = []
    if game_data["game_timestamp"] == 0:
        game_data = DN_game_start(gut.time_s(), 3)
    elif gut.time_s() > game_data["game_timestamp"] + dn_period:
        total_players, winners = DN_game_end(game_data)
        if total_players <= 20:
            new_options = 3
        elif total_players <= 50:
            new_options = 4
        elif total_players <= 100:
            new_options = 5
        elif total_players <= 150:
            new_options = 6
        elif total_players <= 200:
            new_options = 7
        elif total_players <= 250:
            new_options = 8
        elif total_players <= 300:
            new_options = 9
        else:
            new_options = 10
        game_data = DN_game_start(gut.time_s(), new_options)
    return game_data, winners


def ui_DN_main_screen(chat_id):
    game_data, winners = DN_check_game()
    player_data = best.mini_get_player(chat_id, "Daily News")
    user_timestamp = player_data["vote_timestamp"]
    message = uistr.get(chat_id, "DN welcome")
    prize_money_mult, prize_blocks, _, _, total_players = DN_prize(game_data)
    custom_prize_money = DN_player_money_prize(chat_id, prize_money_mult)
    message += uistr.get(chat_id, "DN round time prize").format(
        time=ui_DN_time_left(chat_id),
        votes=total_players,
        prize=ui_game_prizes_message(
            chat_id=chat_id,
            owntype_blocks=prize_blocks,
            owntype_money=custom_prize_money))
    if user_timestamp > game_data["game_timestamp"]:
        message += uistr.get(chat_id, "DN already voted")
        keyboard = [{
            uistr.get(chat_id, "button agencies"): "DN Agencies",
            uistr.get(chat_id, "button back"): "Main menu"}
        ]
    else:
        message += uistr.get(chat_id, "DN please vote")
        keyboard = DN_country_keyboard(
            chat_id, game_data["Countries"]) + [{
                uistr.get(chat_id, "button agencies"): "DN Agencies",
                uistr.get(chat_id, "button back"): "Main menu"}
        ]

    return message, keyboard, winners


def ui_DN_extra_prize_onvote(chat_id, sel_id):
    extra = dn_extra_prizes[int(sel_id)]
    if extra == "money":
        prize_money = int(best.get_production(chat_id) / 6)
        player_cursym = best.get_types_of(chat_id)["symbol"]

        dbw.give_money(chat_id, prize_money)
        return uistr.get(
            chat_id, "DN thanks") + "\n" + uistr.get(
            chat_id, "DN extra money").format(
                money=put.pretty(prize_money),
                cur_sym=player_cursym
        )
    if extra == "blocks":
        blocks = best.apply_block_bonus(5, chat_id=chat_id, deal=True)
        player_cur = best.get_types_of(chat_id)["currency"]
        dbw.add_block(chat_id, player_cur, count=blocks)
        return uistr.get(
            chat_id, "DN thanks") + "\n" + uistr.get(
            chat_id, "DN extra blocks").format(
                blocks=blocks
        )
    if extra == "CP_crypto":
        prize_qty = 10
        player_CPdata = best.mini_get_player(chat_id, "Coinopoly")
        if len(player_CPdata) != 0:
            crypto_types = list(set(cp_map))  # gets all unique types of cells
            crypto_types.remove(cp_map[0])  # removes the storehouse
            timestamp = dbr.mini_get_general("Daily News")["game_timestamp"]
            sel_type = crypto_types[
                (timestamp + int(sel_id)) % len(crypto_types)]

            player_CPdata["Coins"][sel_type] = float.hex(
                float.fromhex(player_CPdata["Coins"][sel_type]) + prize_qty
            )
            best.mini_up_player(chat_id, "Coinopoly", player_CPdata)
            return uistr.get(
                chat_id, "DN thanks") + "\n" + uistr.get(
                chat_id, "DN extra CP_crypto").format(
                    coin_type=sel_type,
                    coins=prize_qty
            )
    if extra == "CP_extraturn":
        best.inventory_give(chat_id, "dice", 1)
        return uistr.get(
            chat_id, "DN thanks") + "\n" + uistr.get(
            chat_id, "DN extra onvote CP_extraturn")
    if extra == "OM_protection":
        player_OMdata = best.mini_get_player(chat_id, "Ore Miner")
        if len(player_OMdata) != 0:
            player_OMdata["protections"] += 5
            best.mini_up_player(chat_id, "Ore Miner", player_OMdata)
            return uistr.get(
                chat_id, "DN thanks") + "\n" + uistr.get(
                chat_id, "DN extra onvote OM_protection")
    if extra == "OM_key":
        best.inventory_give(chat_id, "key", 1)
        return uistr.get(
            chat_id, "DN thanks") + "\n" + uistr.get(
            chat_id, "DN extra onvote OM_key")
    if extra == "OM_coal":
        best.inventory_give(chat_id, "coal", 2)
        return uistr.get(
            chat_id, "DN thanks") + "\n" + uistr.get(
            chat_id, "DN extra OM_coal")
    if extra == "SR_gas":
        player_SRdata = best.mini_get_player(chat_id, "Global Steel Road")
        player_SRitems = []
        for i in range(len(player_SRdata["Slots"]) // 2):
            player_SRitems.append(
                player_SRdata["Slots"][i * 2] + player_SRdata["Slots"][i * 2 + 1])

        player_SRitems.append("DD")  # Gas
        player_SRdata["Slots"] = ""
        for item in player_SRitems:
            player_SRdata["Slots"] += item
        best.mini_up_player(chat_id, "Global Steel Road", player_SRdata)
        return uistr.get(
            chat_id, "DN thanks") + "\n" + uistr.get(
            chat_id, "DN extra onvote SR_gas")
    # if None
    return uistr.get(chat_id, "DN thanks")


def ui_DN_select_country(chat_id, sel_id):
    game_data, notifications = DN_check_game()
    player_data = best.mini_get_player(chat_id, "Daily News")
    user_timestamp = player_data["vote_timestamp"]
    if user_timestamp > game_data["game_timestamp"]:
        return uistr.get(chat_id, "DN already voted"), notifications
    if sel_id not in game_data["Countries"]:
        return uistr.get(chat_id, "DN invalid country"), notifications
    game_data["Countries"][sel_id]["vote_count"] += 1
    if "all_voters" not in game_data["Countries"][sel_id]:  # Update shield
        game_data["Countries"][sel_id]["all_voters"] = []
    game_data["Countries"][sel_id]["all_voters"].append(chat_id)
    if game_data["Countries"][sel_id]["first_voter_chat_id"] < 0:
        game_data["Countries"][sel_id]["first_voter_chat_id"] = chat_id
    game_data["Countries"][sel_id]["last_voter_chat_id"] = chat_id
    dbw.mini_up_general(game_data)
    player_data["vote_timestamp"] = gut.time_s()
    best.mini_up_player(chat_id, "Daily News", player_data)

    player_agency = DN_agencies_player(chat_id, game_data["Agencies"])
    if player_agency:
        if len(game_data["Agencies"][player_agency]) >= 2:
            all_in = True
            for member_id in game_data["Agencies"][player_agency]:
                if member_id not in game_data["Countries"][sel_id]["all_voters"]:
                    all_in = False
            if all_in:
                for member_id in game_data["Agencies"][player_agency]:
                    notifications.append({
                        "chat_id": member_id,
                        "message": uistr.get(member_id, "DN Agencies notify all voted")
                    })
                    best.inventory_give(member_id, "mystery_item", 1)

    message = ui_DN_extra_prize_onvote(chat_id, sel_id)
    return message, notifications


def ui_DN_agency_info_text(chat_id, ag):
    season = gut.current_season()
    rgen = random.Random(int(season[:4] + season[5] + ag.split("_")[1]))
    names = uistr.news_agency_names
    ag_name = rgen.choice(names) + rgen.choice(names) + rgen.choice(names)
    return uistr.get(chat_id, "DN Agencies agency").format(
        ag_name=ag_name,
        size=ag.split("_")[0]
    )


def DN_agencies_player(chat_id, agencies_data):
    for ag in agencies_data:
        if chat_id in agencies_data[ag]:
            return ag
    return None


def ui_DN_agencies_screen(chat_id):
    game_data, notifications = DN_check_game()
    message = ""
    keyboard = []
    # Show rules of the agencies
    message += uistr.get(chat_id, "DN Agencies Info")
    # Check if player is in any agency
    player_agency = DN_agencies_player(chat_id, game_data["Agencies"])
    # If in agency, show info on members (last DN vote, mystery items available)
    if player_agency:
        message += ui_DN_agency_info_text(chat_id, player_agency) + "\n"

        all_voted = True
        if len(game_data["Agencies"][player_agency]) < 2:
            all_voted = False
        for member_id in game_data["Agencies"][player_agency]:
            if best.mini_get_player(member_id, "Daily News")["vote_timestamp"] < game_data["game_timestamp"]:
                all_voted = False
                break
        for member_id in game_data["Agencies"][player_agency]:
            last_vote_timestamp = best.mini_get_player(member_id, "Daily News")["vote_timestamp"]
            last_vote_date_str = uistr.date_string(member_id, last_vote_timestamp)
            if all_voted:
                for country_id in game_data["Countries"]:
                    if member_id in game_data["Countries"][country_id]["all_voters"]:
                        last_vote_date_str += " - " + uistr.dn_country(chat_id, country_id)
                        break
            mi_available = best.inventory_get(member_id, "mystery_item")
            message += uistr.get(chat_id, "DN Agencies member").format(
                name=uistr.nickname(chat_id, member_id, dbr.get_nickname(member_id)),
                last_vote=last_vote_date_str,
                mys_items=mi_available
            ) + "\n"
    # Keyboard to leave
        keyboard.append({uistr.get(chat_id, "DN Agencies button leave"): "DN Agencies Leave"})
    # If not in agency, show current open agencies (a member's name, size maybe)
    else:
        count = 0
        keyboard_line = {}  # Keyboard to join
        for ag in game_data["Agencies"]:
            if len(game_data["Agencies"][ag]) >= int(ag.split("_")[0]):
                continue
            if len(game_data["Agencies"][ag]) == 0:
                continue
            count += 1
            message += str(count) + ": " + ui_DN_agency_info_text(chat_id, ag) + "\n"
            keyboard_line[uistr.get(
                chat_id, "DN Agencies button join"
            ) + str(count)] = "DN Agencies Join " + ag
            if count % 3 == 0:
                keyboard.append(keyboard_line)
                keyboard_line = {}
        if len(keyboard_line) > 0:
            keyboard.append(keyboard_line)
        keyboard.append({
            uistr.get(chat_id, "DN Agencies button create") + "2": "DN Agencies Create 2",
            uistr.get(chat_id, "DN Agencies button create") + "3": "DN Agencies Create 3"
        })

    keyboard.append({
        uistr.get(chat_id, "button back mini"): "DN main",
        uistr.get(chat_id, "button back"): "Main menu"
    })
    return message, keyboard, notifications


def ui_DN_agencies_action(chat_id, action):
    game_data, notifications = DN_check_game()
    if action == "Leave":
        player_agency = DN_agencies_player(chat_id, game_data["Agencies"])
        if player_agency:
            game_data["Agencies"][player_agency].remove(chat_id)
            for member_id in game_data["Agencies"][player_agency]:
                notifications.append({
                    "chat_id": member_id,
                    "message": uistr.get(member_id, "DN Agencies notify leave").format(
                        new_member=uistr.nickname(member_id, chat_id, dbr.get_nickname(chat_id))
                    )
                })
        else:
            return "Eh?", notifications
    elif "Join" in action:
        player_agency = DN_agencies_player(chat_id, game_data["Agencies"])
        if player_agency:
            return "Eh?", notifications
        agid = action[len("Join "):]
        if len(game_data["Agencies"][agid]) >= int(agid.split("_")[0]):
            return "Eh?", notifications
        for member_id in game_data["Agencies"][agid]:
            notifications.append({
                "chat_id": member_id,
                "message": uistr.get(member_id, "DN Agencies notify join").format(
                    new_member=uistr.nickname(member_id, chat_id, dbr.get_nickname(chat_id))
                )
            })
        game_data["Agencies"][agid].append(chat_id)
    elif "Create" in action:
        player_agency = DN_agencies_player(chat_id, game_data["Agencies"])
        if player_agency:
            return "Eh?", notifications
        size = action[len("Create "):]
        found = False
        for ag in game_data["Agencies"]:
            if ag.split("_")[0] == size and len(game_data["Agencies"][ag]) == 0:
                game_data["Agencies"][ag].append(chat_id)
                found = True
                break
        if not found:
            agid = size + "_" + str(len(game_data["Agencies"]))
            game_data["Agencies"][agid] = [chat_id]
    dbw.mini_up_general(game_data)
    return uistr.get(chat_id, "Done"), notifications


# == ORE MINER ==
'''
Global data
    Origin timestamp: N (hardcoded)
    Blocks Mined: M
        {level : N for level in [5, 10, 15, 20, 25, 30, 35, 40]}

User data
    Record level: N
    Total earnings: N
    Total Blocks mined Dollar : N
    Total Blocks mined Euro : N
    Total Blocks mined Yuan : N
    etc blocks

Query data
    0 - Current Level: N
    1 - Current Damage: N
    2 - Player Strength: N
    3 - Hammer uses: N
    4 - Pick uses: N
    5 - Protections: N
    6 - Hammer Precision

    querylen 01234567890123456789012345678901234567 -> 37 chars for deep game
    example: "OM game_[120,1000,5000,50,10,30,4000]"

Actions
    game: nothing, initial action
    hmmr: use hammer
    pick: use pick
    +str: upgrade strength
    +hpr: upgrade hammer precision
    reph: repair hammer
    repp: repair pick
    rspw: respawn
    exit: do new main menu message keeping this game going
    skey: use a secret key
'''


def OM_blocks_available(game_data, lvl):
    period = 3 * 60 * 60
    blocks_created = (gut.time_s() - origin_timestamp) // period
    return blocks_created - game_data["blocks_mined"][str(lvl)]


# Changed
def OM_mine_blocks_old(lvl):
    if lvl <= 40 and lvl % 5 == 0:
        qty = (lvl // 5)
    elif lvl % 10 == 0:
        qty = min(lvl // 5, 10)
        if lvl > 50:
            qty += min((lvl - 50) // 20, 5)
        if lvl > 150:
            qty += min((lvl - 150) // 50, 5)
        game_data = dbr.mini_get_general("Ore Miner")
        game_data["top_level"] = max(lvl, game_data["top_level"])
        dbw.mini_up_general(game_data)
        return qty
    else:
        return 0
    # this is executed only if lvl in [5,10,15,20,25,30,35,40]
    game_data = dbr.mini_get_general("Ore Miner")
    blocks_mined = min(qty, OM_blocks_available(game_data, lvl))
    game_data["blocks_mined"][str(lvl)] += blocks_mined
    game_data["top_level"] = max(lvl, game_data["top_level"])
    dbw.mini_up_general(game_data)
    return blocks_mined


def OM_mine_blocks(chat_id, lvl):
    game_data = dbr.mini_get_general("Ore Miner")
    extra_prize = 0

    if lvl <= 50 and lvl % 5 == 0:
        qty = lvl // 5
    else:
        bV = best.season_points("first") - best.season_points(dbr.login(chat_id)["membership"])

        base_prize = 0
        if lvl % 10 == 0:
            base_prize = max(
                lvl // 10,
                int(bV / 1000.0 * min(1, lvl / 1000.0))
            )

        for reserve in [5, 10, 15, 20, 25, 30, 35, 40]:
            if lvl % reserve > 0:
                continue
            if OM_blocks_available(game_data, reserve) > 0:
                extra_prize += max(1, int(bV / 640.0 * min(1, lvl / 1000.0)))
                game_data["blocks_mined"][str(reserve)] += 1
        qty = base_prize + extra_prize

    if lvl > game_data["top_level"] or extra_prize > 0:
        game_data["top_level"] = max(lvl, game_data["top_level"])
        dbw.mini_up_general(game_data)

    return qty


def OM_ore_conversion(chat_id, ores):
    p_faction = dbr.login(chat_id)["membership"]
    _, sc_data = SC_game_and_player_data(chat_id)
    value = {
        "aluminium": 5,
        "magnesium": 7,
        "chromium": 10,
        "iron": 5,
        "antimony": 20,
        "copper": 50,
        "silver": max(40, best.get_base_production(chat_id) * 24 // 100000),
        "platinum": max(60, sc_data["shops_" + p_faction] // 5),
        "gold": max(75, SR_factories_dividend(
            SR_position()[0]
        ) // 100000)
    }

    money = 0
    for ore in ores:
        money += int(ores[ore] * value[ore])

    return money


def ui_OM_prizes(chat_id, lvl, damage, layer_hp, layer_hpmax, action):
    ores = {}
    message = ""

    if action != "pick":
        message += uistr.get(chat_id, "OM ores destroyed")
        converted_prizes = {i: 0 for i in gut.list["block"]}
        converted_prizes["money"] = 0
    else:
        orig_lvl = lvl
        if orig_lvl <= 5:
            ores["aluminium"] = lvl
            ores["magnesium"] = 1 + lvl // 2
            ores_message = uistr.get(chat_id, "OM ores_message 2").format(
                num1=ores["aluminium"],
                ore1=uistr.get(chat_id, "OM ore aluminium"),
                num2=ores["magnesium"],
                ore2=uistr.get(chat_id, "OM ore magnesium")
            )
        elif orig_lvl <= 10:
            lvl -= 5
            ores["chromium"] = lvl
            ores["aluminium"] = 2 + lvl // 2
            ores["iron"] = 1
            ores_message = uistr.get(chat_id, "OM ores_message 3").format(
                num1=ores["chromium"],
                ore1=uistr.get(chat_id, "OM ore chromium"),
                num2=ores["aluminium"],
                ore2=uistr.get(chat_id, "OM ore aluminium"),
                num3=ores["iron"],
                ore3=uistr.get(chat_id, "OM ore iron")
            )
        elif orig_lvl <= 15:
            lvl -= 10
            ores["antimony"] = lvl
            ores["aluminium"] = 1 + lvl // 2
            ores["iron"] = 5
            ores_message = uistr.get(chat_id, "OM ores_message 3").format(
                num1=ores["antimony"],
                ore1=uistr.get(chat_id, "OM ore antimony"),
                num2=ores["aluminium"],
                ore2=uistr.get(chat_id, "OM ore aluminium"),
                num3=ores["iron"],
                ore3=uistr.get(chat_id, "OM ore iron")
            )
        elif orig_lvl <= 20:
            lvl -= 15
            ores["silver"] = lvl
            ores["iron"] = 15
            ores_message = uistr.get(chat_id, "OM ores_message 2").format(
                num1=ores["silver"],
                ore1=uistr.get(chat_id, "OM ore silver"),
                num2=ores["iron"],
                ore2=uistr.get(chat_id, "OM ore iron")
            )
        elif orig_lvl <= 25:
            lvl -= 20
            ores["antimony"] = 2 + lvl
            ores["copper"] = 1 + lvl // 2
            ores["iron"] = 10
            ores_message = uistr.get(chat_id, "OM ores_message 3").format(
                num1=ores["antimony"],
                ore1=uistr.get(chat_id, "OM ore antimony"),
                num2=ores["copper"],
                ore2=uistr.get(chat_id, "OM ore copper"),
                num3=ores["iron"],
                ore3=uistr.get(chat_id, "OM ore iron")
            )
        elif orig_lvl <= 30:
            lvl -= 25
            ores["platinum"] = lvl
            ores["iron"] = 15
            ores_message = uistr.get(chat_id, "OM ores_message 2").format(
                num1=ores["platinum"],
                ore1=uistr.get(chat_id, "OM ore platinum"),
                num2=ores["iron"],
                ore2=uistr.get(chat_id, "OM ore iron")
            )
        elif orig_lvl <= 40:
            lvl -= 30
            ores["gold"] = (lvl + 1) // 2
            ores["iron"] = 10 + lvl
            ores_message = uistr.get(chat_id, "OM ores_message 2").format(
                num1=ores["gold"],
                ore1=uistr.get(chat_id, "OM ore gold"),
                num2=ores["iron"],
                ore2=uistr.get(chat_id, "OM ore iron")
            )
        else:
            ores["gold"] = (lvl - 40) // 10 + 1
            ores["platinum"] = (lvl - 40) // 7 + 1
            ores["silver"] = (lvl - 40) // 5 + 1
            ores["iron"] = lvl // 2
            ores_message = uistr.get(chat_id, "OM ores_message 4").format(
                num1=ores["gold"],
                ore1=uistr.get(chat_id, "OM ore gold"),
                num2=ores["platinum"],
                ore2=uistr.get(chat_id, "OM ore platinum"),
                num3=ores["silver"],
                ore3=uistr.get(chat_id, "OM ore silver"),
                num4=ores["iron"],
                ore4=uistr.get(chat_id, "OM ore iron")
            )
        lvl = orig_lvl
        message += uistr.get(chat_id,
                             "OM prize ore").format(prize=ores_message)

        converted_prizes = {i: 0 for i in gut.list["block"]}
        converted_prizes["money"] = OM_ore_conversion(chat_id, ores)
        cur_sym = best.get_types_of(chat_id)["symbol"]
        message += uistr.get(chat_id, "OM ore conversion").format(
            money=put.pretty(converted_prizes["money"]), cur_sym=cur_sym)

    blocks_mined = OM_mine_blocks(chat_id, lvl)
    if action != "pick" and damage < layer_hpmax - 10:
        dmg_ratio = (damage - layer_hp) / (layer_hpmax - 10 - layer_hp)
        if random.random() > dmg_ratio:
            blocks_mined = 0
    if blocks_mined > 0:
        blocks_mined = best.apply_block_bonus(
            blocks_mined,
            chat_id=chat_id,
            deal=True
        )
        type = random.choice(gut.list["block"])
        converted_prizes[type] = blocks_mined
        message += "📦 " + \
            uistr.get(chat_id, "OM prize blocks").format(
                blocks_num=put.pretty(blocks_mined), type=type)

    if lvl % 10 == 9:
        converted_prizes["protections"] = 1
        message += uistr.get(chat_id, "OM prize protection")

    if lvl == 7:
        best.inventory_give(chat_id, "coal", 1)
        message += uistr.get(chat_id, "OM prize coal")
    elif lvl >= 5 and random.random() < min(.9, 0.1 + lvl / 1000):
        best.inventory_give(chat_id, "coal", 1)
        message += uistr.get(chat_id, "OM prize coal")

    if lvl == 40 and random.random() <= (.3 *
       best.mystery_item_base_probability(chat_id)):
        best.inventory_give(chat_id, "mystery_item", 1)
        message += uistr.get(chat_id, "found mystery item")
    elif lvl % 100 == 0 and random.random() <= (
            .5 * best.mystery_item_base_probability(chat_id)):
        best.inventory_give(chat_id, "mystery_item", 1)
        message += uistr.get(chat_id, "found mystery item")
    return message, converted_prizes


def OM_query_compile(action, data):
    # adding a symbol to break compatibility at reset!
    return "OM " + action + "_" + json.dumps([data[i] for i in [
        "level",
        "damage",
        "strength",
        "hammer_uses",
        "pick_uses",
        "protections",
        "hammer_precision"]])


def OM_query_decompile(query, chat_id):
    raw_data = json.loads(query[len("OM game_"):])
    if len(raw_data) < 6:  # compatibility with 0.4
        raw_data.append(0)
    if len(raw_data) < 7 or "_" not in query:  # compatibility with 0.5 | reset
        raw_data.append(0)
        raw_data[0] = 1
        raw_data[1] = 0
    return query[len("OM "):len("OM game")], {
        "level": raw_data[0],
        "damage": raw_data[1],
        "strength": raw_data[2],
        "hammer_uses": raw_data[3],
        "pick_uses": raw_data[4],
        "protections": raw_data[5],
        "hammer_precision": raw_data[6],
        "economy_inflation": economy_inflation(chat_id)
    }


def ui_OM_main_screen(chat_id):
    player_data = best.mini_get_player(chat_id, "Ore Miner")
    game_data = dbr.mini_get_general("Ore Miner")
    if "mined_mDmb" in player_data:
        player_data["mined_mUSDmb"] = player_data.pop("mined_mDmb")
        best.mini_up_player(chat_id, "Ore Miner", player_data)
    if "mined_mAUDmb" not in player_data:
        for block_type in ["mAUDmb", "mBRmb", "mIRmb", "mAmb"]:
            player_data["mined_" + block_type] = 0
        best.mini_up_player(chat_id, "Ore Miner", player_data)
    if len(game_data) == 0:
        game_data = {"key": "Ore Miner"}
        game_data["blocks_mined"] = {
            str(i): 0 for i in [5, 10, 15, 20, 25, 30, 35, 40]}
        game_data["top_level"] = 0
        dbw.mini_up_general(game_data)

    if game_data["top_level"] < player_data["record_level"]:
        game_data["top_level"] = player_data["record_level"]
        dbw.mini_up_general(game_data)

    message = uistr.get(chat_id, "OM welcome")
    message += uistr.get(chat_id, "OM past results").format(
        record=player_data["record_level"],
        money=put.pretty(player_data["money_earnings"]),
        cur_sym="M",
        mUSDmb=put.pretty(player_data["mined_mUSDmb"]),
        mEmb=put.pretty(player_data["mined_mEmb"]),
        mYmb=put.pretty(player_data["mined_mYmb"]),
        mAUDmb=put.pretty(player_data["mined_mAUDmb"]),
        mBRmb=put.pretty(player_data["mined_mBRmb"]),
        mIRmb=put.pretty(player_data["mined_mIRmb"]),
        mAmb=put.pretty(player_data["mined_mAmb"])
    )
    message += uistr.get(chat_id,
                         "OM top level").format(lvl=game_data["top_level"])
    starting_data_normal = {
        "level": 1,
        "damage": 0,
        "strength": 0,
        "hammer_uses": 0,
        "pick_uses": 0,
        "protections": 0,
        "hammer_precision": 0
    }
    starting_data_protections = {
        "level": 1,
        "damage": 0,
        "strength": 0,
        "hammer_uses": 0,
        "pick_uses": 0,
        "protections": player_data["protections"],
        "hammer_precision": 0
    }
    if player_data["protections"] == 0:
        keyboard = [{uistr.get(chat_id, "OM start"): OM_query_compile(
            "game", starting_data_normal)}]
    else:
        keyboard = [{
            uistr.get(chat_id, "OM start"): OM_query_compile(
                "game",
                starting_data_normal),
            uistr.get(chat_id, "OM start protected").format(
                protections=player_data["protections"]
            ): OM_query_compile("game", starting_data_protections)
        }]
    keyboard.append({uistr.get(chat_id, "button back"): "Main menu"})
    return message, keyboard


def ui_OM_ruined_line(ratio, len=30):
    line = "`"
    for _ in range(len):
        if random.random() * 1.4 < ratio:
            line += "-"
        else:
            line += "="
    line += "`"
    return line


def OM_tool_uses(record_level):
    hammer_max_uses = 10 + tv.OM_extra_durability()
    pick_max_uses = 3 + tv.OM_extra_durability()
    step = 1
    while record_level > 0:
        hammer_max_uses += min(record_level, step * 100) // (10 * step)
        pick_max_uses += min(record_level, step * 100) // (20 * step)
        record_level -= step * 100
        step *= 2

    return hammer_max_uses, pick_max_uses


def OM_damages(adventure_data):
    ei = adventure_data["economy_inflation"]
    max_bonus = int(math.log10(max(1, ei)) * 2)
    return {
        "hammer_min": adventure_data["hammer_precision"] + 5,
        "hammer_max": adventure_data["strength"] + 10 + max_bonus,
        "pick": adventure_data["strength"] // 2 + 2
    }


def OM_layer_HP(layer):
    return (
        10 * (1 + layer + (layer - 1) // 10 +
                          (layer - 1) // 20 +
                          (layer - 1) // 50 +
                          (layer - 1) // 100
              )
    )


def OM_fast_hammer(adventure_data, player_record):
    if player_record < 40:
        return 0
    max_output = OM_damages(adventure_data)["hammer_max"]
    layer_current_hp = OM_layer_HP(
        adventure_data["level"]) - adventure_data["damage"]
    if layer_current_hp // max_output > 3:
        return min(
            (layer_current_hp // max_output),
            OM_tool_uses(player_record)[0] - adventure_data["hammer_uses"]) - 1
    return 0


def ui_OM_game(chat_id, query):
    player_data = best.mini_get_player(chat_id, "Ore Miner")
    action, adventure_data = OM_query_decompile(query, chat_id)
    if action == "hmmr":
        adventure_data["damage"] += random.randint(
            OM_damages(adventure_data)["hammer_min"],
            OM_damages(adventure_data)["hammer_max"])
        adventure_data["hammer_uses"] += 1
    elif action == "fsth":
        fast_hammer = OM_fast_hammer(
            adventure_data, player_data["record_level"])
        for _ in range(fast_hammer):
            adventure_data["damage"] += random.randint(
                OM_damages(adventure_data)["hammer_min"],
                OM_damages(adventure_data)["hammer_max"])
        adventure_data["hammer_uses"] += fast_hammer
    elif action == "pick":
        adventure_data["damage"] += OM_damages(adventure_data)["pick"]
        adventure_data["pick_uses"] += 1
    elif action == "+str":
        adventure_data["strength"] += 10
    elif action == "+hpr":
        if adventure_data["hammer_precision"] < adventure_data["strength"]:
            adventure_data["hammer_precision"] += 5
    elif action == "reph":
        adventure_data["hammer_uses"] = 0
    elif action == "repp":
        adventure_data["pick_uses"] = 0
    # on game start
    elif (action == "game" and
          adventure_data["level"] == 1 and adventure_data["damage"] == 0):
        if (player_data["protections"] > 0 and
           adventure_data["protections"] > 0):
            player_data["protections"] = 0
            best.mini_up_player(chat_id, "Ore Miner", player_data)
    elif action == "rspw":
        blocks_to_pay = (adventure_data["level"] // 10) * 20 + 10
        if dbr.check_any_block(chat_id, qty=blocks_to_pay):
            blocks = dbr.login(chat_id)["blocks"]
            block_types = [type for type in blocks]
            for btype in blocks:
                if blocks[btype] == 0:
                    block_types.remove(btype)
            to_pay = {btype: 0 for btype in block_types}
            bleft = blocks_to_pay
            while bleft > 0:
                split_qty = bleft // 10 + 1
                btype = random.choice(block_types)
                to_pay[btype] += min(blocks[btype], split_qty)
                bleft -= min(blocks[btype], split_qty)
                if blocks[btype] == to_pay[btype]:
                    block_types.remove(btype)
            for btype in to_pay:
                r = dbw.pay_block(chat_id, btype, to_pay[btype])
                if r == "Abort":
                    print("OM coult'd pay blocks:", chat_id, blocks, to_pay)
            adventure_data["hammer_uses"] = 0
            adventure_data["pick_uses"] = 0
            if adventure_data["level"] <= 40:
                adventure_data["level"] = ((adventure_data["level"] - 1) //
                                           5) * 5 + 1
            else:
                adventure_data["level"] = ((adventure_data["level"] - 1) //
                                           10) * 10 + 1
            adventure_data["damage"] = 0
    elif action == "skey":
        if best.inventory_use(chat_id, "key", 1):
            adventure_data["level"] = adventure_data["level"] // 100 * 100 + 91
            adventure_data["hammer_uses"] = 0
            adventure_data["pick_uses"] = 0
    elif action == "exit":
        return None, None, [{
            "chat_id": chat_id,
            "message": uistr.get(chat_id, "OM exit message")}]

    layer_hp = OM_layer_HP(adventure_data["level"])
    layer_hpmax = layer_hp + (
        10 + adventure_data["protections"] * 5 + tv.OM_extra_layer_hp())
    ruin_ratio = adventure_data["damage"] / layer_hp

    hammer_max_uses, pick_max_uses = OM_tool_uses(player_data["record_level"])

    message = ""
    message += ui_OM_ruined_line(ruin_ratio, 30) + "\n"
    message += uistr.get(chat_id, "OM layer status").format(
        level=adventure_data["level"],
        damage=adventure_data["damage"],
        hp=layer_hp, hpmax=layer_hpmax)
    message += uistr.get(chat_id, "OM hammer status").format(
        uses=adventure_data["hammer_uses"],
        uses_max=hammer_max_uses,
        damage_min=OM_damages(adventure_data)["hammer_min"],
        damage_max=OM_damages(adventure_data)["hammer_max"]
    )
    message += uistr.get(chat_id, "OM pick status").format(
        uses=adventure_data["pick_uses"],
        uses_max=pick_max_uses,
        damage=OM_damages(adventure_data)["pick"]
    )
    message += ui_OM_ruined_line(ruin_ratio, 30) + "\n"

    death_keyboard = []
    blocks_to_pay = (adventure_data["level"] // 10) * 20 + 10
    if dbr.check_any_block(chat_id, qty=blocks_to_pay):
        death_keyboard.append({
            uistr.get(chat_id, "OM respawn").format(
                blocks_to_pay=blocks_to_pay
            ): OM_query_compile("rspw", adventure_data)
        })
    death_keyboard.append({uistr.get(chat_id, "button back"): "OM main"})

    if adventure_data["damage"] >= layer_hp:
        if adventure_data["damage"] > layer_hpmax:
            return message + uistr.get(
                chat_id, "OM lose"), death_keyboard, None
        message += uistr.get(chat_id, "OM layer broken")
        prize_message, converted_prizes = ui_OM_prizes(
            chat_id, adventure_data["level"],
            adventure_data["damage"],
            layer_hp, layer_hpmax, action)
        message += prize_message
        message += uistr.get(chat_id, "OM choose upgrade")
        adventure_data["level"] += 1
        adventure_data["damage"] = 0
        if adventure_data["hammer_precision"] < adventure_data["strength"]:
            keyboard = [
                {
                    "🎯🔨 " + uistr.get(chat_id, "OM upgrade precision"): OM_query_compile("+hpr", adventure_data),  # noqa: E501
                    "💪 " + uistr.get(chat_id, "OM upgrade strength"): OM_query_compile("+str", adventure_data)  # noqa: E501
                }
            ]
        else:
            keyboard = [
                {
                    "💪 " + uistr.get(chat_id, "OM upgrade strength"): OM_query_compile("+str", adventure_data)}  # noqa: E501
                ]

        keyboard += [
            {
                "🔧🔨 " + uistr.get(chat_id, "OM repair hammer"): OM_query_compile("reph", adventure_data),  # noqa: E501
                "🔧⛏ " + uistr.get(chat_id, "OM repair pick"): OM_query_compile("repp", adventure_data)}  # noqa: E501
            ]
        keys_owned = best.inventory_get(chat_id, "key")
        if (
                adventure_data["level"] % 100 in [51, 56] and
                keys_owned > 0 and
                player_data["record_level"] > (
                adventure_data["level"] // 100 + 1) * 100
        ):
            keyboard += [{
                "🗝" + uistr.get(chat_id, "OM use key").format(
                    owned=keys_owned
                ): OM_query_compile("skey", adventure_data)  # noqa: E501
            }]
        player_data["record_level"] = max(
            player_data["record_level"], adventure_data["level"])
        dbw.give_money(chat_id, converted_prizes["money"])
        player_data["money_earnings"] += converted_prizes["money"]
        for block_type in gut.list["block"]:
            if converted_prizes[block_type] > 0:
                dbw.add_block(
                    chat_id,
                    conv.name(block=block_type)["currency"],
                    count=converted_prizes[block_type])
                player_data[
                    "mined_" + block_type] += converted_prizes[block_type]
        if "protections" in converted_prizes:
            player_data["protections"] += converted_prizes["protections"]
        best.mini_up_player(chat_id, "Ore Miner", player_data)
    else:
        if adventure_data["hammer_uses"] >= hammer_max_uses:
            message += uistr.get(chat_id, "OM broken hammer")
            return message, death_keyboard, None
        if adventure_data["pick_uses"] >= pick_max_uses:
            message += uistr.get(chat_id, "OM broken pick")
            return message, death_keyboard, None
        message += uistr.get(chat_id, "OM continue")

        fast_hammer = OM_fast_hammer(
            adventure_data, player_data["record_level"])
        if fast_hammer < 2:
            keyboard = [{
                "🔨 " + uistr.get(chat_id, "OM use hammer"): OM_query_compile("hmmr", adventure_data),  # noqa: E501
                "⛏" + uistr.get(chat_id, "OM use pick"): OM_query_compile("pick", adventure_data)  # noqa: E501
            }]
        else:
            keyboard = [{
                "🔨 " + uistr.get(chat_id, "OM use hammer"): OM_query_compile("hmmr", adventure_data),   # noqa: E501
                str(fast_hammer) + " x 🔨": OM_query_compile("fsth", adventure_data),   # noqa: E501
                "⛏" + uistr.get(chat_id, "OM use pick"): OM_query_compile("pick", adventure_data)  # noqa: E501
            }]
    keyboard.append({uistr.get(chat_id, "OM exit"): OM_query_compile("exit", adventure_data)})  # noqa: E501
    return message, keyboard, None


# == INVESTMENT PLAN ==
'''
Global data
    game_timestamp: N
    last_line_timestamp: N
    Companies: M
        level: N
        faction: S

User data
    last_investment_timestamp: N
    current_option: N

'''


ip_period = (60 * (60 * 36 + 9) + 27)  # 36h, 9m, 27 secs
# ip_period = (20*60)  # test time
player_base_period = (60 * (60 * 1 + 45))  # 1h, 45m
# player_base_period = (2*60)  # test time
ipv3_origin_timestamp = int(time.mktime((2022, 4, 28, 22, 0, 0, 0, 0, 0)))
# test time
# ipv3_origin_timestamp = int(time.mktime((2022, 4, 28, 0, 0, 0, 0, 0, 0)))

gamemode_cycle_period = 8


def IP_get_gamemode():
    game_id = (
        (dbr.mini_get_general("Investment Plan")["game_timestamp"] - ipv3_origin_timestamp) //
        (ip_period)
    )
    cycle_id = game_id // gamemode_cycle_period
    rgen = random.Random(cycle_id)
    time_mode = ["Timed", "Instant"] * (gamemode_cycle_period // 2)
    econ_mode = ["Capitalist", "Socialist"] * (gamemode_cycle_period // 2)
    rgen.shuffle(time_mode)
    rgen.shuffle(econ_mode)
    mode_id = game_id % gamemode_cycle_period

    return (
        time_mode[mode_id], econ_mode[mode_id]
    )


def IP_game_start(start_time):
    game_data = {"Companies": {}, "key": "Investment Plan"}
    game_data["game_timestamp"] = start_time
    for company in "ABCDEFGHIJKL":
        game_data["Companies"][company] = {
            "level": 0,
            "faction": "No"
        }
    dbw.mini_up_general(game_data)


def IP_accessibility():
    game_ts = dbr.mini_get_general("Investment Plan")["game_timestamp"]
    rroundgen = random.Random(game_ts)
    rhourgen = random.Random(gut.time_s() // 3600)
    state = {i: "accessible" for i in "ABCDEFGHIJKL"}
    # With probs 0.05 and 0.08, the probability of a cell being free is 0.874
    # With prob 0.1, every hour there's a prob of 0.718 that at least a cell is
    #  temporarily locked (not counting for the ones affected by round effects)
    for company in "ABCDEFGHIJKL":
        if rhourgen.random() < 0.1:
            state[company] = "hour_lock"
        if rroundgen.random() < 0.05:
            state[company] = "round_lock"
        if rroundgen.random() < 0.08:
            state[company] = "invisible"
    # If all cells are affected (very rare, 0.213^12), free one up
    if "accessible" not in state.values():
        state[rhourgen.choice("ABCDEFGHIJKL")] = "accessible"
    return state


def IP_player_prices(chat_id, companies="ABCDEFGHIJKL", deal=0):
    game_data = dbr.mini_get_general("Investment Plan")
    gamemode = IP_get_gamemode()
    if "Capitalist" in gamemode:
        faction_denominator = 1
    elif "Socialist" in gamemode:
        currencies_status = dbr.get_currencies_status()
        cur_order = [(i, currencies_status[i]) for i in currencies_status]
        cur_order = sorted(cur_order, key=lambda item: item[1], reverse=True)
        denominators = {}
        for i in range(len(cur_order)):
            denominators[cur_order[i][0]] = i + 1
        player_cur = best.get_types_of(chat_id)["currency"]
        faction_denominator = denominators[player_cur]

    player_prod = best.get_production(chat_id)

    # To multiply to the company level
    linear_price = (player_prod // 6) / faction_denominator * tv.IP_price_pity(
        chat_id)

    low_bound = int(max([
        game_data["Companies"][comp]["level"]
        for comp in game_data["Companies"]
    ]) * .8)

    # To multiply to (difference between low_bound and selected lvl)^exponent
    exp_price = (player_prod // 6) / faction_denominator * tv.IP_price_pity(
        chat_id)

    if len(companies) > 1:
        prices = {}
        for cy in companies:
            try:
                diff_to_bound = max(game_data["Companies"][cy]["level"] - low_bound, 0)
                prices[cy] = best.apply_discount(
                    game_data["Companies"][cy]["level"] * linear_price +
                    diff_to_bound ** (1 + diff_to_bound / 200) * exp_price,
                    chat_id=chat_id)
            except OverflowError:
                prices[cy] = dbr.login(chat_id)["balance"] + dbr.login(
                    chat_id)["balance"] // 10
        return prices
    else:
        try:
            diff_to_bound = max(game_data["Companies"][companies]["level"] - low_bound, 0)
            return best.apply_discount(
                (game_data["Companies"][companies]["level"] * linear_price +
                 diff_to_bound ** (1 + diff_to_bound / 200) * exp_price) * max(1, deal),
                chat_id=chat_id, deal=(deal > 0))
        except OverflowError:
            return dbr.login(chat_id)["balance"] + dbr.login(
                chat_id)["balance"] // 10


# Use after Investing
def IP_player_prizes(chat_id, companies="ABCDEFGHIJKL", deal=0):
    game_data = dbr.mini_get_general("Investment Plan")
    if len(companies) > 1:
        prizes = {}
        for cy in companies:
            prizes[cy] = best.apply_block_bonus(
                game_data["Companies"][cy]["level"] * 4,
                chat_id=chat_id
            )
        return prizes
    else:
        return best.apply_block_bonus(
            game_data["Companies"][companies]["level"] * 4 * max(1, deal),
            chat_id=chat_id,
            deal=(deal > 0)
        )


# A B C D
# E F G H
# I J K L
def IP_market_prizes():
    game_data = dbr.mini_get_general("Investment Plan")
    prizes = {faction: 0 for faction in gut.list["membership"]}
    for company in game_data["Companies"]:
        faction = game_data["Companies"][company]["faction"]
        if faction != "No":
            prizes[faction] += game_data["Companies"][company]["level"] * 5
    trios = [
        "ABC", "BCD", "EFG", "FGH", "IJK", "JKL",   # horizontals
        "AEI", "BFJ", "CGK", "DHL",                 # verticals
        "AFK", "BGL", "CFI", "DGJ"                  # diagonals
    ]
    trios_report = {}
    for trio in trios:
        faction = game_data["Companies"][trio[0]]["faction"]
        if (faction == "No" or
           game_data["Companies"][trio[1]]["faction"] != faction or
           game_data["Companies"][trio[2]]["faction"] != faction):
            trios_report[trio] = {"blocks": 0, "faction": "No"}
        else:
            reward = 40 * min([
                game_data["Companies"][cy]["level"] for cy in trio])
            trios_report[trio] = {"blocks": reward, "faction": faction}
            prizes[faction] += reward
    return prizes, trios_report


def IP_does_tris(chat_id, company):
    pfaction = dbr.login(chat_id)["membership"]
    game_data = dbr.mini_get_general("Investment Plan")
    _, trios_report = IP_market_prizes()
    for trio in trios_report:
        if company not in trio:
            continue
        if trios_report[trio]["faction"] != "No":
            continue
        missing = ""
        for c in trio:
            if game_data["Companies"][c]["faction"] != pfaction:
                missing += c
        if missing == company:
            return True
    return False


def IP_tris_prize(chat_id, deal=False):
    game_data = IP_check_game()
    time_enlapsed = gut.time_s() - game_data["last_line_timestamp"]
    highest_level = max([
        game_data["Companies"][comp]["level"]
        for comp in game_data["Companies"]
    ])
    low_bound = int(sum([
        game_data["Companies"][comp]["level"]
        for comp in game_data["Companies"]
    ]) / 12)
    rate_minute = int(highest_level - low_bound)
    base_prize = int(
        time_enlapsed * rate_minute / 60
    )

    return best.apply_block_bonus(
        base_prize, chat_id=chat_id, deal=deal), best.apply_block_bonus(
        rate_minute, chat_id=chat_id)


def IP_game_end():
    prizes, _ = IP_market_prizes()
    for market in gut.list["block"]:
        market_data = dbr.get_market_data(market)
        market_data["blocks"] += prizes[conv.name(block=market)["membership"]]
        dbw.market_update(market, market_data)


def IP_check_game():
    current_time = gut.time_s()
    if current_time < ipv3_origin_timestamp:
        return "WIP"
    game_data = dbr.mini_get_general("Investment Plan")
    if ("game_timestamp" not in game_data or
       current_time > game_data["game_timestamp"] + ip_period):
        if "game_timestamp" in game_data:
            IP_game_end()
            new_time = game_data["game_timestamp"]
        else:
            new_time = ipv3_origin_timestamp
        while current_time > new_time + ip_period:
            new_time += ip_period
        IP_game_start(new_time)
        game_data = dbr.mini_get_general("Investment Plan")
    if "last_line_timestamp" not in game_data:
        game_data["last_line_timestamp"] = current_time
        dbw.mini_up_general(game_data)
    last_line_timestamp = game_data["last_line_timestamp"]
    game_timestamp = game_data["game_timestamp"]
    if last_line_timestamp < game_timestamp:
        game_data["last_line_timestamp"] = game_data["game_timestamp"]
        dbw.mini_up_general(game_data)
    return game_data


def ui_IP_invest_keyboard(game_data):
    keyboard = []
    access_state = IP_accessibility()
    for rowcys in ["ABCD", "EFGH", "IJKL"]:
        row = {}
        for company in rowcys:
            key = company + ": "
            if access_state[company] == "round_lock":
                key += "⛔️"
            elif access_state[company] == "invisible":
                key += "???"
            else:
                if access_state[company] == "hour_lock":
                    key += "⏳"
                key += str(game_data["Companies"][company]["level"]) + " "
                if game_data["Companies"][company]["faction"] != "No":
                    key += conv.name(
                        membership=game_data["Companies"][company]["faction"])[
                        "badgemoji"]
            row[key] = "IP invest " + company
        keyboard.append(row)
    return keyboard


def IP_player_investment_options(chat_id):
    game_data = IP_check_game()
    gear_level = dbr.login(chat_id)["gear_level"]
    player_faction = dbr.login(chat_id)["membership"]
    gamemode = IP_get_gamemode()

    fcc = 0
    general_average = 0
    faction_average = 0
    for comp in game_data["Companies"]:
        if game_data["Companies"][comp]["faction"] == player_faction:
            fcc += 1
            faction_average += game_data["Companies"][comp]["level"]
        general_average += game_data["Companies"][comp]["level"]

    general_average /= 12
    if fcc > 1:
        faction_average /= fcc

    base_0 = int(min(
        faction_average // 100 + 1,
        gear_level // 10 + 1
    ))
    base_1 = int(min(
        faction_average + 5,
        gear_level // 5 + 5
    ))
    base_2 = int(min(
        general_average + 1,
        gear_level // 2 + 1
    ))
    base_3 = int(min([
        general_average + 20,
        gear_level + 1,
        100
    ]
    ))
    ei = int(economy_inflation(chat_id))
    base_options = [
        max(1, base_0 + (ei // 25)),
        max(1, base_1 + (ei // 10)),
        max(1, base_2 + (ei // 3)),
        max(1, base_3 + (ei))
    ]
    if "Instant" in gamemode:
        maximum = max(base_options)
        return [
            max(1, base_0 + (ei // 25)),
            max(1, maximum // 10 + base_0 + (ei // 10)),
            max(1, maximum // 4 + base_0 + (ei // 3)),
            max(1, maximum + base_0 + (ei))
        ]
    else:
        options = base_options.copy()
        if base_options[2] <= base_options[1]:
            options.remove(base_options[2])
        if base_options[3] <= base_options[1]:
            options.remove(base_options[3])
        return options


def ui_IP_investment_options_keyboard(chat_id):
    curopt = best.mini_get_player(chat_id, "Investment Plan")["current_option"]
    options = IP_player_investment_options(chat_id)
    if curopt >= len(options):
        curopt = len(options) - 1

    opt_strings = ["" for _ in range(len(options))]
    for i in range(len(options)):
        if curopt == i:
            opt_strings[i] += "🔘 "
        opt_strings[i] += str(options[i])

    return [{opt_strings[i]: "IP option " + str(i)
            for i in range(len(options))}]


def ui_IP_time_left_general(chat_id, game_timestamp):
    current_sec_left = (
        ip_period - (gut.time_s() - game_timestamp))
    hours = int(current_sec_left // (60 * 60))
    if hours > 0:
        return uistr.get(chat_id, "IP time about").format(h1=hours, h2=hours + 1)
    else:
        return uistr.get(chat_id, "IP time less1h")


def IP_player_period(chat_id):
    currencies_status = dbr.get_currencies_status()
    cur_order = [(i, currencies_status[i]) for i in currencies_status]
    cur_order = sorted(cur_order, key=lambda item: item[1], reverse=True)
    denominators = {}
    for i in range(len(cur_order)):
        denominators[cur_order[i][0]] = i + 1

    player_cur = best.get_types_of(chat_id)["currency"]
    return int(
        player_base_period /
        (denominators[player_cur] * tv.IP_turn_multiplier())
    )


# Assumes player already moved (aka can't invest)
def ui_IP_time_left_player(chat_id, game_timestamp):
    game_sec_left = (
        ip_period - (gut.time_s() - game_timestamp))
    player_period = IP_player_period(chat_id)
    if game_sec_left <= player_period:
        return uistr.get(chat_id, "IP no more turns")
    current_sec_left = (
        player_period -
        ((gut.time_s() - game_timestamp) % player_period))
    minutes = (current_sec_left + 30) // 60
    return uistr.get(chat_id, "IP next action time").format(minutes=minutes)


def IP_Instant_current_company(chat_id, game_timestamp):
    turn = 1 + (gut.time_s() - game_timestamp) // IP_player_period(chat_id)
    starting_company = (chat_id + game_timestamp // ip_period) % 12
    step = (game_timestamp // ip_period) % 11 + 1
    shift_step = {
        1: 12000,
        2: 6,
        3: 4,
        4: 3,
        5: 12000,
        6: 2,
        7: 12000,
        8: 3,
        9: 4,
        10: 6,
        11: 12000
    }[step]
    return "ABCDEFGHIJKL"[(
        starting_company + turn * step + turn // shift_step
    ) % len("ABCDEFGHIJKL")]


def ui_IP_time_left_instant(chat_id, game_timestamp):
    game_sec_left = (
        ip_period - (gut.time_s() - game_timestamp))
    player_period = IP_player_period(chat_id)
    if game_sec_left <= player_period:
        return uistr.get(chat_id, "IP Instant no more turns")
    current_sec_left = (
        player_period -
        ((gut.time_s() - game_timestamp) % player_period))
    minutes = (current_sec_left + 30) // 60
    return uistr.get(chat_id, "IP next company time").format(minutes=minutes)


def IP_player_can_invest(chat_id, game_timestamp):
    gamemode = IP_get_gamemode()
    if "Timed" not in gamemode:
        return True

    player_data = best.mini_get_player(chat_id, "Investment Plan")
    current_time = gut.time_s()
    player_period = IP_player_period(chat_id)
    if player_data["last_investment_timestamp"] < game_timestamp:
        return True
    player_vote_turn = int(
        (player_data["last_investment_timestamp"] - game_timestamp) /
        player_period)
    current_vote_turn = int(
        (current_time - game_timestamp) /
        player_period)
    return player_vote_turn < current_vote_turn


def IP_game_emoji(chat_id, game_timestamp):
    gamemode = IP_get_gamemode()
    if "Timed" in gamemode:
        return IP_player_can_invest(chat_id, game_timestamp)

    player_data = best.mini_get_player(chat_id, "Investment Plan")
    current_time = gut.time_s()
    player_period = IP_player_period(chat_id)
    if player_data["last_investment_timestamp"] < game_timestamp:
        return True
    player_vote_turn = int(
        (player_data["last_investment_timestamp"] - game_timestamp) /
        player_period)
    current_vote_turn = int(
        (current_time - game_timestamp) /
        player_period)
    return player_vote_turn < current_vote_turn


def ui_IP_main_screen(chat_id):
    game_data = IP_check_game()
    if game_data == "WIP":
        return "🚧🚧⛔️🚧🚧", [{uistr.get(chat_id, "button back"): "Main menu"}]
    message = uistr.get(chat_id, "IP welcome").format(
        time_left_general=ui_IP_time_left_general(
            chat_id, game_data["game_timestamp"]))
    gamemode = IP_get_gamemode()
    message += uistr.get(
        chat_id, "IP gamemode " + gamemode[0] + "_" + gamemode[1])
    if "Timed" in gamemode:
        if IP_player_can_invest(chat_id, game_data["game_timestamp"]):
            message += uistr.get(chat_id, "IP your turn")
        else:
            message += ui_IP_time_left_player(
                chat_id, game_data["game_timestamp"])
    elif "Instant" in gamemode:
        message += uistr.get(chat_id, "IP your company").format(
            cid=IP_Instant_current_company(
                chat_id, game_data["game_timestamp"])
        )
        message += ui_IP_time_left_instant(
            chat_id, game_data["game_timestamp"])
        if IP_game_emoji(chat_id, game_data["game_timestamp"]):
            player_data = best.mini_get_player(chat_id, "Investment Plan")
            player_data["last_investment_timestamp"] = gut.time_s()
            best.mini_up_player(chat_id, "Investment Plan", player_data)

    tris_prize, tris_prize_rate = IP_tris_prize(chat_id)
    message += uistr.get(chat_id, "IP tris prize").format(
        current=put.pretty(tris_prize),
        rate=tris_prize_rate
    )
    keyboard = ui_IP_invest_keyboard(game_data)
    keyboard += ui_IP_investment_options_keyboard(chat_id)

    keyboard.append({
        uistr.get(chat_id, "IP button info"): "IP info",
        uistr.get(chat_id, "button back"): "Main menu"})

    return message, keyboard


def ui_IP_info_screen(chat_id):
    game_data = IP_check_game()
    access_state = IP_accessibility()
    message = "..:." * 19 + ".\n"

    low_bound = sum([
        game_data["Companies"][comp]["level"]
        for comp in game_data["Companies"]
    ]) / 12

    message += uistr.get(chat_id, "IP info prices")
    prices = IP_player_prices(chat_id)
    message += "`"
    for rowcys in ["ABCD", "EFGH", "IJKL"]:
        for company in rowcys:
            if access_state[company] == "round_lock":
                continue
            if access_state[company] == "invisible":
                line = company + ": ??? "
            else:
                line = company + ": " + put.pretty(prices[company]) + " "
                if game_data["Companies"][company]["level"] > low_bound + 10:
                    line += "!"
            message += line + " " * (10 - len(line))
        message += "\n"
    message += "`" + uistr.get(chat_id, "IP info extra price") + "\n"

    message += uistr.get(chat_id, "IP info market prizes")
    prizes, trios = IP_market_prizes()
    message += "`"
    for t in trios:
        if True in [access_state[t[i]] == "round_lock" for i in range(3)]:
            continue
        if True in [access_state[t[i]] == "invisible" for i in range(3)]:
            message += t + ": ??? ???\n"
        else:
            message += (
                t + ": " + trios[t]["faction"] + " " +
                str(trios[t]["blocks"]) + "\n")
    message += "`"
    keyboard = ui_IP_invest_keyboard(game_data)
    keyboard += ui_IP_investment_options_keyboard(chat_id)

    keyboard.append({
        uistr.get(chat_id, "button back mini"): "IP main",
        uistr.get(chat_id, "button back"): "Main menu"})

    return message, keyboard


def ui_IP_option_select(chat_id, option):
    player_data = best.mini_get_player(chat_id, "Investment Plan")
    player_data["current_option"] = option
    best.mini_up_player(chat_id, "Investment Plan", player_data)
    return uistr.get(chat_id, "Done")


def ui_IP_invest(chat_id, sel_id):
    game_data = IP_check_game()
    access_state = IP_accessibility()
    if not IP_player_can_invest(chat_id, game_data["game_timestamp"]):
        return uistr.get(chat_id, "IP already invested")
    if access_state[sel_id] == "hour_lock":
        return uistr.get(chat_id, "IP hour locked")
    if access_state[sel_id] == "round_lock":
        return uistr.get(chat_id, "IP round locked")
    if "Instant" in IP_get_gamemode() and sel_id != IP_Instant_current_company(
            chat_id, game_data["game_timestamp"]):
        return uistr.get(chat_id, "IP not your company")
    membership = best.get_types_of(chat_id)["membership"]

    curopt = best.mini_get_player(chat_id, "Investment Plan")["current_option"]
    options = IP_player_investment_options(chat_id)
    if curopt >= len(options):
        curopt = len(options) - 1
    investment_quantity = options[curopt]

    # returns the int price when input is 1 letter
    price = IP_player_prices(
        chat_id,
        companies=sel_id,
        deal=investment_quantity)
    if not dbr.check_payment(chat_id, price):
        return uistr.get(chat_id, "Insufficient balance")

    if IP_does_tris(chat_id, sel_id):
        tris_prize = IP_tris_prize(chat_id, deal=True)[0]
        game_data["last_line_timestamp"] = gut.time_s()
    else:
        tris_prize = 0

    if game_data["Companies"][sel_id]["faction"] != "No":
        '''
        if best.get_market_impulse() < 0.5:
            market_section = conv.name(
                membership=game_data["Companies"][sel_id]["faction"])["block"]
            market_data = dbr.get_market_data(market_section)
            market_data["money"] += int(price // 2)
            market_data["money_limit"] += int(price - price // 2)
            dbw.market_update(market_section, market_data)
        '''
        dbw.pay_money(chat_id, price)  # Should be free if it were "No"

    game_data["Companies"][sel_id]["faction"] = membership
    game_data["Companies"][sel_id]["level"] += investment_quantity
    dbw.mini_up_general(game_data)

    # returns the int number of blocks when input is 1 letter
    prize = IP_player_prizes(
        chat_id,
        companies=sel_id,
        deal=investment_quantity)
    dbw.add_block(
        chat_id, conv.name(membership=membership)["currency"],
        prize + tris_prize
    )
    player_data = best.mini_get_player(chat_id, "Investment Plan")
    player_data["last_investment_timestamp"] = gut.time_s()
    best.mini_up_player(chat_id, "Investment Plan", player_data)

    return uistr.get(chat_id, "IP invested").format(prize=prize + tris_prize)


# == COINOPOLY ==
'''
Global data
    Coins: M
        <name>: S (using float.hex() and float.fromhex())
    Houses: M
        <cell_num>: M
            chat_id: N
            level: N

User data
    Coins: M
        <name>: S (using float.hex() and float.fromhex())
    Position: N
    State: S            [landed, acted]
    Last Movement Timestamp: N

'''

cp_period = 60 * 60  # one hour
cp_min_val = 0.00000001
cp_map = [
    "storehouse",  # -------------
    "Solana",
    "Litecoin",
    "Polkadot",
    "Terra",
    "BitTorrent",
    "Shiba",
    "Dogecoin",
    "Solana",  # -----
    "Filecoin",
    "Terra",
    "BitTorrent",
    "IdleCoin",
    "IdleCoin",
    "Dogecoin",
    "Bitcoin",
    "storehouse",  # -------------
    "Ada",
    "Litecoin",
    "Polkadot",
    "Terra",
    "Shiba",
    "Shiba",
    "Dogecoin",
    "Polkadot",  # -----
    "Filecoin",
    "Filecoin",
    "Tether",
    "Tether",
    "Tether",
    "Dogecoin",
    "Ether",
    "storehouse",  # -------------
    "Ada",
    "Litecoin",
    "Polkadot",
    "Terra",
    "Shiba",
    "Solana",
    "Dogecoin",
    "Solana",  # -----
    "Filecoin",
    "BitTorrent",
    "BitTorrent",
    "Tether",
    "IdleCoin",
    "Dogecoin",
    "Ether",
    "storehouse",  # -------------
    "Ada",
    "Litecoin",
    "Polkadot",
    "Shiba",
    "Shiba",
    "Solana",
    "Dogecoin",
    "Polkadot",  # -----
    "Filecoin",
    "Terra",
    "BitTorrent",
    "BitTorrent",
    "Solana",
    "Dogecoin",
    "Ether"
]


def CP_storehouse_crypto_counts(cell):
    counts = {}
    for cell_num in range(cell + 1, cell + 16):
        if cp_map[cell_num] not in counts:
            counts[cp_map[cell_num]] = 0
        counts[cp_map[cell_num]] += 1
    return counts


def CP_base_player_value(chat_id):
    return best.get_base_production(chat_id)


def CP_crypto_sell_value(chat_id, coin_stock, coins):
    player_prod = CP_base_player_value(chat_id)
    return int((coins * 10 * player_prod / 12) / coin_stock)


def CP_buy_crypto(chat_id, coin_name, delta, money_spent_by_player):
    game_data = dbr.mini_get_general("Coinopoly")
    coin_stock = float.fromhex(game_data["Coins"][coin_name])

    game_data["Coins"][coin_name] = float.hex(max(coin_stock - delta, 0))
    game_data["Money"][coin_name] += max(money_spent_by_player, 0)
    dbw.mini_up_general(game_data)
    return uistr.get(chat_id, "Done")


def CP_sell_crypto(chat_id, coin_name, quantity):
    game_data = dbr.mini_get_general("Coinopoly")
    coin_stock = float.fromhex(game_data["Coins"][coin_name])

    prize_money = CP_crypto_sell_value(chat_id, coin_stock, quantity)
    dbw.give_money(chat_id, prize_money)
    game_data["Coins"][coin_name] = float.hex(coin_stock + quantity)
    game_data["Money"][coin_name] -= min(prize_money, game_data["Money"][coin_name] // 2)
    dbw.mini_up_general(game_data)
    return uistr.get(chat_id, "Done")


def CP_options_prices(chat_id, option_string):
    player_cur = best.get_types_of(chat_id)["currency"]
    player_prod = CP_base_player_value(chat_id)
    if option_string == "buy 1/10" or option_string == "buy":
        base_price = player_prod // 12  # 5 minutes of production
        qty_multiplier = 1
    if option_string == "buy 1/5":
        base_price = player_prod // 3  # 20 minutes of production
        qty_multiplier = 2
    if option_string == "buy 1/2":
        base_price = player_prod * 3  # 3 hours of production
        qty_multiplier = 5
    converted_price = best.apply_discount(
        base_price, player_cur)
    return converted_price, qty_multiplier


def CP_mine():
    return random.random()**4 * 30 + 0.1


def CP_player_available_actions(chat_id, player_data):
    actions = []
    player_time = player_data["timestamp"]
    cell_type = cp_map[player_data["position"]]
    if gut.time_s() // cp_period == player_time // cp_period:
        if player_data["state"] == "landed":
            if cell_type != "storehouse":
                actions.append("buy")
                actions.append("sell")
                actions.append("mine")
            actions.append("build")
        if best.inventory_get(chat_id, "dice") > 0:
            actions.append("dice")
    else:
        actions.append("move")
    return actions


# Data based on the current level
def CP_house_data(chat_id, coin_name, cur_level):
    shown_level = (cur_level + 9 + int(max(economy_inflation(chat_id), 0))) // 10
    cells_num = cp_map.count(coin_name)
    exponential_base = int(shown_level ** (1.8 - cells_num / 10))

    building_cost = exponential_base * 10 + 10
    target_build_level = shown_level * 10 + 10
    payment_to_stock = target_build_level + (building_cost - target_build_level) // 2

    block_prize = exponential_base * 5

    return building_cost, target_build_level, payment_to_stock, block_prize


def CP_sell_quantity(chat_id, cur_cell, cur_house, in_pocket):
    game_data = dbr.mini_get_general("Coinopoly")
    if cur_house["chat_id"] == chat_id:
        quantity = in_pocket
    else:
        building_cost, _, _, _ = CP_house_data(chat_id, cur_cell, cur_house["level"])
        if abs(building_cost - in_pocket) < cp_min_val:
            quantity = in_pocket
        else:
            quantity = min(building_cost, in_pocket)

    stored_money = game_data["Money"][cur_cell]
    coin_stock = float.fromhex(game_data["Coins"][cur_cell])
    if in_pocket > 1:
        coin_price = float(CP_crypto_sell_value(chat_id, coin_stock, in_pocket)) / in_pocket
    else:
        coin_price = CP_crypto_sell_value(chat_id, coin_stock, 1)
    if coin_price > 0:
        max_sellable = float(stored_money // 2) / coin_price
        quantity = min(quantity, max_sellable)
    return quantity


def ui_CP_player_action(chat_id, action):
    player_data = best.mini_get_player(chat_id, "Coinopoly")
    available_actions = CP_player_available_actions(chat_id, player_data)
    cell_type = cp_map[player_data["position"]]

    if action == "build" and "build" in available_actions:
        if cell_type == "storehouse":
            game_data = dbr.mini_get_general("Coinopoly")
            cur_house = game_data["Houses"][
                str(player_data["position"])]
            inflation_multiplier = (1 + max(0, economy_inflation(chat_id)) / 100)
            new_level = int(
                cur_house["level"] * inflation_multiplier +
                19) // 10 * 10
            money_to_pay = int(CP_base_player_value(chat_id) *
                               cur_house["level"] * inflation_multiplier / 600)
            money_to_pay = best.apply_discount(
                money_to_pay,
                best.get_types_of(chat_id)["currency"]
            )
            if not dbr.check_payment(chat_id, money_to_pay):
                return uistr.get(chat_id, "Insufficient balance"), None
            dbw.pay_money(chat_id, money_to_pay)
            player_data["state"] = "acted"
            best.mini_up_player(chat_id, "Coinopoly", player_data)
            game_data["Houses"][str(player_data["position"])] = {
                "chat_id": chat_id,
                "level": new_level
            }
            shcp = CP_storehouse_crypto_counts(player_data["position"])
            for coin in shcp:
                game_data["Money"][coin] += shcp[coin] * money_to_pay // 16
            dbw.mini_up_general(game_data)
            return uistr.get(chat_id, "Done"), None

        else:
            game_data = dbr.mini_get_general("Coinopoly")
            coin_stock = float.fromhex(game_data["Coins"][cell_type])
            cur_house = game_data["Houses"][
                str(player_data["position"])]
            building_cost, target_build_level, payment_to_stock, _ = CP_house_data(chat_id, cell_type, cur_house["level"])
            if float.fromhex(player_data[
                    "Coins"][cell_type]) <= building_cost:
                return uistr.get(chat_id, "Insufficient balance"), None
            player_data["Coins"][cell_type] = float.hex(
                float.fromhex(player_data["Coins"][cell_type]) -
                building_cost
            )
            player_data["state"] = "acted"
            best.mini_up_player(chat_id, "Coinopoly", player_data)
            game_data["Coins"][cell_type] = float.hex(
                float.fromhex(game_data["Coins"][cell_type]) +
                payment_to_stock * (1 - tv.CP_coin_tax())
            )
            game_data["Houses"][str(player_data["position"])] = {
                "chat_id": chat_id,
                "level": target_build_level
            }
            dbw.mini_up_general(game_data)
            return uistr.get(chat_id, "Done"), None

    if "buy" in action and "buy" in available_actions:
        converted_price, qty_multiplier = CP_options_prices(
            chat_id, action)
        # payment
        if not dbr.check_payment(chat_id, converted_price):
            return uistr.get(chat_id, "Insufficient balance"), None
        r = dbw.pay_money(chat_id, converted_price)
        if r != "Ok":
            return uistr.get(chat_id, "Internal error"), None
        # coin exchange
        game_data = dbr.mini_get_general("Coinopoly")
        coin_stock = float.fromhex(game_data["Coins"][cell_type])
        delta = coin_stock / 10 * qty_multiplier
        player_data["Coins"][cell_type] = float.hex(
            float.fromhex(player_data["Coins"][cell_type]) + delta
        )
        player_data["state"] = "acted"
        best.mini_up_player(chat_id, "Coinopoly", player_data)
        return CP_buy_crypto(chat_id, cell_type, delta, converted_price), None

    if action == "mine" and "mine" in available_actions:
        mining_prize = CP_mine()
        player_data["Coins"][cell_type] = float.hex(
            float.fromhex(player_data["Coins"][cell_type]) + mining_prize
        )
        player_data["state"] = "acted"
        best.mini_up_player(chat_id, "Coinopoly", player_data)
        return uistr.get(chat_id, "CP mining").format(
            qty=ui_CP_cryptoprint(mining_prize)), None

    if action == "sell" and "sell" in available_actions:
        in_pocket = float.fromhex(player_data["Coins"][cell_type])
        game_data = dbr.mini_get_general("Coinopoly")
        cur_house = game_data["Houses"][str(player_data["position"])]
        quantity = CP_sell_quantity(chat_id, cell_type, cur_house, in_pocket)
        new_player_pocket = in_pocket - quantity
        if new_player_pocket < cp_min_val:
            player_data["Coins"][cell_type] = float.hex(0.0)
        else:
            player_data["Coins"][cell_type] = float.hex(new_player_pocket)
        player_data["state"] = "acted"
        best.mini_up_player(chat_id, "Coinopoly", player_data)
        return CP_sell_crypto(chat_id, cell_type, quantity), None

    if action == "move" and (
            "move" in available_actions or "dice" in available_actions):
        dice_used = 1
        if "dice" in available_actions:
            ei = max(1, economy_inflation(chat_id))
            dice_used = int(ei ** .5)
            best.inventory_use(chat_id, "dice", min(dice_used, best.inventory_get(chat_id, "dice")))
        dieval = random.randint(1, 6)
        message = ("🎲 " +
                   uistr.get(chat_id, "CP roll").format(dieval=dieval) +
                   " 🎲\n\n")
        player_data["position"] = (dieval +
                                   player_data["position"]) % len(cp_map)
        player_data["state"] = "landed"
        player_data["timestamp"] = gut.time_s()
        best.mini_up_player(chat_id, "Coinopoly", player_data)
        new_cell_type = cp_map[player_data["position"]]
        if new_cell_type == "storehouse":
            coin_count = 0
            for coin in player_data["Coins"]:
                if float.fromhex(player_data["Coins"][coin]) > 2:
                    coin_count += int(math.log2(float.fromhex(player_data["Coins"][coin])))
            if coin_count > 0:
                prize = coin_count * dice_used
                dbw.add_block(
                    chat_id, best.get_types_of(chat_id)["currency"],
                    best.apply_block_bonus(
                        prize,
                        chat_id=chat_id,
                        deal=True)
                )
                message += uistr.get(
                    chat_id,
                    "CP landon storehouse").format(blocks=prize)
            else:
                message += uistr.get(
                    chat_id, "CP landon storehouse nocoin")
            notifications = []
            game_data = dbr.mini_get_general("Coinopoly")
            cur_house = game_data["Houses"][str(player_data["position"])]

            # Storehouse owner prize
            if cur_house["level"] > 0 and cur_house["chat_id"] > 0:
                message += uistr.get(chat_id, "CP landon house")
                chl = game_data["Houses"][str(player_data["position"])]["level"]
                game_data["Houses"][str(player_data["position"])]["level"] = max(
                    chl - tv.CP_house_degrade() * dice_used *
                    max(1, chl // 100),
                    chl // 1000
                )
                dbw.mini_up_general(game_data)
                if cur_house["chat_id"] == chat_id:
                    message += uistr.get(
                        chat_id, "CP landon your house")
                    if random.random() < (.2 *
                       best.mystery_item_base_probability(chat_id)):
                        best.inventory_give(chat_id, "mystery_item", 1)
                        message += "\n\n" + uistr.get(
                            chat_id, "found mystery item")
                else:  # Land on somebody else's house
                    if tv.is_on("CP Dice Pity"):
                        if random.random() < .3:
                            best.inventory_give(chat_id, "dice", 1)
                            message += uistr.get(
                                chat_id, "mystery prize dice").format(qty=1)
                    shcp = CP_storehouse_crypto_counts(player_data["position"])
                    owner_data = best.mini_get_player(cur_house["chat_id"], "Coinopoly")
                    exchanged_message = ""
                    for coin in shcp:
                        exchanged_value = shcp[coin] * float.fromhex(player_data["Coins"][coin]) / 100
                        if exchanged_value < cp_min_val:
                            continue
                        float.fromhex(player_data["Coins"][cell_type])
                        player_data["Coins"][coin] = float.hex(float.fromhex(player_data["Coins"][coin]) - exchanged_value)
                        owner_data["Coins"][coin] = float.hex(float.fromhex(owner_data["Coins"][coin]) + exchanged_value)
                        if len(exchanged_message) > 0:
                            exchanged_message += ", "
                        exchanged_message += ui_CP_cryptoprint(exchanged_value) + " " + coin
                    if len(exchanged_message) > 0:
                        best.mini_up_player(chat_id, "Coinopoly", player_data)
                        best.mini_up_player(cur_house["chat_id"], "Coinopoly", owner_data)
                    else:
                        exchanged_message = "0"
                    if dbr.login(cur_house["chat_id"])[
                            "settings"]["CP_notification"]:
                        notifications = [{
                            "chat_id": cur_house["chat_id"],
                            "message": uistr.get(
                                cur_house["chat_id"],
                                "CP notify storehouse house").format(
                                    cryptos=exchanged_message
                            )
                        }]
            return message, notifications
        else:  # not storehouse
            message += uistr.get(chat_id, "CP landon crypto")
            game_data = dbr.mini_get_general("Coinopoly")
            cur_house = game_data["Houses"][str(player_data["position"])]
            if cur_house["level"] > 0 and cur_house["chat_id"] > 0:
                _, _, _, blocks_won = CP_house_data(chat_id, new_cell_type, cur_house["level"])
                blocks_won = best.apply_block_bonus(
                    blocks_won * dice_used, chat_id=cur_house["chat_id"], deal=True)
                # Level of the previous storehouse, top in the board view
                storehouse_ref = 1 + game_data["Houses"][
                    str((player_data["position"] // 16) * 16)]["level"]
                if random.random() < cur_house["level"] / storehouse_ref:
                    chl = game_data["Houses"][str(player_data["position"])]["level"]
                    game_data["Houses"][str(player_data["position"])][
                        "level"] = max(chl - tv.CP_house_degrade() * dice_used, chl // 10)
                    dbw.mini_up_general(game_data)
                notifications = []
                if cur_house["chat_id"] == chat_id:
                    message += uistr.get(
                        chat_id, "CP landon your house").format(
                        blocks=blocks_won
                    )
                    if random.random() < (.2 *
                       best.mystery_item_base_probability(chat_id)):
                        best.inventory_give(chat_id, "mystery_item", 1)
                        message += "\n\n" + uistr.get(
                            chat_id, "found mystery item")
                else:
                    message += uistr.get(chat_id, "CP landon house")
                    if tv.is_on("CP Dice Pity"):
                        if random.random() < .3:
                            best.inventory_give(chat_id, "dice", 1)
                            message += uistr.get(
                                chat_id, "mystery prize dice").format(qty=1)
                    if dbr.login(cur_house["chat_id"])[
                            "settings"]["CP_notification"]:
                        notifications = [{
                            "chat_id": cur_house["chat_id"],
                            "message": uistr.get(
                                cur_house["chat_id"],
                                "CP notify house").format(
                                    blocks=blocks_won
                            )
                        }]
                dbw.add_block(cur_house["chat_id"], conv.name(
                    membership=dbr.login(cur_house["chat_id"])[
                        "membership"])["currency"], blocks_won)
                return message, notifications
            return message, None
        return message, None
    return uistr.get(chat_id, "CP error action not available"), None


def ui_CP_cellstr(chat_id, cell_num, id_str=None,
                  show_level=False, show_owned_by=None):
    cell_num = cell_num % len(cp_map)
    game_data = dbr.mini_get_general("Coinopoly")
    if cp_map[cell_num] == "storehouse":
        cell_name = uistr.get(chat_id, "CP cell storehouse")
        house_display_level = (
            game_data["Houses"][str(cell_num)]["level"] + 9) // 10
        if house_display_level > 0:
            house_str = "🏬"
        else:
            house_str = "--"
    else:
        cell_name = cp_map[cell_num]
        house_display_level = (
            game_data["Houses"][str(cell_num)]["level"] + 9) // 10
        if house_display_level == 0:
            house_str = "--"
        elif house_display_level < 5:
            house_str = "🏠"
        elif house_display_level < 10:
            house_str = "🏘"
        elif house_display_level < 20:
            house_str = "🏢"
        elif house_display_level < 50:
            house_str = "🏨"
        else:
            house_str = "🏙"
    if show_level:
        if house_display_level < 10:
            house_str += " " + str(house_display_level)
        else:
            house_str += str(house_display_level)
    if not id_str:
        if cell_num < 10:
            id_str = " " + str(cell_num)
        else:
            id_str = str(cell_num)

    owned = "  "
    if game_data["Houses"][str(cell_num)]["chat_id"] == show_owned_by:
        owned = "🚪"
    message = ("`" + id_str + owned + ":" + house_str + ": " + cell_name +
               "\n`")
    return message


def ui_CP_map(position, page, chat_id):
    message = ""
    for i in range(page * 16, (page + 1) * 16):
        if i == position:
            cellstr = ui_CP_cellstr(
                chat_id, i, id_str="🟢",
                show_level=True, show_owned_by=chat_id)
        else:
            cellstr = ui_CP_cellstr(
                chat_id,
                i, show_level=True, show_owned_by=chat_id)
        message += cellstr
    return message


def ui_CP_menu_map(chat_id, page):
    player_data = best.mini_get_player(chat_id, "Coinopoly")
    message = ".-" * 20 + ".\n"
    message += ui_CP_map(player_data["position"], page, chat_id)
    keyboard = [
        {
            "<": "CP map " + str((page + 3) % 4),
            ">": "CP map " + str((page + 1) % 4)
        },
        {
            uistr.get(chat_id, "CP button Wallet"): "CP list Wallet",
            uistr.get(chat_id, "CP button Stock"): "CP list Stock",
            uistr.get(chat_id, "CP button Price"): "CP list Price"
        },
        {uistr.get(chat_id, "button back mini"): "CP main"}
    ]
    return message, keyboard


def ui_CP_menu_list(chat_id, page):
    if page == "Price" or page == "Stock":
        game_data = dbr.mini_get_general("Coinopoly")
    if page == "Price":
        player_cursym = best.get_types_of(chat_id)["symbol"]
    if page == "Wallet":
        player_data = best.mini_get_player(chat_id, "Coinopoly")

    page_name = uistr.get(chat_id, "CP button " + page) + " "
    top_string = '|°°' * 10 + '|'

    message = page_name + top_string[len(page_name):] + '\n'
    for coin_name in ["Bitcoin", "Ether", "Ada", "Dogecoin",
                      "Polkadot", "Litecoin", "Solana",
                      "IdleCoin", "Filecoin", "Terra",
                      "Shiba", "BitTorrent", "Tether"]:
        message += "`" + coin_name + ":" + " " * (
            13 - len(coin_name)
        )
        if page == "Stock":
            coin_stock = float.fromhex(game_data["Coins"][coin_name])
            crpr = ui_CP_cryptoprint(coin_stock)
            message += crpr + " " * (8 - len(crpr)) + put.pretty(game_data["Money"][coin_name]) + " M"
        elif page == "Wallet":
            owned = float.fromhex(player_data["Coins"][coin_name])
            message += ui_CP_cryptoprint(owned)
        elif page == "Price":
            coin_stock = float.fromhex(game_data["Coins"][coin_name])
            price = CP_crypto_sell_value(chat_id, coin_stock, 1)
            # converted_price = best.apply_discount(price, player_cur)
            message += put.pretty(price) + " " + player_cursym
        message += "`\n"

    keyboard = [
        {
            uistr.get(chat_id, "CP button " + button): "CP list " + button
            for button in ["Wallet", "Stock", "Price"] if button != page
        },
        {
            uistr.get(chat_id, "CP button map"): "CP map 0",
            uistr.get(chat_id, "button back mini"): "CP main"
        }
    ]

    return message, keyboard


def ui_CP_cryptoprint(qty):
    if qty == 0.0:
        text = "0.0"
    elif qty < 10**-3:
        exp = int(math.log10(qty)) - 1
        shown = int(qty * (10**(1 - exp)) + 0.5)
        text = ""
        text += str(shown)[0] + "." + str(shown)[1]
        text += "(E" + str(exp) + ")"
    elif qty < 1:
        exp = int(math.log10(qty)) - 1
        shown = int(qty * (10**(1 - exp)) + 0.5)
        text = "0." + "0" * (-1 - exp)
        text += str(shown)
    elif qty < 10 - 0.05:
        text = str(qty + 0.05)[:3]
    elif qty < 10000:
        text = str(int(qty + 0.5))
    else:
        text = put.pretty(int(qty + 0.5))
    return text


def ui_CP_player_cells_count(chat_id, houses_data):
    count = 0
    for cell in range(len(cp_map)):
        if houses_data[str(cell)]["chat_id"] == chat_id:
            count += 1
    return "\n" + uistr.get(chat_id, "CP house count").format(num=count)


def ui_CP_main_screen(chat_id):
    game_data = dbr.mini_get_general("Coinopoly")
    player_cursym = best.get_types_of(chat_id)["symbol"]
    if len(game_data) == 0:
        game_data["key"] = "Coinopoly"
        game_data["Coins"] = {
            coin_name: float.hex(1000.0) for coin_name in [
                "Bitcoin", "Ether", "Ada", "Dogecoin",
                "Polkadot", "Litecoin", "Solana",
                "IdleCoin", "Filecoin", "Terra",
                "Shiba", "BitTorrent", "Tether"
            ]
        }
    if "Houses" not in game_data:
        game_data["Houses"] = {
            str(cell): {
                "chat_id": 0, "level": 0} for cell in range(len(cp_map))
        }
        game_data["Money"] = {
            coin_name: 1000000 for coin_name in [
                "Bitcoin", "Ether", "Ada", "Dogecoin",
                "Polkadot", "Litecoin", "Solana",
                "IdleCoin", "Filecoin", "Terra",
                "Shiba", "BitTorrent", "Tether"
            ]
        }
        dbw.mini_up_general(game_data)
    player_data = best.mini_get_player(chat_id, "Coinopoly")
    player_time = player_data["timestamp"]
    if gut.time_s() // cp_period == player_time // cp_period:
        message = ""
    else:
        message = uistr.get(chat_id, "CP welcome")

    for i in range(7):
        message += ui_CP_cellstr(
            chat_id,
            player_data["position"] + i,
            show_owned_by=chat_id)
    cur_cell = cp_map[(player_data["position"])]
    keyboard = []
    if cur_cell == "storehouse":
        message += uistr.get(chat_id, "CP in storehouse")
        if gut.time_s() // cp_period != player_time // cp_period:
            keyboard.append({
                uistr.get(chat_id, "CP button move"): "CP move"
            })
        elif player_data["state"] == "landed":
            cur_house = game_data["Houses"][
                str(player_data["position"])]
            new_level = (cur_house["level"] + 19) // 10 * 10
            inflation_multiplier = (1 + max(0, economy_inflation(chat_id)) / 100)
            money_to_pay = int(CP_base_player_value(chat_id) *
                               cur_house["level"] * inflation_multiplier / 600)
            money_to_pay = best.apply_discount(
                money_to_pay,
                best.get_types_of(chat_id)["currency"]
            )
            keyboard.append({
                uistr.get(chat_id, "CP button build").format(
                    price=put.pretty(money_to_pay)
                ): "CP build"
            })
    else:
        stored = float.fromhex(game_data["Coins"][cur_cell])
        in_pocket = float.fromhex(player_data["Coins"][cur_cell])
        message += "\n" + uistr.get(chat_id, "CP in coin").format(
            coin_name="`" + cur_cell + "`",
            qty_stock=stored,
            qty_player=in_pocket,
            price=put.pretty(CP_crypto_sell_value(chat_id, stored, 1))
        )
        if gut.time_s() // cp_period != player_time // cp_period:
            keyboard.append({
                uistr.get(chat_id, "CP button move"): "CP move"
            })
        elif player_data["state"] == "landed":
            keyboard.append(
                {uistr.get(chat_id, "CP button mine"): "CP mine"}
            )
            if stored > cp_min_val * 10:
                keyboard.append({
                    uistr.get(chat_id, "CP button buy main").format(
                        qty=ui_CP_cryptoprint(stored / 10),
                        price=put.pretty(
                            CP_options_prices(chat_id, "buy 1/10")[0]),
                        cur_sym=player_cursym
                    ): "CP buy 1/10"
                })
                keyboard.append({
                    uistr.get(chat_id, "CP button buy others").format(
                        qty=ui_CP_cryptoprint(stored / 5),
                        price=put.pretty(
                            CP_options_prices(chat_id, "buy 1/5")[0]),
                        cur_sym=player_cursym
                    ): "CP buy 1/5",
                    uistr.get(chat_id, "CP button buy others").format(
                        qty=ui_CP_cryptoprint(stored / 2),
                        price=put.pretty(
                            CP_options_prices(chat_id, "buy 1/2")[0]),
                        cur_sym=player_cursym
                    ): "CP buy 1/2"
                })
            cur_house = game_data["Houses"][str(player_data["position"])]
            if in_pocket > cp_min_val:
                quantity = CP_sell_quantity(chat_id, cur_cell, cur_house, in_pocket)
                if quantity > cp_min_val:
                    keyboard.append({
                        uistr.get(chat_id, "CP button sell").format(
                            qty=ui_CP_cryptoprint(quantity),
                            prize=put.pretty(
                                CP_crypto_sell_value(
                                    chat_id, stored, quantity)),
                            cur_sym=player_cursym
                        ): "CP sell"
                    })
            building_cost, _, _, _ = CP_house_data(chat_id, cur_cell, cur_house["level"])
            if float.fromhex(player_data[
                    "Coins"][cur_cell]) > building_cost:
                keyboard.append({
                    uistr.get(chat_id, "CP button build").format(
                        price=building_cost
                    ): "CP build"
                })

    message += ui_CP_player_cells_count(chat_id, game_data["Houses"])

    if gut.time_s() // cp_period == player_time // cp_period:
        if best.inventory_get(chat_id, "dice") > 0:
            keyboard.append({
                uistr.get(chat_id, "CP button extra dice").format(
                    qty=best.inventory_get(chat_id, "dice")
                ): "CP move"
            })
    keyboard.append({
        uistr.get(chat_id, "CP button map"): "CP map 0",
        uistr.get(chat_id, "button back"): "Main menu"
    })
    return message, keyboard


# == GLOBAL STEEL ROAD ==
'''
Global data
    Interactions: N     (count, gets used and reset every Capital)
    Sold Materials: N   (count, gets reset every city)
    Current Station: N
    Last Stop Timestamp: N
    Available Coal: N
    Factories: M    [key: <city_id><factory_letter between S,A,B,C,D,E and F>]
        Owner chat_id: N
        Value: N

User data
    Slots: S
    Last viewed menu: S     (so when the player opens GSR it goes to fav game)
                            (Either "Market" or "Factories")
    Last Investment Timestamp: N
    Investments in Last Station: N


'''


sr_data = json.load(open("global_steel_road.json"))


sr_dividends = {}


def SR_factories_dividend(station, redo=False):
    if station not in sr_dividends or redo:
        game_data = dbr.mini_get_general("Global Steel Road")
        tot_production = 0
        for fid in "SABCDEF":
            if game_data["Factories"][str(station) + fid][
               "owner_chat_id"] > 0:
                tot_production += best.get_base_production(game_data[
                    "Factories"][str(station) + fid]["owner_chat_id"])
        sr_dividends[station] = (
            tot_production * tv.GSRF_extra_divdeg()[0]
        ) // 60
    return sr_dividends[station]


def SR_position():
    game_data = dbr.mini_get_general("Global Steel Road")
    if len(game_data) == 0:
        game_data["key"] = "Global Steel Road"
        game_data["interactions"] = 0
        game_data["sold_materials"] = 0
        game_data["current_station"] = 0
        game_data["last_stop_timestamp"] = gut.time_s() // (5 * 60) * (5 * 60)
        game_data["available_coal"] = 0
        dbw.mini_up_general(game_data)
    if "Factories" not in game_data:
        game_data["Factories"] = {
            str(cid) + fid: {"owner_chat_id": 0, "value": 0}
            for cid in range(len(sr_data["itinerary"]))
            for fid in "SABCDEF"
        }
        dbw.mini_up_general(game_data)
    enlapsed_time = gut.time_s() - game_data["last_stop_timestamp"]
    coal = game_data["available_coal"]
    stations_passed = 0
    while True:
        if enlapsed_time < 5 * 60:
            state = "stop"
            break
        state = "going"
        enlapsed_time -= 5 * 60
        if coal > 5:
            coal -= 5
            stations_passed += 1
            game_data["last_stop_timestamp"] += 5 * 60
        else:
            if enlapsed_time >= (5 - coal) * 3 * 60:
                enlapsed_time -= (5 - coal) * 3 * 60
                stations_passed += 1
                game_data["last_stop_timestamp"] += (5 - coal) * 3 * 60 + 5 * 60
                coal = 0
            else:
                break
    # print("GSR could calculate stations to pass: ", stations_passed)
    start_time = time.time()
    if stations_passed > 0:
        game_data["sold_materials"] = 0
        blocks_for_market = {}
        money_awards = []
        for i in range(stations_passed):
            print(time.time() - start_time, "GSR passing station", i + 1)
            game_data["current_station"] = (game_data["current_station"] +
                                            1) % len(sr_data["itinerary"])
            do_degrade = False
            if game_data["interactions"] > 0:
                do_degrade = True
            if game_data["interactions"] > 0 and sr_data["itinerary"][
                    game_data["current_station"]]["type"] == "capital":
                market_section = conv.name(membership=sr_data["itinerary"][
                    game_data["current_station"]]["central bank"])["block"]
                if market_section not in blocks_for_market:
                    blocks_for_market[market_section] = 0
                blocks_for_market[market_section] += game_data["interactions"]
                game_data["interactions"] = 0
            for fid in "SABCDEF":
                factory = game_data["Factories"][
                    str(game_data["current_station"]) + fid]
                if factory["value"] > 0:
                    base_dividend = SR_factories_dividend(
                        game_data["current_station"], redo=True)
                    money_awards.append({
                        "station": game_data["current_station"],
                        "fid": fid,
                        "qty": int(factory["value"] * base_dividend)
                    })
                    if do_degrade:  # random.random()*7 < 1:
                        season_days_left = gut.time_till_next_season() // (60 * 60 * 24)
                        degrade_rate = (season_days_left / 100.0) ** 2
                        factory["value"] -= max(
                            int(factory["value"] * degrade_rate),
                            tv.GSRF_extra_divdeg()[1]
                        )
                if factory["value"] <= 0:
                    factory["owner_chat_id"] = 0
                    factory["value"] = 0
        for section in blocks_for_market:
            print(time.time() - start_time,
                  "GSR market section awarding", section)
            market_data = dbr.get_market_data(section)
            market_data["blocks"] += blocks_for_market[section]
            dbw.market_update(section, market_data)
        if best.get_market_impulse() < .6:
            for award in money_awards:
                print(time.time() - start_time,
                      "GSR player factory awarding", str(
                      award["station"]) + str(award["fid"]))
                SR_factory_cache_awards(
                    award["station"],
                    award["fid"],
                    award["qty"]
                )
            SR_factory_give_cached_awards(start_time)
        game_data["available_coal"] = coal
        dbw.mini_up_general(game_data)
    current_station = game_data["current_station"]
    return current_station, state


# To be called after SR_position
def SR_journey():
    game_data = dbr.mini_get_general("Global Steel Road")
    enlapsed_time = gut.time_s() - game_data["last_stop_timestamp"]
    coal = game_data["available_coal"]
    if enlapsed_time < 5 * 60:
        return 0
    enlapsed_time -= 5 * 60
    return min(100, ((enlapsed_time + coal * 3 * 60) * 100) // (15 * 60))


def SR_available_items(station):
    if station["type"] == "capital":
        return station["production"] + [station["raw material"]]
    return station["production"] + [station["raw material"]] + [
        station["final product"]]


def SR_next_stop_to_use(user_item):
    current_station, state = SR_position()
    extra = 1
    if state == "stop":
        extra == 0
    count = 0
    if user_item in sr_data["prize"]:
        while count < len(sr_data["itinerary"]):
            if sr_data["itinerary"][(current_station + count + extra) % len(
                    sr_data["itinerary"])]["type"] == "capital":
                return count
            count += 1
    uses = []
    for item in sr_data["requirement"]:
        if sr_data["requirement"][item] == user_item:
            uses.append(item)
    while count < len(sr_data["itinerary"]):
        pos = (current_station + count + extra) % len(sr_data["itinerary"])
        for available_item in SR_available_items(sr_data["itinerary"][pos]):
            if available_item in uses:
                return count
        count += 1
    return len(sr_data["itinerary"])


def SR_current_faction():
    current_station, _ = SR_position()
    while sr_data["itinerary"][current_station % len(sr_data["itinerary"])][
            "type"] != "capital":
        current_station += 1
    return sr_data["itinerary"][current_station % len(sr_data["itinerary"])][
        "central bank"]


def ui_SR_inventory(chat_id):
    player_data = best.mini_get_player(chat_id, "Global Steel Road")
    inv_string = player_data["Slots"]
    item_materials = []
    item_final_prods = []
    for i in range(len(inv_string) // 2):
        item_code = inv_string[i * 2] + inv_string[i * 2 + 1]
        if item_code == "--":
            continue
        next_stop = SR_next_stop_to_use(item_code)
        if next_stop == 0:
            next_stop_str = uistr.get(chat_id, "SR inventory next stop")
        else:
            next_stop_str = str(next_stop)
        if item_code in sr_data["prize"]:
            item_final_prods.append((
                uistr.sr_product(chat_id, item_code), next_stop_str))
        else:
            item_materials.append((
                uistr.sr_product(chat_id, item_code), next_stop_str))

    message = ""
    for i in range(len(item_materials)):
        message += "<" + item_materials[i][0] + "> "
        message += "(" + item_materials[i][1] + ")\n"
    slots_number = min(dbr.login(chat_id)["gear_level"] // 3 + 3, 12)
    for _ in range(slots_number - len(item_materials) - len(item_final_prods)):
        message += "< >\n"
    if len(item_final_prods) > 0:
        message += uistr.get(chat_id, "SR inventory final prods")
    for i in range(len(item_final_prods)):
        message += "<" + item_final_prods[i][0] + "> "
        message += "(" + item_final_prods[i][1] + ")\n"
    message + "\n"
    return message


def SR_material_price(chat_id, material):
    return max(
        sr_data["price"][material],
        sr_data["price"][material] *
        best.get_production(chat_id) // 3600 *
        max(1, int(economy_inflation(chat_id)))
    )


def ui_SR_station_keyboard(chat_id, station):
    player_cur = best.get_types_of(chat_id)["currency"]
    inv_string = best.mini_get_player(chat_id, "Global Steel Road")["Slots"]
    player_items = []
    for i in range(len(inv_string) // 2):
        player_items.append(inv_string[i * 2] + inv_string[i * 2 + 1])
    slots_number = min(dbr.login(chat_id)["gear_level"] // 3 + 3, 12)
    keyboard = []

    raw_material_price = SR_material_price(chat_id, station["raw material"])
    if slots_number > len(player_items) and dbr.check_payment(
            chat_id, best.apply_discount(raw_material_price, player_cur)):
        keyboard.append({
            uistr.get(chat_id, "SR button buy").format(
                itemname=uistr.sr_product(chat_id, station["raw material"])
            ): "SR " + station["raw material"]
        })
    for item_code in station["production"]:
        if sr_data["requirement"][item_code] in player_items:
            keyboard.append({
                uistr.get(chat_id, "SR button exchange").format(
                    requireditemname=uistr.sr_product(
                        chat_id,
                        sr_data["requirement"][item_code]),
                    itemname=uistr.sr_product(chat_id, item_code)
                ): "SR " + item_code
            })
    if station["type"] == "city":
        item_code = station["final product"]
        if sr_data["requirement"][item_code] in player_items:
            keyboard.append({
                uistr.get(chat_id, "SR button exchange").format(
                    requireditemname=uistr.sr_product(
                        chat_id,
                        sr_data["requirement"][item_code]),
                    itemname=uistr.sr_product(chat_id, item_code)
                ): "SR " + item_code
            })
    else:
        for item in player_items:
            if item in sr_data["prize"]:
                keyboard.append({
                    uistr.get(chat_id, "SR button sell").format(
                        itemname=uistr.sr_product(chat_id, item),
                    ): "SR sell " + item
                })
    return keyboard


def SR_item_prize(chat_id, item):
    return max(
        sr_data["prize"][item]["money"],
        sr_data["prize"][item]["money"] *
        best.get_production(chat_id) // 3600 *
        max(1, int(economy_inflation(chat_id)))
    )


def ui_SR_available_selling_options_prizes(chat_id, station_faction):
    player_cur = best.get_types_of(chat_id)["currency"]
    inv_string = best.mini_get_player(chat_id, "Global Steel Road")["Slots"]
    player_items = []
    for i in range(len(inv_string) // 2):
        player_items.append(inv_string[i * 2] + inv_string[i * 2 + 1])

    message = ""
    for item in player_items:
        if item in sr_data["prize"]:
            message += uistr.get(chat_id, "SR sell info").format(
                itemname=uistr.sr_product(chat_id, item),
                money=put.pretty(SR_item_prize(chat_id, item)),
                cur_sym=conv.name(currency=player_cur)["symbol"],
                blocks=best.apply_block_bonus(
                    sr_data["prize"][item]["blocks"] * max(1, int(economy_inflation(chat_id))),
                    chat_id=chat_id
                ),
                blocktype=conv.name(membership=station_faction)["block"]
            )
    return message


def SR_player_mode(chat_id):
    if "last_viewed_menu" not in best.mini_get_player(
            chat_id, "Global Steel Road"):
        return "Market"
    return best.mini_get_player(
        chat_id, "Global Steel Road")["last_viewed_menu"]


def SR_factories_current():
    cid, state = SR_position()
    game_data = dbr.mini_get_general("Global Steel Road")
    if state == "going":
        cid = (cid + 1) % len(sr_data["itinerary"])
    fact_data = {
        fid: game_data["Factories"][str(cid) + str(fid)]
        for fid in "SABCDEF"
    }
    return fact_data


def ui_SR_factories_state(chat_id, station=None, short=False):
    if station:
        game_data = dbr.mini_get_general("Global Steel Road")
        fact_data = {
            fid: game_data["Factories"][str(station) + str(fid)]
            for fid in "SABCDEF"
        }
    else:
        station, state = SR_position()
        if state == "going":
            station = (station + 1) % len(sr_data["itinerary"])
        fact_data = SR_factories_current()
    message = ""
    if fact_data["S"]["owner_chat_id"] > 0:
        if short:
            message += uistr.nickname(
                chat_id,
                fact_data["S"]["owner_chat_id"],
                dbr.get_nickname(fact_data["S"]["owner_chat_id"]))
        else:
            message += uistr.get(chat_id, "SR Factories landowner").format(
                landowner=uistr.nickname(
                    chat_id,
                    fact_data["S"]["owner_chat_id"],
                    dbr.get_nickname(fact_data["S"]["owner_chat_id"]))
            )
    message += "\n`"
    for fid in fact_data:
        badgemoji = "   "
        if fact_data[fid]["owner_chat_id"] > 0:
            badgemoji = best.get_types_of(
                fact_data[fid]["owner_chat_id"])["badgemoji"] + " "
        if fact_data[fid]["owner_chat_id"] == chat_id:
            badgemoji = "⭐️"
        message += (
            fid + ": " + put.pretty(fact_data[fid]["value"]) + " " + badgemoji
        )
        if fid in "SCF":
            if short:
                message += " "
            else:
                message += "\n"
        else:
            if short:
                message += " "
            else:
                message += "\t\t|"
    message += "`"
    if not short:
        message += uistr.get(chat_id, "SR Factories dividend").format(
            base_div=put.pretty(SR_factories_dividend(station)),
            cur_sym=best.get_types_of(chat_id)["symbol"]
        )
    return message


def SR_factories_investment_multipliers(chat_id):
    fact_data = SR_factories_current()
    base_mult = 1
    advanced_mult = 1
    for fid in fact_data:
        if fact_data[fid]["owner_chat_id"] == chat_id:
            base_mult = fact_data[fid]["value"] // 10 + 1
            advanced_mult = fact_data[fid]["value"] // 100
            break
    base_mult = min(base_mult, 10) + max(0, int(economy_inflation(chat_id)))
    advanced_mult = max(advanced_mult, 1)
    return base_mult, advanced_mult


def SR_prices_prizes(chat_id, fid, deal=False):
    game_data = dbr.mini_get_general("Global Steel Road")
    next_cb_position = game_data["current_station"]
    while "central bank" not in sr_data["itinerary"][next_cb_position]:
        next_cb_position = (next_cb_position + 1) % len(sr_data["itinerary"])
    block_type = conv.name(membership=sr_data["itinerary"][
        next_cb_position]["central bank"])["block"]

    value = SR_factories_current()[fid]["value"]
    player_prod = best.get_production(chat_id)
    base_pim, advanced_pim = SR_factories_investment_multipliers(chat_id)
    pim = base_pim * advanced_pim
    prpr = {
        "price_building": int(max(50, value * max(10, value * 9))),
        "value_rise": max(10, value * 9),
        "city_block_type": block_type,
        "price_investing": best.apply_discount(
            max(10, value * player_prod * pim *
                5 // 60 * tv.GSRF_frenzy_invest_price_multiplier()),
            chat_id=chat_id,
            deal=deal
        ),
        "prize_self_blocks": best.apply_block_bonus(
            int(value * pim),
            chat_id=chat_id,
            deal=deal
        ),
        "prize_city_block": best.apply_block_bonus(
            int((value * pim) // 10 + 1),
            chat_id=chat_id,
            deal=deal
        ),
        "investments_use": advanced_pim
    }
    if fid == "S":
        prpr["price_building"] = int(max(200, value * max(20, value * 19)))
        prpr["value_rise"] = max(20, value * 19)
        prpr["prize_city_block"] = best.apply_block_bonus(
            int((value * pim) * 3 // 10 + 1),
            chat_id=chat_id,
            deal=deal
        )
    return prpr


def SR_factory_award_money(cid, fid, qty):
    game_data = dbr.mini_get_general("Global Steel Road")
    owner_chat_id = game_data["Factories"][
        str(cid) + fid]["owner_chat_id"]

    '''
    market_section = best.get_types_of(owner_chat_id)["block"]

    market_data = dbr.get_market_data(market_section)
    _, money_limits = best.get_all_market_limits()
    highest = gut.sort(money_limits)[0][1]

    player_part = min(
        1.0,
        (market_data["money"] + market_data["money_limit"]) / (highest * 2)
    )
    dbw.give_money(owner_chat_id, int(qty * player_part))
    market_part = qty - int(qty * player_part)
    market_data["money"] += int(market_part // 2)
    market_data["money_limit"] += int(market_part - market_part // 2)
    dbw.market_update(market_section, market_data)
    '''
    dbw.give_money(owner_chat_id, int(qty))


sr_cached_awards = {
    "market_money": {},
    "market_money_limit": {},
    "players": {}
}


def SR_factory_cache_awards(cid, fid, qty):
    game_data = dbr.mini_get_general("Global Steel Road")
    owner_chat_id = game_data["Factories"][
        str(cid) + fid]["owner_chat_id"]
    if owner_chat_id == 0:
        return
    '''
    market_section = best.get_types_of(owner_chat_id)["block"]
    market_data = dbr.get_market_data(market_section)

    if owner_chat_id not in sr_cached_awards["players"]:
        sr_cached_awards["players"][owner_chat_id] = 0
    if market_section not in sr_cached_awards["market_money"]:
        sr_cached_awards["market_money"][market_section] = 0
        sr_cached_awards["market_money_limit"][market_section] = 0

    _, money_limits = best.get_all_market_limits()
    highest = gut.sort(money_limits)[0][1]
    player_part = min(
        1.0,
        (
            market_data["money"] +
            sr_cached_awards["market_money"][market_section] +
            market_data["money_limit"] +
            sr_cached_awards["market_money_limit"][market_section]
        ) / (highest * 2)
    )
    sr_cached_awards["players"][owner_chat_id] += int(qty * player_part)
    market_part = qty - int(qty * player_part)
    sr_cached_awards["market_money"][
        market_section] += int(market_part // 2)
    sr_cached_awards["market_money_limit"][
        market_section] += int(market_part - market_part // 2)
    '''
    if owner_chat_id not in sr_cached_awards["players"]:
        sr_cached_awards["players"][owner_chat_id] = 0
    sr_cached_awards["players"][owner_chat_id] += int(qty)


def SR_factory_give_cached_awards(start_time):
    '''
    for section in sr_cached_awards["market_money"]:
        print(time.time() - start_time,
              "GSR cached market", section)
        market_data = dbr.get_market_data(section)
        market_data["money"] += sr_cached_awards[
            "market_money"][section]
        market_data["money_limit"] += sr_cached_awards[
            "market_money_limit"][section]
        dbw.market_update(section, market_data)
    '''
    for chat_id in sr_cached_awards["players"]:
        print(time.time() - start_time,
              "GSR cached player", chat_id)
        dbw.give_money(chat_id, sr_cached_awards["players"][chat_id])


def ui_SR_factories_keyboard(chat_id):
    fact_data = SR_factories_current()
    keyboard = []
    extra = 1
    minimum_value = min([10**29] + [fact_data[fid]["value"]
                                    for fid in fact_data
                                    if fact_data[fid]["value"] > 0])

    mode = "new"
    for fid in "SABCDEF":
        if chat_id == fact_data[fid]["owner_chat_id"]:
            mode = "switch"
            switch_fid = fid
            break

    for fid in fact_data:
        if fid != "S":
            if fact_data[fid]["value"] <= 0:
                if extra <= 0:
                    continue
                extra -= 1
        prpr = SR_prices_prizes(chat_id, fid)
        if fact_data[fid]["value"] <= 0:
            invest_button_text = "-"
        else:
            invest_button_text = ""
            if fact_data[fid]["value"] > minimum_value ** 2:
                invest_button_text += "🚫 "
            invest_button_text += uistr.get(
                chat_id, "SR Factories button invest").format(
                # factory_letter=fid,
                price=put.pretty(prpr["price_investing"]),
                prize=put.pretty(prpr["prize_self_blocks"])
            )
        if mode == "new":
            build_button_text = uistr.get(
                chat_id, "SR Factories button own").format(
                factory_letter=fid,
                cost=put.pretty(prpr["price_building"]),
                block_type=prpr["city_block_type"]
            )
        else:
            if switch_fid == fid:
                build_button_text = uistr.get(
                    chat_id, "SR Factories button up").format(
                    factory_letter=fid,
                    cost=put.pretty(prpr["price_building"]),
                    block_type=prpr["city_block_type"]
                )
            elif fact_data[fid]["owner_chat_id"] > 0:
                build_button_text = uistr.get(
                    chat_id, "SR Factories button switch").format(
                    factory_letter=fid,
                    cost=put.pretty(prpr["price_building"]),
                    block_type=prpr["city_block_type"]
                )
            else:
                build_button_text = "-"
        if build_button_text != "-" or invest_button_text != "-":
            keyboard.append({
                build_button_text: "SR build " + fid,
                invest_button_text: "SR invest " + fid
            })
    return keyboard, prpr["city_block_type"]


def ui_SR_main_screen(chat_id):
    player_coal = best.inventory_get(chat_id, "coal")

    if SR_player_mode(chat_id) == "Market":
        message = uistr.get(chat_id, "SR welcome")
        message += uistr.get(chat_id, "SR inventory").format(
            items=ui_SR_inventory(chat_id))
    else:
        message = uistr.get(chat_id, "SR Factories welcome")
        message += uistr.get(chat_id, "SR Factories state").format(
            state=ui_SR_factories_state(chat_id)
        )

    station, state = SR_position()
    ui_train_len = (SR_journey() * 14) // 100
    journey_string = ""
    for i in range(15):
        if i % 3 == 0:
            journey_string += "|"
        if i < ui_train_len:
            journey_string += "="
        elif i == ui_train_len:
            journey_string += ">"
        else:
            journey_string += "-"

    message += "`" + journey_string + "|`\n"

    keyboard = []
    if state == "going":
        next_station_name = sr_data["itinerary"][
            (station + 1) % len(sr_data["itinerary"])]["name"]
        message += uistr.get(chat_id, "SR travelling").format(
            next_station=next_station_name
        )
        if player_coal > 0:
            keyboard.append({
                uistr.get(chat_id, "SR button coal").format(
                    coal=player_coal
                ): "SR coal"
            })
    else:
        if SR_player_mode(chat_id) == "Market":
            station_name = sr_data["itinerary"][station]["name"]
            station_type = sr_data["itinerary"][station]["type"]
            raw_material_name = uistr.sr_product(
                chat_id,
                sr_data["itinerary"][station]["raw material"])
            production_1_name = uistr.sr_product(
                chat_id,
                sr_data["itinerary"][station]["production"][0])
            production_2_name = uistr.sr_product(
                chat_id,
                sr_data["itinerary"][station]["production"][1])
            if station_type == "city":
                final_prod_name = uistr.sr_product(
                    chat_id,
                    sr_data["itinerary"][station]["final product"])
                message += uistr.get(chat_id, "SR city info").format(
                    statname=station_name,
                    rawmatname=raw_material_name,
                    prod1name=production_1_name,
                    prod2name=production_2_name,
                    finprodname=final_prod_name
                )
            else:
                message += uistr.get(chat_id, "SR capital info").format(
                    statname=station_name,
                    cenbank=sr_data["itinerary"][station]["central bank"],
                    rawmatname=raw_material_name,
                    prod1name=production_1_name,
                    prod2name=production_2_name
                )
                message += ui_SR_available_selling_options_prizes(
                    chat_id,
                    sr_data["itinerary"][station]["central bank"])
            keyboard += ui_SR_station_keyboard(
                chat_id,
                sr_data["itinerary"][station])
        else:
            station_name = sr_data["itinerary"][station]["name"]
            message += uistr.get(chat_id, "SR Factories city info").format(
                statname=station_name
            )
            player_data = best.mini_get_player(chat_id, "Global Steel Road")
            game_data = dbr.mini_get_general("Global Steel Road")
            if player_data["last_investment_timestamp"] < game_data[
                    "last_stop_timestamp"]:
                player_data["investments_in_last_station"] = 0
            message += uistr.get(chat_id, "SR available investments").format(
                num=tv.GSRF_frenzy_invest_count(chat_id) - player_data[
                    "investments_in_last_station"]
            )
            passes = best.inventory_get(chat_id, "investment_pass")
            if passes > 0:
                message += uistr.get(chat_id, "SR investment passes").format(
                    passes=passes
                )
            gsrf_keyboard, city_block_type = ui_SR_factories_keyboard(chat_id)
            keyboard += gsrf_keyboard
            cur_sym = conv.name(membership=dbr.login(
                chat_id)["membership"])["symbol"]
            own_faction_blocks = conv.name(membership=dbr.login(
                chat_id)["membership"])["block"]
            message += "\n\n" + uistr.get(chat_id, "MM main balance").format(
                value=put.pretty(dbr.login(chat_id)["balance"]), sym=cur_sym)
            own_cur = conv.name(block=own_faction_blocks)["currency"]
            city_cur = conv.name(block=city_block_type)["currency"]
            message += (
                uistr.get(chat_id, "MM blocks") +
                put.pretty(dbr.login(chat_id)["blocks"][own_cur]) +
                " " + own_faction_blocks
            )
            if own_faction_blocks != city_block_type:
                message += (
                    ", " +
                    put.pretty(dbr.login(chat_id)["blocks"][city_cur]) +
                    " " + city_block_type
                )

    if SR_player_mode(chat_id) == "Market":
        keyboard.append({
            uistr.get(chat_id, "SR button to Factories"): "SR mode switch"
        })
        keyboard.append({
            uistr.get(chat_id, "minis button manual"): "SR manual 3",
            uistr.get(chat_id, "button back"): "Main menu"})
    else:
        keyboard.append({
            uistr.get(chat_id, "SR button to Market"): "SR mode switch"
        })
        keyboard.append({
            uistr.get(chat_id, "minis button manual"): "SR manual 3",
            uistr.get(chat_id, "button back"): "Main menu"})
    return message, keyboard


def ui_SR_manual(chat_id, page):
    page = max(0, page)
    if page == 0:  # Prizes
        player_cursym = best.get_types_of(chat_id)["symbol"]
        message = "📈" + "⁞:" * 17 + "⁞\n"
        message += uistr.get(chat_id, "SR section Prizes") + "\n\n"
        for fin_prod in sr_data["prize"]:
            message += uistr.sr_product(chat_id, fin_prod) + ": "
            money_prize = SR_item_prize(chat_id, fin_prod)
            message += put.pretty(money_prize) + player_cursym + ", "
            message += put.pretty(
                sr_data["prize"][fin_prod]["blocks"]) + " " + uistr.get(
                chat_id, "blocks") + "\n"

    elif page == 1:  # Prices
        player_cur = best.get_types_of(chat_id)["currency"]
        player_cursym = best.get_types_of(chat_id)["symbol"]
        message = "📈" + "⁞:" * 17 + "⁞\n"
        message += uistr.get(chat_id, "SR section Prices") + "\n\n"
        for material in sr_data["price"]:
            message += uistr.sr_product(chat_id, material) + ": "
            money_price = best.apply_discount(
                SR_material_price(chat_id, material),
                player_cur
            )
            message += put.pretty(money_price) + player_cursym + "\n"

    elif page == 2:  # Exchanges
        message = "📈" + "⁞:" * 17 + "⁞\n"
        message += uistr.get(chat_id, "SR section Exchanges") + "\n"
        for cat in "ABCDEFGHIJKLMNOPQRTUVWXYZ":
            for prod in "BCDEFGHIJKLMNOPQRTUVWXYZ":
                if cat + prod in sr_data["requirement"]:
                    message += uistr.sr_product(chat_id, cat + prod) + " <- "
                    message += uistr.sr_product(chat_id, sr_data[
                        "requirement"][cat + prod]) + "\n"
            message += "\n"

    else:  # Itinerary
        message = "🚄" + "=Ι" * 17 + "=\n"
        iti_page = page - 3
        position, _ = SR_position()
        for i in range(7):
            iti_station = (
                position + i + iti_page * 7) % len(sr_data["itinerary"])
            stdata = sr_data["itinerary"][iti_station]
            if stdata["type"] == "capital":
                message += "⭐️" + conv.name(membership=stdata["central bank"])[
                    "badgemoji"] + " "
            if iti_page == 69:
                message += "❤️"
            message += stdata["name"] + ": "
            if SR_player_mode(chat_id) == "Market":
                message += "\n" + uistr.sr_product(
                    chat_id, stdata["raw material"]) + ", "
                message += uistr.sr_product(
                    chat_id, stdata["production"][0]) + ",\n"
                message += uistr.sr_product(chat_id, stdata["production"][1])
                if stdata["type"] == "city":
                    message += ", " + uistr.sr_product(
                        chat_id, stdata["final product"])
            else:
                message += ui_SR_factories_state(
                    chat_id, iti_station, short=True)
            message += "\n\n"

    keyboard = [
        {"<": "SR manual " + str(page - 1),
         ">": "SR manual " + str(page + 1)
         },
        {uistr.get(chat_id, "button back mini"): "SR main"}]
    return message, keyboard


def ui_SR_mode_switch(chat_id):
    player_data = best.mini_get_player(chat_id, "Global Steel Road")
    if SR_player_mode(chat_id) == "Market":
        player_data["last_viewed_menu"] = "Factories"
    else:
        player_data["last_viewed_menu"] = "Market"
    best.mini_up_player(chat_id, "Global Steel Road", player_data)
    return uistr.get(chat_id, "Done")


def ui_SR_player_action(chat_id, product, selling=False, coal=False):
    game_data = dbr.mini_get_general("Global Steel Road")
    if coal:
        if best.inventory_get(chat_id, "coal") == 0:
            return uistr.get(chat_id, "SR no coal")
        best.inventory_use(chat_id, "coal", 1)
        game_data["available_coal"] += 1
        dbw.mini_up_general(game_data)
        return uistr.get(chat_id, "Done")
    station_number, state = SR_position()
    if state == "going":
        return uistr.get(chat_id, "SR error going")

    player_data = best.mini_get_player(chat_id, "Global Steel Road")
    player_items = []
    for i in range(len(player_data["Slots"]) // 2):
        player_items.append(
            player_data["Slots"][i * 2] + player_data["Slots"][i * 2 + 1])

    station = sr_data["itinerary"][station_number]
    if selling:
        if station["type"] != "capital":
            return uistr.get(chat_id, "SR error not capital")
        if product not in player_items:
            return uistr.get(chat_id, "SR error requirement not met")
        player_items.remove(product)
        dbw.give_money(chat_id, SR_item_prize(chat_id, product))
        dbw.add_block(
            chat_id,
            conv.name(membership=station["central bank"])["currency"],
            best.apply_block_bonus(
                sr_data["prize"][product]["blocks"],
                chat_id=chat_id,
                deal=True
            )
        )
        player_data["Slots"] = ""
        for item in player_items:
            player_data["Slots"] += item
        best.mini_up_player(chat_id, "Global Steel Road", player_data)
        game_data["interactions"] += 1
        dbw.mini_up_general(game_data)
        if random.random() <= (.2 *
           best.mystery_item_base_probability(chat_id)):
            best.inventory_give(chat_id, "mystery_item", 1)
            return uistr.get(chat_id, "found mystery item")
        return uistr.get(chat_id, "Done")

    # if exchanging:
    if product in sr_data["requirement"]:  # includes every non-raw material
        available_items = station["production"].copy()
        if station["type"] == "city":
            available_items.append(station["final product"])

        if product not in available_items:
            return uistr.get(chat_id, "SR error item not available")
        if sr_data["requirement"][product] not in player_items:
            return uistr.get(chat_id, "SR error requirement not met")
        player_items.remove(sr_data["requirement"][product])
        player_items.append(product)
        player_data["Slots"] = ""
        for item in player_items:
            player_data["Slots"] += item
        best.mini_up_player(chat_id, "Global Steel Road", player_data)
        game_data["interactions"] += 1
        dbw.mini_up_general(game_data)
        return uistr.get(chat_id, "Done")

    # if buying a raw material
    if product != station["raw material"]:
        return uistr.get(chat_id, "SR error item not available")
    if game_data["sold_materials"] >= len(
            dbr.mini_get_general("Daily News")["Countries"]):
        return uistr.get(chat_id, "SR error materials sold out")
    slots_number = min(dbr.login(chat_id)["gear_level"] // 3 + 3, 12)
    if slots_number <= len(player_items):
        return uistr.get(chat_id, "SR error inventory full")
    raw_material_price = SR_material_price(chat_id, product)
    price_for_player = best.apply_discount(raw_material_price, chat_id=chat_id)
    if not dbr.check_payment(chat_id, price_for_player):
        return uistr.get(chat_id, "Insufficient balance")

    r = dbw.pay_money(chat_id, price_for_player)
    if r != "Ok":
        return uistr.get(chat_id, "Internal error")
    player_items.append(product)
    player_data["Slots"] = ""
    for item in player_items:
        player_data["Slots"] += item
    best.mini_up_player(chat_id, "Global Steel Road", player_data)
    game_data["interactions"] += 1
    game_data["sold_materials"] += 1
    dbw.mini_up_general(game_data)
    return uistr.get(chat_id, "Done")


def SR_factories_can_invest(chat_id, needed):
    game_data = dbr.mini_get_general("Global Steel Road")
    player_data = best.mini_get_player(chat_id, "Global Steel Road")
    is_new_station = player_data["last_investment_timestamp"] < game_data[
        "last_stop_timestamp"]
    natural_investments = tv.GSRF_frenzy_invest_count(chat_id)
    passes = best.inventory_get(chat_id, "investment_pass")
    cur_investment_count = player_data["investments_in_last_station"]

    return (
        is_new_station and (needed <= (natural_investments + passes))
    ) or (
        (cur_investment_count + needed) <= (natural_investments + passes)
    )


def SR_factories_count_new_investments(chat_id, investments):
    player_data = best.mini_get_player(chat_id, "Global Steel Road")
    player_data["last_investment_timestamp"] = gut.time_s()
    natural_investments = tv.GSRF_frenzy_invest_count(chat_id)

    investments_left_to_use = investments
    if player_data[
            "investments_in_last_station"] < natural_investments:
        new_state = min(
            player_data["investments_in_last_station"] + investments,
            natural_investments
        )
        investments_left_to_use -= new_state - player_data[
            "investments_in_last_station"]
        player_data["investments_in_last_station"] = new_state

    if investments_left_to_use > 0:
        best.inventory_use(chat_id, "investment_pass", investments_left_to_use)
    player_data["last_investment_timestamp"] = gut.time_s()
    best.mini_up_player(chat_id, "Global Steel Road", player_data)


def ui_SR_factories_action(chat_id, sel_fid, action):
    cid, state = SR_position()
    if state == "going":
        return uistr.get(chat_id, "SR error going"), None
    user_data = dbr.login(chat_id)
    game_data = dbr.mini_get_general("Global Steel Road")
    player_data = best.mini_get_player(chat_id, "Global Steel Road")

    current_faction = conv.name(membership=SR_current_faction())

    if action == "build":
        prpr = SR_prices_prizes(chat_id, sel_fid)
        mode = "new"
        for fid in "SABCDEF":
            if chat_id == game_data["Factories"][str(cid) + fid][
                    "owner_chat_id"]:
                mode = "switch"
                switch_fid = fid
                break
                # return uistr.get(chat_id, "SR error already landowner"), None
        if prpr["price_building"] > user_data[
           "blocks"][current_faction["currency"]]:
            return uistr.get(chat_id, "SR error build blocks"), None
        old_owner = game_data["Factories"][str(cid) + sel_fid]["owner_chat_id"]
        if mode == "switch" and old_owner == 0:
            return uistr.get(chat_id, "SR error already landowner"), None
        # General action in all cases
        game_data["Factories"][
            str(cid) + sel_fid]["owner_chat_id"] = chat_id
        game_data["Factories"][str(cid) + sel_fid]["value"] += prpr["value_rise"]
        dbw.pay_block(
            chat_id, current_faction["currency"], prpr["price_building"])
        dbw.mini_up_general(game_data)
        SR_factories_dividend(cid, redo=True)
        if old_owner != chat_id:
            if mode == "new" and old_owner > 0:
                notifications = [{
                    "chat_id": old_owner,
                    "message": uistr.get(
                        old_owner,
                        "SR Factories notify lost factory").format(
                            city=sr_data["itinerary"][cid]["name"]
                    )
                }]
                return uistr.get(chat_id, "Done"), notifications
            elif mode == "switch":  # old_owner isn't 0
                game_data["Factories"][
                    str(cid) + switch_fid]["owner_chat_id"] = old_owner
                dbw.mini_up_general(game_data)
                notifications = [{
                    "chat_id": old_owner,
                    "message": uistr.get(
                        old_owner,
                        "SR Factories notify switched factory").format(
                            city=sr_data["itinerary"][cid]["name"]
                    )
                }]
                return uistr.get(chat_id, "Done"), notifications
        return uistr.get(chat_id, "Done"), None
    if action == "invest":  # todo: redesign the game mechanics here, to reduce db writes
        prpr = SR_prices_prizes(chat_id, sel_fid)
        passes = best.inventory_get(chat_id, "investment_pass")
        if not SR_factories_can_invest(chat_id, prpr["investments_use"]):
            return uistr.get(chat_id, "SR error already invested"), None
        if player_data["last_investment_timestamp"] < game_data[
                "last_stop_timestamp"]:
            player_data["investments_in_last_station"] = 0
        minimum_value = min([10**29] + [
            game_data["Factories"][str(cid) + fid]["value"]
            for fid in "SABCDEF"
            if game_data["Factories"][str(cid) + fid]["value"] > 0])
        if game_data["Factories"][str(cid) + sel_fid]["value"] <= 0:
            return uistr.get(chat_id, "SR error no owner"), None
        if game_data["Factories"][
                str(cid) + sel_fid]["value"] > minimum_value ** 2:
            return uistr.get(chat_id, "SR error value too high"), None
        if not dbr.check_payment(chat_id, prpr["price_investing"]):
            return uistr.get(chat_id, "Insufficient balance"), None

        prpr = SR_prices_prizes(chat_id, sel_fid, deal=True)
        base_pim, advanced_pim = SR_factories_investment_multipliers(chat_id)
        pim = base_pim * advanced_pim
        if sel_fid == "S":
            game_data["Factories"][str(cid) + sel_fid]["value"] += 5 * pim
        else:
            game_data["Factories"][str(cid) + sel_fid]["value"] += 1 * pim
        SR_factories_count_new_investments(chat_id, prpr["investments_use"])

        if game_data["Factories"][str(cid) + sel_fid]["owner_chat_id"] == chat_id and best.get_market_impulse() < 0.5:
            dbw.pay_money(chat_id, prpr["price_investing"] * 9 // 10)
        elif best.get_market_impulse() < 0.5:
            dbw.pay_money(chat_id, prpr["price_investing"])
            SR_factory_award_money(cid, sel_fid, prpr["price_investing"] // 10)
        else:
            dbw.pay_money(chat_id, prpr["price_investing"])
        # block bonus already applied in prpr
        dbw.add_block(
            chat_id,
            best.get_types_of(chat_id)["currency"],
            prpr["prize_self_blocks"])
        dbw.add_block(
            chat_id, current_faction["currency"], prpr["prize_city_block"])

        dbw.mini_up_general(game_data)  # This takes 100-1000ms, it slows everyone down if spammed
        best.mini_up_player(chat_id, "Global Steel Road", player_data)
        return uistr.get(chat_id, "Done"), None
    return "Eh?", None


# == SHOP CHAIN ==
'''
Global data
    Employers: M    [key: faction]
        <employerIDs>: NS     (number set)
    Record Number of Shops: N (the current best employerID)

User data
    Game Timestamp: N     (used to update history)
    Employees: N
    Shops <faction>: N
    Payment Amount: N     (this is saved as pro capite)
    History of Payments: L  (FIFO queue)

'''

sc_period = 60 * 60 * 8  # 4 hours


def SC_game_and_player_data(chat_id):
    game_data = dbr.mini_get_general("Shop Chain")
    player_data = best.mini_get_player(chat_id, "Shop Chain")
    if len(game_data) == 0:
        game_data = {
            "key": "Shop Chain",
            "general_highscore": chat_id,
            "faction_employers": {f: {0} for f in gut.list["membership"]}
        }
        dbw.mini_up_general(game_data)
    # Reading from database forgets the type, reconvert lists to sets pls
    game_data["faction_employers"] = {
        f: set(game_data["faction_employers"][f])
        for f in gut.list["membership"]
    }

    if sum(player_data["history"]) > 0:
        period_diff = gut.time_s() // sc_period - player_data["game_timestamp"] // sc_period
        if period_diff > 0:
            for _ in range(min(6, period_diff)):
                player_data["history"] = player_data["history"][1:6] + [0]
            player_data["game_timestamp"] = gut.time_s()
            best.mini_up_player(chat_id, "Shop Chain", player_data)

    p_faction = dbr.login(chat_id)["membership"]
    update = False
    if sum(player_data["history"]) > 0:
        if chat_id not in game_data["faction_employers"][p_faction]:
            game_data["faction_employers"][p_faction].add(chat_id)
            update = True
    elif chat_id in game_data["faction_employers"][p_faction]:
        game_data["faction_employers"][p_faction].remove(chat_id)
        update = True

    for f in game_data["faction_employers"]:
        if f != p_faction and chat_id in game_data["faction_employers"][f]:
            game_data["faction_employers"][f].remove(chat_id)
            update = True

    if update:
        dbw.mini_up_general(game_data)
    return game_data, player_data


def economy_inflation(chat_id):
    _, player_data = SC_game_and_player_data(chat_id)
    paid_wages = sum(x > 0 for x in player_data["history"])
    if paid_wages < 4:
        return 0
    return (
        math.log10(max(1, sum(player_data["history"]))) +
        (
            math.log2(max(1, sum(player_data["history"][-3:]))) -
            math.log2(max(1, sum(player_data["history"][:3])))
        ) * 10
    )


# Returns all daily wages, updates list for 0 incomes. and individual data
def SC_faction_upget(chat_id, faction):
    game_data, _ = SC_game_and_player_data(chat_id)
    employers_to_delete = []
    employers_wages = {}
    for employer_id in game_data["faction_employers"][faction]:
        if employer_id == 0:
            continue
        employer_data = best.mini_get_player(employer_id, "Shop Chain")
        if sum(employer_data["history"]) > 0:
            period_diff = gut.time_s() // sc_period - employer_data["game_timestamp"] // sc_period
            if period_diff > 0:
                for _ in range(min(6, period_diff)):
                    employer_data["history"] = employer_data["history"][1:6] + [0]
                employer_data["game_timestamp"] = gut.time_s()
                best.mini_up_player(employer_id, "Shop Chain", employer_data)
        if sum(employer_data["history"]) == 0:
            employers_to_delete.append(employer_id)
        else:
            employers_wages[employer_id] = sum(employer_data["history"])

    if len(employers_to_delete) > 0:
        for employer_id in employers_to_delete:
            game_data["faction_employers"][faction].remove(employer_id)
        dbw.mini_up_general(game_data)

    return employers_wages


def SC_player_total_shops(chat_id):
    _, player_data = SC_game_and_player_data(chat_id)
    count = 0
    for faction in gut.list["membership"]:
        count += player_data["shops_" + faction]
    return count


def SC_hire(chat_id, qty):
    _, player_data = SC_game_and_player_data(chat_id)
    player_data["employees"] = max(
        10,
        player_data["employees"] + qty
    )
    best.mini_up_player(chat_id, "Shop Chain", player_data)
    return True


# This does not account for block payment
def SC_open_new_shop(chat_id):
    game_data, player_data = SC_game_and_player_data(chat_id)
    p_faction = dbr.login(chat_id)["membership"]
    tot_shops = SC_player_total_shops(chat_id)

    # if player_data["employees"] < 3 * (tot_shops + 1):
    #    return False
    player_data["shops_" + p_faction] += 1
    best.mini_up_player(chat_id, "Shop Chain", player_data)
    return True


def SC_shop_cost(chat_id):
    tot_shops = SC_player_total_shops(chat_id)
    return tot_shops * 100


def SC_maximize(chat_id):
    tot_shops = SC_player_total_shops(chat_id)
    _, player_data = SC_game_and_player_data(chat_id)
    p_faction = dbr.login(chat_id)["membership"]
    user_data = dbr.login(chat_id)
    user_blocks = user_data["blocks"][conv.name(membership=p_faction)["currency"]]
    max_shops = math.isqrt(max(0, tot_shops**2 + user_blocks // 50))
    if max_shops <= tot_shops:
        return False, 0, 0  # , 0
    # max_workers = max_shops * 10
    paid_blocks = (max_shops * (max_shops + 1) - tot_shops * (tot_shops + 1)) * 50
    opened_shops = max_shops - tot_shops
    # hired = max_workers - player_data["employees"]

    player_data["shops_" + p_faction] += opened_shops
    # player_data["employees"] = max_workers
    best.mini_up_player(chat_id, "Shop Chain", player_data)
    dbw.pay_block(
        chat_id,
        conv.name(membership=p_faction)["currency"],
        paid_blocks
    )
    return True, paid_blocks, opened_shops  # , hired


def ui_SC_wage_change(chat_id, per_cent):
    _, player_data = SC_game_and_player_data(chat_id)
    old_wage = player_data["payment_amount"]
    player_data["payment_amount"] *= 1 + per_cent / 100
    player_data["payment_amount"] = int(max(1000, player_data["payment_amount"]))
    if player_data["payment_amount"] == old_wage:
        return uistr.get(chat_id, "SC wage not changed")
    best.mini_up_player(chat_id, "Shop Chain", player_data)
    return uistr.get(chat_id, "Done")


def ui_SC_wage_pay(chat_id):
    game_data, player_data = SC_game_and_player_data(chat_id)
    if player_data["history"][-1] > 0:
        return uistr.get(chat_id, "SC already paid")
    player_prod = best.get_production(chat_id)
    salary = player_data["payment_amount"] * player_prod // 30000
    price = salary * player_data["employees"]
    if not dbr.check_payment(chat_id, price):
        return uistr.get(chat_id, "Insufficient balance")
    dbw.pay_money(chat_id, price)

    player_data["history"][-1] = salary
    faction_wages = SC_faction_upget(chat_id, dbr.login(chat_id)["membership"])
    if len(faction_wages) < 3:
        multiplier = 1
    else:
        max_wage = max(faction_wages.values())
        if faction_wages[chat_id] == max_wage:
            multiplier = 2
        else:
            multiplier = (faction_wages[chat_id] / max_wage)**2
    bpf = {}
    tot_score = 0
    for faction in gut.list["membership"]:
        bpf[faction] = min(int(
            .5 +
            player_data["employees"] *
            math.log2(player_data["shops_" + faction] + 1) *
            multiplier
        ), 10**35)
        tot_score += bpf[faction]
        dbw.add_block(
            chat_id, conv.name(membership=faction)["currency"],
            bpf[faction]
        )

    if tot_score > player_data["highscore"] or player_data["game_timestamp"] < 1703874597:
        player_data["highscore"] = tot_score
        if game_data["general_highscore"] != chat_id:
            if player_data["highscore"] > SC_game_and_player_data(game_data["general_highscore"])[1]["highscore"]:
                game_data["general_highscore"] = chat_id
                dbw.mini_up_general(game_data)

    # Change number of employees
    paid_wages = sum(x > 0 for x in player_data["history"])
    tot_shops = SC_player_total_shops(chat_id)
    employees = player_data["employees"]
    ten_times_shops = tot_shops * 10
    if paid_wages == 1:
        SC_hire(chat_id, int(employees * (-.10)))
    elif paid_wages == 2:
        SC_hire(chat_id, int(employees * (-.05)))
    elif paid_wages == 3:
        SC_hire(chat_id, int(employees * (-.02)))
    elif paid_wages == 4:
        SC_hire(chat_id, int(min(ten_times_shops, employees) * (.02)))
    elif paid_wages == 5:
        SC_hire(chat_id, max(3, int(.5 + min(ten_times_shops, employees) * (.05))))
    elif paid_wages == 6:
        SC_hire(chat_id, max(3, int(.5 + ten_times_shops * (.05))))

    best.mini_up_player(chat_id, "Shop Chain", player_data)

    return uistr.get(chat_id, "SC block prize").format(
        prize=ui_game_prizes_message(
            chat_id,
            us_dollar_blocks=bpf["FED"], euro_blocks=bpf["ECB"],
            yuan_blocks=bpf["PBC"], au_dollar_blocks=bpf["RBA"],
            real_blocks=bpf["CBB"], rupee_blocks=bpf["RBI"],
            afro_blocks=bpf["ACB"])
    )


def ui_SC_action(chat_id, action, value=0):
    game_data, player_data = SC_game_and_player_data(chat_id)
    if action == "pay":
        return ui_SC_wage_pay(chat_id)
    if action == "wage":
        return ui_SC_wage_change(chat_id, value)
    if action == "hire":
        # if SC_hire(chat_id, value):
        #    return uistr.get(chat_id, "Done")
        return uistr.get(chat_id, "SC not hired")
    if action == "open":
        block_cost = SC_shop_cost(chat_id)
        user_data = dbr.login(chat_id)
        if block_cost > user_data["blocks"][conv.name(membership=user_data["membership"])["currency"]]:
            return uistr.get(chat_id, "SR error build blocks")  # eheh
        if SC_open_new_shop(chat_id):
            dbw.pay_block(
                chat_id,
                conv.name(membership=user_data["membership"])["currency"],
                block_cost
            )
            return uistr.get(chat_id, "Done")
        return uistr.get(chat_id, "SC not opened")
    if action == "maximize":
        # done, paid_blocks, opened_shops, hired = SC_maximize(chat_id)
        done, paid_blocks, opened_shops = SC_maximize(chat_id)
        if not done:
            return uistr.get(chat_id, "SR error build blocks")
        return uistr.get(chat_id, "SC maximized").format(
            blocks=put.pretty(paid_blocks),
            shops=opened_shops  # ,
            # hired=hired
        )
    return "Eh?"


def ui_SC_main_screen(chat_id):
    game_data, player_data = SC_game_and_player_data(chat_id)
    message = uistr.get(chat_id, "SC presentation")

    recent_payments_line = "\["
    for el in player_data["history"][:-1]:
        recent_payments_line += put.pretty(el) + " | "
    recent_payments_line += put.pretty(player_data["history"][-1]) + "]"
    message += uistr.get(chat_id, "SC player data").format(
        shops_FED=conv.name(membership="FED")["badgemoji"] + " " + put.readable(player_data["shops_FED"]),
        shops_ECB=conv.name(membership="ECB")["badgemoji"] + " " + put.readable(player_data["shops_ECB"]),
        shops_PBC=conv.name(membership="PBC")["badgemoji"] + " " + put.readable(player_data["shops_PBC"]),
        shops_RBA=conv.name(membership="RBA")["badgemoji"] + " " + put.readable(player_data["shops_RBA"]),
        shops_CBB=conv.name(membership="CBB")["badgemoji"] + " " + put.readable(player_data["shops_CBB"]),
        shops_RBI=conv.name(membership="RBI")["badgemoji"] + " " + put.readable(player_data["shops_RBI"]),
        shops_ACB=conv.name(membership="ACB")["badgemoji"] + " " + put.readable(player_data["shops_ACB"]),
        tot_shops=put.pretty(SC_player_total_shops(chat_id)),
        employees=put.readable(player_data["employees"]),
        current_wage=put.pretty(sum(player_data["history"])),
        recent_payments=recent_payments_line
    )
    player_prod = best.get_production(chat_id)
    salary = player_data["payment_amount"] * player_prod // 30000
    keyboard = []
    keyboard.append({
        uistr.get(chat_id, "SC button pay").format(
            amount=put.pretty(salary),
            price=put.pretty(player_data["employees"] * salary)
        ): "SC pay"
    })
    keyboard.append({
        "-50%": "SC wage -50",
        "-10%": "SC wage -10",
        "+10%": "SC wage +10",
        "+50%": "SC wage +50"
    })
    '''
    keyboard.append({
        uistr.get(chat_id, "SC button hire"): "SC hire 1",
        "5": "SC hire 5",
        "50": "SC hire 50"
    })
    '''
    keyboard.append({
        uistr.get(chat_id, "SC button open shop").format(
            block_cost=put.pretty(SC_shop_cost(chat_id)) + " " + conv.name(
                membership=dbr.login(chat_id)["membership"])["block"]
        ): "SC open"
    })
    keyboard.append({
        uistr.get(chat_id, "SC button maximize"): "SC maximize"
    })
    keyboard.append({
        uistr.get(chat_id, "SC button data"): "SC data screen",
        uistr.get(chat_id, "button back"): "Main menu"
    })
    return message, keyboard


def ui_SC_data_screen(chat_id):
    # Show data on this player's faction
    player_faction = dbr.login(chat_id)["membership"]
    player_faction_wages = SC_faction_upget(chat_id, player_faction)
    if len(player_faction_wages) == 0:
        player_faction_wages = {chat_id: 0}
    message = uistr.get(chat_id, "SC Data Player Faction") + uistr.get(chat_id, "SC Data Line").format(
        max=put.pretty(max(player_faction_wages.values())),
        avg=put.pretty(sum(player_faction_wages.values()) // len(player_faction_wages)),
        min=put.pretty(min(player_faction_wages.values())),
        syn=conv.name(membership=player_faction)["symbol"]
    ) + "\n\n"

    # Show data on other factions
    all_factions_wages = {}
    all_factions_wages = {**all_factions_wages, **player_faction_wages}
    for faction in gut.list["membership"]:
        if faction == player_faction:
            continue
        faction_wages = SC_faction_upget(chat_id, faction)
        all_factions_wages = {**all_factions_wages, **faction_wages}
        if len(faction_wages) == 0:
            faction_wages = {chat_id: 0}
        message += faction + ": " + uistr.get(chat_id, "SC Data Line").format(
            max=put.pretty(max(faction_wages.values())),
            avg=put.pretty(sum(faction_wages.values()) // len(faction_wages)),
            min=put.pretty(min(faction_wages.values())),
            syn=conv.name(membership=faction)["symbol"]
        ) + "\n"
    message += "\n"

    # Show best player in player faction and in general
    best_player_in_player_faction, b_wage_ipf = gut.sort(player_faction_wages)[0]
    best_player_in_general, b_wage_ig = gut.sort(all_factions_wages)[0]

    if best_player_in_player_faction == best_player_in_general:
        message += uistr.get(chat_id, "SC best unified").format(
            player=uistr.nickname(
                chat_id,
                best_player_in_general,
                dbr.get_nickname(best_player_in_general)
            ),
            wage=put.pretty(b_wage_ig)
        )
    else:
        message += uistr.get(chat_id, "SC best two").format(
            player_pf=uistr.nickname(
                chat_id,
                best_player_in_player_faction,
                dbr.get_nickname(best_player_in_player_faction)
            ),
            wage_pf=put.pretty(b_wage_ipf),
            player_general=uistr.nickname(
                chat_id,
                best_player_in_general,
                dbr.get_nickname(best_player_in_general)
            ),
            wage_general=put.pretty(b_wage_ig)
        )

    keyboard = [{
        uistr.get(chat_id, "SC button main"): "SC main",
        uistr.get(chat_id, "button back"): "Main menu"
    }]
    return message, keyboard


def SC_get_points_record(chat_id):
    game_data, _ = SC_game_and_player_data(chat_id)
    nickname = uistr.nickname(
        chat_id,
        game_data["general_highscore"],
        dbr.get_nickname(game_data["general_highscore"])
    )
    _, hsp_data = SC_game_and_player_data(game_data["general_highscore"])
    highscore = hsp_data["highscore"]
    return {"highscore_player_nick": nickname, "highscore": highscore}


def SC_get_personal_points_record(chat_id):
    _, player_data = SC_game_and_player_data(chat_id)
    return player_data["highscore"]


# =========================


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
