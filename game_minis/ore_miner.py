from _common import *

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
