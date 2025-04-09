import game_dbwrite as dbw
import game_dbread as dbr
import back_end_sub_tasks as best
import game_util as gut
import print_util as put
import uistr
import random
import math


# Differently from other parts of the source, this code relies often on the
# fact that user_data will always be passed through functions as reference.
# Some operations are done in careful order because of this.
def get_user_data(chat_id):
    user_data = dbr.get_minimal_user(chat_id)
    new = False
    if len(user_data) == 0:
        new = True
        user_data = {
            "production_level": 0,
            "saved_balance": 20,
            "balance_timestamp": gut.time_s(),
            "blocks": 50,
            "gear_level": 0,
            "generator_level": 0,
            "board_level": 1,
            "board_timestamp": gut.time_s(),
            "shard_exp": 0
        }
        dbw.up_minimal_user(chat_id, user_data)
    if "shard_exp" not in user_data:
        user_data["shard_exp"] = 0
    return user_data, new


def set_user_data(chat_id, data):
    dbw.up_minimal_user(chat_id, data)


def get_balance(chat_id):
    user_data, _ = get_user_data(chat_id)
    return gut.balance(
        user_data["production_level"],
        user_data["gear_level"],
        "L" * user_data["gear_level"],
        user_data["saved_balance"],
        user_data["balance_timestamp"]
    )


def get_production_rate(chat_id):
    user_data, _ = get_user_data(chat_id)
    return int(
        gut.hourly_production_rate_of_level(user_data["production_level"]) *
        gut.total_multiplier("L" * user_data["gear_level"])
    )


def get_general_data():
    mnm_data = dbr.get_minimal_general_data()
    if len(mnm_data) == 0:
        mnm_data = {
            "Requests": [],
            "Leaderboard": []
        }
        dbw.up_minimal_general_data(mnm_data)
    return mnm_data["Requests"], mnm_data["Leaderboard"]


def get_shard_bins():
    mnm_data = dbr.get_minimal_general_data()
    if len(mnm_data) == 0:
        get_general_data()
    if "shard_bins" not in mnm_data:
        mnm_data["shard_bins"] = {
            type: 0 for type in [
                "red", "green", "blue", "yellow",
                "cyan", "magenta", "silver", "gold"
            ]
        }
        dbw.up_minimal_general_data(mnm_data)
    if "shard_global_exp" not in mnm_data:
        mnm_data["shard_global_exp"] = 0
    return mnm_data["shard_bins"], mnm_data["shard_global_exp"]


def get_shard_levels(chat_id, residuals=False):
    shard_exp = get_user_data(chat_id)[0]["shard_exp"]
    _, shard_global_exp = get_shard_bins()
    if shard_exp < 100:
        user_shard_level = 1
        residual_user = shard_exp / 100
    else:
        user_shard_level = int(math.log2(shard_exp / 25))
        residual_user = (shard_exp - 25 * (2 ** user_shard_level)) / (25 * (2 ** user_shard_level))

    if shard_global_exp < 1000:
        global_shard_level = 1
        residual_global = shard_global_exp / 1000
    else:
        global_shard_level = int(math.log2(shard_global_exp / 250))
        residual_global = (shard_global_exp - 250 * (2 ** global_shard_level)) / (250 * (2 ** global_shard_level))

    if residuals:
        return user_shard_level, global_shard_level, residual_user, residual_global
    return user_shard_level, global_shard_level


def shard_bin_sizes(gslvl):
    return {
        "bin_size": gslvl * 100,
        "simple_prize": gslvl,
        "combined_prize": gslvl * 10,
        "silver_prize": gslvl * 10,
        "gold_prize": gslvl * 50
    }


def set_general_data(requests=None, leaderboard=None, shard_bins=None, shard_global_exp=None):
    mnm_data = dbr.get_minimal_general_data()
    if requests is not None:
        mnm_data["Requests"] = requests
    if leaderboard is not None:
        mnm_data["Leaderboard"] = leaderboard
    if shard_bins is not None:
        mnm_data["shard_bins"] = shard_bins
    if shard_global_exp is not None:
        mnm_data["shard_global_exp"] = shard_global_exp
    dbw.up_minimal_general_data(mnm_data)


def can_player_access(chat_id):
    if gut.time_s() < 1743465600:  # 1st april 2025
        return False
    return True


def april_fools(chat_id):
    cur_day = gut.time_s() // 86400
    if cur_day == (1743465600 // 86400):
        return (
            uistr.get(chat_id, "mnm April Fools"),
            [{
                uistr.get(chat_id, "mnm April Fools button"): "Main menu"
            }]
        )
    else:
        return None


def get_upgrade_costs(chat_id):
    user_data, _ = get_user_data(chat_id)
    costs = gut.production_upgrade_costs(user_data["production_level"] + 1)

    can = True
    reason = ""
    balance = get_balance(chat_id)
    if costs["Money"] > balance:
        can = False
        reason = "money"
    if costs["Blocks"] > user_data["blocks"]:
        can = False
        reason = "blocks"
    return can, costs, reason


def get_generator_status(chat_id):
    user_data, _ = get_user_data(chat_id)
    last_claim = user_data["board_timestamp"]
    time_passed = gut.time_s() - last_claim
    current_blocks = (time_passed // 3600) * user_data["generator_level"]
    board_size = 10 * (2 ** user_data["board_level"])
    if user_data["generator_level"] == 0:
        current_blocks = 0
        cur_loadbar = 0
    elif current_blocks >= board_size:
        current_blocks = board_size
        cur_loadbar = 10
    else:
        cur_loadbar = int((time_passed % 3600) / 3600 * 12)

    return current_blocks, board_size, cur_loadbar


def get_generator_up_costs(chat_id):
    user_data, _ = get_user_data(chat_id)
    return (
        int(1000 * (10 ** ((user_data["generator_level"]) / 3))),
        int(2500 * (2 ** user_data["board_level"]))
    )


def can_gear_up(chat_id):
    user_data, _ = get_user_data(chat_id)
    cur_gear_level = user_data["gear_level"]

    level_cost = gut.gear_up_level_cost(cur_gear_level, cur_gear_level + 1)
    block_prize = gut.gear_up_block_prize(cur_gear_level, cur_gear_level + 1)

    cur_prod_level = user_data["production_level"]

    if cur_prod_level <= level_cost:
        return False, level_cost, block_prize
    return True, level_cost, block_prize


def main_menu(chat_id):
    user_data, _ = get_user_data(chat_id)
    nickname = dbr.get_nickname(chat_id).copy()
    nickname["badge_line"] = user_data["gear_level"] * "L"
    message = uistr.nickname(chat_id, chat_id, nickname) + "\n"
    message += "[[" + put.readable(user_data["production_level"]) + " - " + uistr.get(
        chat_id, "MM titles")[gut.get_titlecode_forlvl(user_data["production_level"])] + "]]\n\n"

    balance = get_balance(chat_id)
    if balance < 10**10:
        money_print = put.readable(balance)
    else:
        money_print = put.pretty(balance)
    message += uistr.get(chat_id, "MM main balance").format(
        value=money_print, sym=" L")

    message += uistr.get(chat_id, "MM blocks") + put.pretty(user_data["blocks"]) + "\n\n"

    prod_rate = get_production_rate(chat_id)
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
            sym="L",
            persec_rate=persec_rate_str)
    else:
        pmint = prod_rate // 60
        pmcent = ((prod_rate * 10 + 3) // 6) % 100
        if pmcent < 10:
            pmcent = "0" + str(pmcent)
        permin_rate_str = str(pmint) + "." + str(pmcent)
        message += uistr.get(chat_id, "MM production w min").format(
            hourly_rate=put.pretty(prod_rate),
            sym="L",
            permin_rate=permin_rate_str)

    user_can_upgrade, costs, _ = get_upgrade_costs(chat_id)
    if not user_can_upgrade:
        money_to_up = costs["Money"] - balance
        blocks_to_up = costs["Blocks"] - user_data["blocks"]
        message += "\n" + uistr.get(chat_id, "MM needed to upgrade")
        if money_to_up > 0 and prod_rate > 0:
            time_left = (costs["Money"] - balance) / prod_rate
            message += uistr.get(
                chat_id, "MM needed money").format(
                val=put.pretty(money_to_up),
                sym="L")
            if time_left * 60 < 3:
                message += random.choice(uistr.get(
                    chat_id, "MM needed money seconds")).format(
                    time=int(time_left * 60 * 60))
            elif time_left * 60 < 90:
                message += uistr.get(
                    chat_id, "MM needed money minutes").format(
                    val=put.pretty(money_to_up),
                    sym="L",
                    time=int(time_left * 60))
            elif time_left < 120:
                message += uistr.get(chat_id, "MM needed money hours").format(
                    val=put.pretty(money_to_up),
                    sym="L",
                    time=int(time_left + 0.5))
            else:
                message += uistr.get(chat_id, "MM needed money days").format(
                    val=put.pretty(money_to_up),
                    sym="L",
                    time=int(time_left / 24))
        if blocks_to_up > 0:
            message += uistr.get(chat_id, "MM needed blocks").format(
                val=put.pretty(blocks_to_up)
            )

    keyboard = []
    if user_can_upgrade:
        button_string = (
            "🔼 " + put.pretty(costs["Money"]) + " L" +
            " & " + put.pretty(costs["Blocks"]) + " " + "mLmb"
        )
        keyboard.append({button_string: "Upgrade Production"})
    keyboard.append({
        uistr.get(chat_id, "button block market"): "Market",
        uistr.get(chat_id, "button leaderboard"): "Leaderboard"
    })
    gen_up_cost, board_up_cost = get_generator_up_costs(chat_id)
    if user_data["generator_level"] > 0:
        board_blocks, board_size, cur_loadbar = get_generator_status(chat_id)
        board_line = "|" + "=" * cur_loadbar + "−" * (12 - cur_loadbar) + "|"
        keyboard.append({
            board_line + f" {put.pretty(board_blocks)}/{put.pretty(board_size)} ({put.pretty(user_data['generator_level'])} mLmb/h)": "Board Claim"
        })

        keyboard.append({
            "🔼 " + uistr.get(chat_id, "button up generator") + put.pretty(
                gen_up_cost) + " L": "Generator Up",
            "🔼 " + uistr.get(chat_id, "button up board") + put.pretty(
                board_up_cost) + " L": "Board Up"
        })
    else:
        keyboard.append({
            "🔼 " + uistr.get(chat_id, "button start generator") + put.pretty(
                gen_up_cost) + " L": "Generator Up"})

    if can_gear_up(chat_id)[0]:
        keyboard.append({
            "IBTV 📺": "Back",
            "⚙️ 📦 ⚙️": "Gear",
            uistr.get(chat_id, "button update"): "Main menu"
        })
    else:
        keyboard.append({
            "IBTV 📺": "Back",
            uistr.get(chat_id, "button update"): "Main menu"
        })
    return message, keyboard


def payment(qty, from_id=None, to_id=None, commit=False):
    if from_id:
        from_user_data, _ = get_user_data(from_id)
        from_user_data["saved_balance"] -= qty
        if commit and to_id is None:
            set_user_data(from_id, from_user_data)
    if to_id:
        to_user_data, _ = get_user_data(to_id)
        to_user_data["saved_balance"] += qty
        if commit:
            set_user_data(to_id, to_user_data)


def block_transfer(qty, from_id=None, to_id=None, commit=False):
    if from_id:
        from_user_data, _ = get_user_data(from_id)
        from_user_data["blocks"] -= qty
        if commit and to_id is None:
            set_user_data(from_id, from_user_data)
    if to_id:
        to_user_data, _ = get_user_data(to_id)
        to_user_data["blocks"] += qty
        if commit:
            set_user_data(to_id, to_user_data)


def upgrade_money_printer(chat_id):
    user_data, _ = get_user_data(chat_id)
    _, costs, reason = get_upgrade_costs(chat_id)
    if reason == "money":
        return uistr.get(chat_id, "Insufficient balance")
    elif reason == "blocks":
        return uistr.get(chat_id, "Insufficient blocks")
    # If reason is neither, then the player can upgrade
    payment(costs["Money"], from_id=chat_id)
    block_transfer(costs["Blocks"], from_id=chat_id)
    user_data["saved_balance"] = get_balance(chat_id)
    user_data["balance_timestamp"] = gut.time_s()
    user_data["production_level"] += 1
    set_user_data(chat_id, user_data)
    update_leaderboard(chat_id)
    return uistr.get(chat_id, "Done")


def generator_time_to_shards(total_generator_time, uslvl, gslvl):
    partial_minutes = total_generator_time % (60 * 60) // 60
    completed_hours = total_generator_time // (60 * 60)

    simple_shard_color = ["red", "green", "blue"][(gut.time_s() // (60 * 60 * 8)) % 3]

    shards = {}

    # Partial minutes shards, and uslvl bonus
    if partial_minutes >= 30:
        shards["gold"] = (1 * (uslvl + 4)) // 5
        partial_minutes -= 30
    if partial_minutes >= 10:
        shards["silver"] = ((partial_minutes // 10) * (uslvl + 2)) // 3
        partial_minutes = partial_minutes % 10
    if partial_minutes > 0:
        shards[simple_shard_color] = (partial_minutes * (uslvl + 1)) // 2

    # Completed hours gslvl bonus
    prod_val = (gslvl - 1) * completed_hours
    if prod_val > 0:
        if simple_shard_color not in shards:
            shards[simple_shard_color] = 0
        shards[simple_shard_color] += prod_val
    if prod_val >= 10:
        if "silver" not in shards:
            shards["silver"] = 0
        shards["silver"] += prod_val // 10
    if prod_val >= 50:
        if "gold" not in shards:
            shards["gold"] = 0
        shards["gold"] += prod_val // 50

    # Completed hours extra shards
    if completed_hours >= 20:
        if "gold" not in shards:
            shards["gold"] = 0
        shards["gold"] += completed_hours // 20
        completed_hours = completed_hours % 20
    if completed_hours >= 5:
        if "silver" not in shards:
            shards["silver"] = 0
        shards["silver"] += [1, 2, 4][(completed_hours // 5) - 1]
        completed_hours = completed_hours % 5
    if completed_hours >= 1:
        if simple_shard_color not in shards:
            shards[simple_shard_color] = 0
        shards[simple_shard_color] += [1, 2, 4, 7][completed_hours - 1]
    return shards


def contribute_shards(chat_id, contr_shards, gslvl):
    money = 0
    blocks = 0

    compensation_base = 0
    requests, _ = get_general_data()
    user_data, _ = get_user_data(chat_id)

    if len(requests) > 0:
        requests = sorted(requests, key=lambda item: item["price"], reverse=True)
        compensation_base = requests[0]["price"]

    shard_bins, shard_global_exp = get_shard_bins()

    # Contributing simple, silver and gold shards
    for colour in ["red", "green", "blue"]:
        if colour in contr_shards:
            shard_bins[colour] += contr_shards[colour]
            money += (contr_shards[colour] * compensation_base) // 100
            user_data["shard_exp"] += contr_shards[colour]
            shard_global_exp += contr_shards[colour]
    if "silver" in contr_shards:
        shard_bins["silver"] += contr_shards["silver"]
        money += (contr_shards["silver"] * compensation_base) // 10
        user_data["shard_exp"] += contr_shards["silver"] * 20
        shard_global_exp += contr_shards["silver"] * 20
    if "gold" in contr_shards:
        shard_bins["gold"] += contr_shards["gold"]
        money += (contr_shards["gold"] * compensation_base) // 2
        user_data["shard_exp"] += contr_shards["gold"] * 100
        shard_global_exp += contr_shards["gold"] * 100

    # Generating combination shards and getting blocks from simple ones
    combinations = {
        ("red", "green"): "yellow",
        ("green", "blue"): "cyan",
        ("blue", "red"): "magenta"
    }
    check_order = [
        ["red", "green", "blue"][(gut.time_s() // (60 * 60 * 8) + i) % 3]
        for i in range(3)
    ]

    tot_req_blocks = sum([req["blocks"]for req in requests])
    sb_data = shard_bin_sizes(gslvl)

    for round in [1, 2]:
        for c in range(3):
            if blocks + sb_data["simple_prize"] > tot_req_blocks:
                break
            c1 = check_order[c]
            c2 = check_order[(c + round) % 3]
            if round == 1:
                cc = combinations[(c1, c2)]
            else:
                cc = combinations[(c2, c1)]
            if shard_bins[c1] // 2 + shard_bins[c2] // 2 >= sb_data['bin_size']:
                if shard_bins[c1] >= shard_bins[c2]:  # other side will be checked on second round
                    max_comb_qty = sb_data['bin_size'] // 5
                    if shard_bins[c2] // 2 >= sb_data['bin_size'] // 2:
                        shard_bins[c2] -= sb_data['bin_size'] // 2
                        shard_bins[c1] -= sb_data['bin_size'] // 2
                        combined_quantity = max_comb_qty
                    else:
                        c2_qty = shard_bins[c2] // 2
                        c1_qty = sb_data['bin_size'] - (shard_bins[c2] // 2)
                        shard_bins[c2] -= c2_qty
                        shard_bins[c1] -= c1_qty
                        combined_quantity = max(0, max_comb_qty - 2 * ((sb_data['bin_size'] // 2) - c2_qty))
                    shard_bins[cc] += combined_quantity
                    shard_global_exp += combined_quantity * 2
                    blocks += sb_data["simple_prize"]

    # Getting blocks from combined, silver and gold shards
    for colour in ["yellow", "cyan", "magenta"]:
        if shard_bins[colour] >= sb_data['bin_size'] and blocks <= tot_req_blocks - sb_data['combined_prize']:
            shard_bins[colour] -= sb_data['bin_size']
            blocks += sb_data['combined_prize']

    if shard_bins["silver"] >= sb_data['bin_size'] and blocks <= tot_req_blocks - sb_data['silver_prize']:
        shard_bins["silver"] -= sb_data['bin_size']
        blocks += sb_data['silver_prize']

    if shard_bins["gold"] >= sb_data['bin_size'] and blocks <= tot_req_blocks - sb_data['gold_prize']:
        shard_bins["gold"] -= sb_data['bin_size']
        blocks += sb_data['gold_prize']

    # Giving blocks to market
    while blocks > 0 and len(requests) > 0:
        qty = min(blocks, requests[0]["blocks"])
        block_transfer(qty, to_id=requests[0]["chat_id"], commit=True)
        requests[0]["blocks"] -= qty
        blocks -= qty
        if requests[0]["blocks"] <= 0:
            requests = requests[1:]
    set_general_data(requests=requests, shard_bins=shard_bins, shard_global_exp=shard_global_exp)
    # User data is set afterwards

    return money


def float_to_residualbar(res_float, lnt=10):
    bar = ["–"] * lnt
    for i in range(lnt):
        fi = (i + 1) / lnt
        if res_float >= fi:
            bar[i] = "0"
        elif res_float > fi - (1 / lnt):
            val = str(int(
                (res_float - fi + (1 / lnt)) * lnt * 10
            ))
            if val != "0":
                bar[i] = val
    return ''.join(bar)


def shard_bin_screen(chat_id):
    shard_bins, shard_global_exp = get_shard_bins()
    uslvl, gslvl, usres, gsres = get_shard_levels(chat_id, residuals=True)
    sb_data = shard_bin_sizes(gslvl)
    message = "`S°°S°°S°°S°°S°°S°°S°°S`"
    for shard_type in ["red", "green", "blue", "_", "yellow", "cyan", "magenta", "_", "silver", "gold"]:
        if shard_type == "_":
            message += "\n"
            continue
        message += "\n" + uistr.get(chat_id, f"mnm shard name {shard_type}") + f": {shard_bins[shard_type]} / {sb_data['bin_size']}"
        if shard_type in ["red", "green", "blue"]:
            sb_data_type = "simple_prize"
        elif shard_type in ["yellow", "cyan", "magenta"]:
            sb_data_type = "combined_prize"
        else:
            sb_data_type = f"{shard_type}_prize"
        message += f" → {sb_data[sb_data_type]} mLmb"

    shard_user_exp = get_user_data(chat_id)[0]["shard_exp"]

    message += "\n\n"
    message += f"`UrsLvl {uslvl} - [{float_to_residualbar(usres)}]`\n"
    message += f"`GlbLvl {gslvl} - [{float_to_residualbar(gsres)}]`"
    return message


def claim_board(chat_id):
    current_blocks, _, _ = get_generator_status(chat_id)
    if current_blocks == 0:
        return uistr.get(chat_id, "mnm Board empty")

    message = ""
    user_data, _ = get_user_data(chat_id)
    block_transfer(current_blocks, to_id=chat_id)
    message += uistr.get(chat_id, "mnm Board Claim base blocks").format(
        qty=put.pretty(current_blocks)
    )
    uslvl, gslvl = get_shard_levels(chat_id)
    shards = generator_time_to_shards(gut.time_s() - user_data["board_timestamp"], uslvl, gslvl)
    if len(shards) > 0:
        message += "\n" + uistr.get(chat_id, "mnm Board Claim shard start")
        for shard_type in shards:
            message += uistr.get(chat_id, "mnm Board Claim shard part").format(
                shard_type=uistr.get(chat_id, f"mnm shard name {shard_type}"),
                qty=shards[shard_type]
            )
        message += "."
        contr_money = contribute_shards(chat_id, shards, gslvl)
        if contr_money > 0:
            message += "\n" + uistr.get(chat_id, "mnm Board Claim contribution money").format(
                qty=put.pretty(contr_money)
            )
            payment(contr_money, to_id=chat_id)

    user_data["board_timestamp"] = gut.time_s()
    set_user_data(chat_id, user_data)
    return message


def upgrade_block_generator(chat_id):
    user_data, _ = get_user_data(chat_id)
    gen_up_cost, _ = get_generator_up_costs(chat_id)
    if get_balance(chat_id) < gen_up_cost:
        return uistr.get(chat_id, "Insufficient balance")
    payment(gen_up_cost, from_id=chat_id)
    current_blocks, _, _ = get_generator_status(chat_id)
    if current_blocks > 0:
        block_transfer(current_blocks, to_id=chat_id)
    user_data["generator_level"] += 1
    user_data["board_timestamp"] = gut.time_s()
    set_user_data(chat_id, user_data)
    return uistr.get(chat_id, "Done")


def upgrade_generator_board(chat_id):
    user_data, _ = get_user_data(chat_id)
    _, board_up_cost = get_generator_up_costs(chat_id)
    if get_balance(chat_id) < board_up_cost:
        return uistr.get(chat_id, "Insufficient balance")
    payment(board_up_cost, from_id=chat_id)
    user_data["board_level"] += 1
    set_user_data(chat_id, user_data)
    return uistr.get(chat_id, "Done")


def gear_up(chat_id):
    user_data, _ = get_user_data(chat_id)
    can, level_cost, block_prize = can_gear_up(chat_id)
    if not can:
        return uistr.get(chat_id, "Gearup not available")
    user_data["saved_balance"] = get_balance(chat_id)
    user_data["balance_timestamp"] = gut.time_s()
    user_data["gear_level"] += 1
    user_data["production_level"] -= level_cost
    block_transfer(block_prize, to_id=chat_id, commit=True)
    best.inventory_give(chat_id, "mystery_item", 1)
    update_leaderboard(chat_id)
    return uistr.get(chat_id, "found mystery item")


def block_market_menu(chat_id):
    requests, _ = get_general_data()
    requests = sorted(requests, key=lambda item: item["price"], reverse=True)
    message = uistr.get(chat_id, "mnm Market")
    if len(requests) == 0:
        message += uistr.get(chat_id, "mnm Market empty")
        max_price = 0
    else:
        max_price = requests[0]["price"]
        for rq in requests:
            if rq["chat_id"] == chat_id:
                message += ">"
            else:
                message += "−"
            message += f' {rq["blocks"]} mLmb, {put.pretty(rq["price"])} L/mLmb\n'

    keyboard = []
    user_data, _ = get_user_data(chat_id)
    _, costs, _ = get_upgrade_costs(chat_id)
    player_price = max(
        max_price + max_price // 10,
        get_production_rate(chat_id) // 12,  # 5 minutes of production
        100
    )

    keyboard.append({uistr.get(chat_id, "mnm Market offer button one").format(
        price=put.pretty(player_price)
    ): "Market offer 1"})
    needed_blocks = costs["Blocks"] - user_data["blocks"]
    if needed_blocks > 1:
        keyboard.append({uistr.get(chat_id, "mnm Market offer button many").format(
            price=put.pretty(player_price * needed_blocks),
            blocks=put.pretty(needed_blocks)
        ): f"Market offer {needed_blocks}"})
    if len(requests) > 0:
        keyboard.append({uistr.get(chat_id, "mnm Market sell button").format(
            price=put.pretty(max_price)
        ): "Market sell"})

    keyboard.append({
        uistr.get(chat_id, "mnm Shard Screen button"): "Shard Screen",
        uistr.get(chat_id, "button back"): "Main menu"
    })
    return message, keyboard


def block_market_offer(chat_id, qty):
    requests, _ = get_general_data()
    requests = sorted(requests, key=lambda item: item["price"], reverse=True)
    if len(requests) == 0:
        max_price = 0
    else:
        max_price = requests[0]["price"]

    player_price = max(
        max_price + max_price // 10,
        get_production_rate(chat_id) // 12  # 5 minutes of production
    )
    if get_balance(chat_id) < player_price * qty:
        return uistr.get(chat_id, "Insufficient balance")
    payment(player_price * qty, from_id=chat_id, commit=True)
    requests.append({
        "chat_id": chat_id,
        "price": player_price,
        "blocks": qty
    })
    set_general_data(requests=requests)
    return uistr.get(chat_id, "Done")


def block_market_sell(chat_id):
    requests, _ = get_general_data()
    requests = sorted(requests, key=lambda item: item["price"], reverse=True)
    if len(requests) == 0:
        return uistr.get(chat_id, "mnm Market empty") + " bro"
    user_data, _ = get_user_data(chat_id)
    if user_data["blocks"] == 0:
        return uistr.get(chat_id, "No MMMB found") + " bro"
    max_price = requests[0]["price"]
    payment(max_price, to_id=chat_id)
    block_transfer(1, from_id=chat_id, to_id=requests[0]["chat_id"], commit=True)
    requests[0]["blocks"] -= 1
    if requests[0]["blocks"] <= 0:
        requests = requests[1:]
    set_general_data(requests=requests)
    return uistr.get(chat_id, "Done")


def leaderboard(chat_id):
    _, leaderboard = get_general_data()
    leaderboard = sorted(
        leaderboard,
        key=lambda x_id: (
            -get_user_data(x_id)[0]["gear_level"],
            -get_user_data(x_id)[0]["production_level"]
        )
    )  # [:10]

    message = "=L" * 10 + "=\n"
    pos = 1
    for x_id in leaderboard:
        user_data, _ = get_user_data(x_id)
        nickname = dbr.get_nickname(x_id).copy()
        nickname["badge_line"] = user_data["gear_level"] * "L"
        if x_id == chat_id:
            message += ">"
        if pos <= 10 or x_id == chat_id:
            message += f'{pos} - [[{user_data["gear_level"]} :: {user_data["production_level"]}]] - {uistr.nickname(chat_id, x_id, nickname)}\n'
        pos += 1
    return message, [{uistr.get(chat_id, "button back"): "Main menu"}]


def update_leaderboard(chat_id):
    _, leaderboard = get_general_data()
    if chat_id in leaderboard:
        return
    if len(leaderboard) < 10:
        leaderboard.append(chat_id)
    else:
        leaderboard = sorted(
            leaderboard + chat_id,
            key=lambda x_id: (
                get_user_data(x_id)[0]["gear_level"],
                get_user_data(x_id)[0]["production_level"]
            )
        )  # [:10]
    set_general_data(leaderboard=leaderboard)


def exe_and_reply(query, chat_id):
    message = ""
    keyboard = None
    if query == "Main menu":
        _, is_user_new = get_user_data(chat_id)
        if is_user_new:
            message, keyboard = april_fools(chat_id)
        else:
            message, keyboard = main_menu(chat_id)
    if query == "Upgrade Production":
        message = upgrade_money_printer(chat_id)
    if query == "Board Claim":
        message = claim_board(chat_id)
    if query == "Generator Up":
        message = upgrade_block_generator(chat_id)
    if query == "Board Up":
        message = upgrade_generator_board(chat_id)
    if query == "Gear":
        message = gear_up(chat_id)

    if query == "Market":
        message, keyboard = block_market_menu(chat_id)
    if "Market offer" in query:
        qty = int(query.split()[2])
        message = block_market_offer(chat_id, qty)
        m, keyboard = block_market_menu(chat_id)
        message += "\n" + "-" * 20 + "\n" + m
    if "Market sell" in query:
        message = block_market_sell(chat_id)
        m, keyboard = block_market_menu(chat_id)
        message += "\n" + "-" * 20 + "\n" + m

    if query == "Leaderboard":
        message, keyboard = leaderboard(chat_id)

    if query == "Shard Screen":
        message = shard_bin_screen(chat_id)

    if keyboard:
        for row in keyboard:
            for button in row:
                row[button] = "mnm " + row[button]
    return message, keyboard
