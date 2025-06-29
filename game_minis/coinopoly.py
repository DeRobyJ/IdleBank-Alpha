from game_minis._common import *
from game_minis.shop_chain import economy_inflation

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

