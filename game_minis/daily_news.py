from _common import *

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
