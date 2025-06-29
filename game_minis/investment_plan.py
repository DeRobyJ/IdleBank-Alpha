from game_minis._common import *

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
