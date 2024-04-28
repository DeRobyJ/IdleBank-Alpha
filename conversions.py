# in: membership, currency or block
# out: membership, currency, block, currency symbol, badge letter
def name(membership=None, currency=None, block=None):
    if membership:
        if membership == "FED":
            return {
                "currency": "Dollar",
                "block": "mUSDmb",
                "symbol": "US$",
                "badge_letter": "D",
                "badgemoji": "💵"
            }
        if membership == "ECB":
            return {
                "currency": "Euro",
                "block": "mEmb",
                "symbol": "€",
                "badge_letter": "E",
                "badgemoji": "💶"
            }
        if membership == "PBC":
            return {
                "currency": "Yuan",
                "block": "mYmb",
                "symbol": "¥",
                "badge_letter": "Y",
                "badgemoji": "💴"
            }
        if membership == "RBA":
            return {
                "currency": "AUDollar",
                "block": "mAUDmb",
                "symbol": "AU$",
                "badge_letter": "O",
                "badgemoji": "🌊"
            }
        if membership == "CBB":
            return {
                "currency": "Real",
                "block": "mBRmb",
                "symbol": "R$",
                "badge_letter": "B",
                "badgemoji": "🐊"
            }
        if membership == "RBI":
            return {
                "currency": "Rupee",
                "block": "mIRmb",
                "symbol": "₹",
                "badge_letter": "I",
                "badgemoji": "🪔"
            }
        if membership == "ACB":
            return {
                "currency": "Afro",
                "block": "mAmb",
                "symbol": "A",
                "badge_letter": "A",
                "badgemoji": "🌍"
            }
    if currency:
        memb = {
            "Dollar": "FED",
            "Euro": "ECB",
            "Yuan": "PBC",
            "AUDollar": "RBA",
            "Real": "CBB",
            "Rupee": "RBI",
            "Afro": "ACB"
        }[currency]
    if block:
        memb = {
            "mUSDmb": "FED",
            "mEmb": "ECB",
            "mYmb": "PBC",
            "mAUDmb": "RBA",
            "mBRmb": "CBB",
            "mIRmb": "RBI",
            "mAmb": "ACB"
        }[block]
    return {
        "membership": memb,
        "currency": name(membership=memb)["currency"],
        "block": name(membership=memb)["block"],
        "symbol": name(membership=memb)["symbol"],
        "badge_letter": name(membership=memb)["badge_letter"],
        "badgemoji": name(membership=memb)["badgemoji"]

    }
    return None


# Deprecated, uses the ranking of global production to convert between currencies
def currency(cur_status, amount, currency, original_currency=None):
    cur_order = [(i, cur_status[i]) for i in cur_status]
    cur_order = sorted(cur_order, key=lambda item: item[1], reverse=True)
    cur_order = [i[0] for i in cur_order]
    highest_cur = cur_order[0]
    change_rate = {i: max(0.1, (cur_status[i] / cur_status[highest_cur]))
                   for i in cur_status}

    if original_currency:
        amount = int(amount / change_rate[original_currency])
    return int(max(1, amount * change_rate[currency]))
