from _common import *

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
    Investment: S

'''

sc_period = 60 * 60 * 8  # 8 hours


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
