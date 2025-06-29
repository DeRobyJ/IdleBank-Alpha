from _common import *

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
    if owner_chat_id not in sr_cached_awards["players"]:
        sr_cached_awards["players"][owner_chat_id] = 0
    sr_cached_awards["players"][owner_chat_id] += int(qty)


def SR_factory_give_cached_awards(start_time):
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
