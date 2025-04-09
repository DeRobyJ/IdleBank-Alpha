# This is the place all UI (strings) are formatted
# You could say this is half of the front-end
import json
import game_dbread as dbr
import conversions as conv
import time
from db_chdata import pioneers


f = open("localisation_strings.json")
strings = json.load(f)


def get(chat_id, str_name):
    lang = dbr.get_language(chat_id)
    if lang not in strings[str_name]:
        lang = "English"
    if len(strings[str_name][lang]) == 0:
        lang = "English"
    return strings[str_name][lang]


dn_flags = [
    "🇨🇦", "🇫🇷", "🇩🇪", "🇯🇵", "🇮🇹",
    "🇬🇧", "🇺🇸", "🇧🇷", "🇷🇺", "🇨🇳",
    "🇮🇳", "🇿🇦", "🇦🇺", "🇸🇦", "🇦🇷",
    "🇰🇷", "🇮🇩", "🇲🇽", "🇹🇷", "🇪🇸"
]


def dn_country(chat_id, country_id):
    return dn_flags[int(country_id)] + " " + get(chat_id, "DN countries")[int(
        country_id)]


def sr_product(chat_id, item_code):
    lang = dbr.get_language(chat_id)
    if lang not in strings["SR products"][item_code]:
        lang = "English"
    if len(strings["SR products"][item_code][lang]) == 0:
        lang = "English"
    return strings["SR products"][item_code][lang]


gendered_languages = ["Italiano", "Português"]


def apply_gender(language, word, gender):
    if language not in gendered_languages:
        return word
    if language == "Italiano":
        if gender == "f":
            return word.replace("*", "a")
        if gender == "m":
            return word.replace("*", "o")
    if language == "Português":
        if word in ["Impressor*", "Investidor*", "Encantador*"]:
            if gender == "f":
                return word.replace("*", "a")
            if gender == "m":
                return word.replace("*", "")
        else:
            if gender == "f":
                return word.replace("*", "a")
            if gender == "m":
                return word.replace("*", "o")


def supergear_badges(chat_id, value):
    line = ""

    # Elemental Stars
    line += chr(314) * (value // (21 * 5))
    value %= 21 * 5

    # Elements
    elemental = value // 21
    if elemental > 0:
        line += chr(310 + elemental - 1)  # max chr(313)
    value %= 21

    # Monuments
    monument_count = 0
    while value >= 3:
        monument_count += 1
        line += chr(300 + ((chat_id // 100 + monument_count)) % 6)
        value -= 3

    # Jewelry
    if value == 1:
        line += "α"
    elif value == 2:
        line += "β"
    return line


# nick_data: dictionary
#   "language": <a language or "Translate">
#   "adjective_1": number
#   "adjective_2": number
#   "noun": number


def nickname(reader_id, player_id, nick_data, compress=True):
    if nick_data["language"] == "Translate":
        language = dbr.get_language(reader_id)
        if language not in strings["NICK structure"]:
            language = "English"
    else:
        language = nick_data["language"]

    structure = strings["NICK structure"][language]
    gender = ""
    if language in gendered_languages:
        gender = strings["NICK noun"][language + "_gender"][nick_data["noun"]]
    adj1 = strings["NICK adjective_1"][language][nick_data["adjective_1"]]
    adj2 = strings["NICK adjective_2"][language][nick_data["adjective_2"]]
    noun = strings["NICK noun"][language][nick_data["noun"]]

    badgemoji = {
        "D": conv.name(membership="FED")["badgemoji"],
        "E": conv.name(membership="ECB")["badgemoji"],
        "Y": conv.name(membership="PBC")["badgemoji"],
        "O": conv.name(membership="RBA")["badgemoji"],
        "B": conv.name(membership="CBB")["badgemoji"],
        "I": conv.name(membership="RBI")["badgemoji"],
        "A": conv.name(membership="ACB")["badgemoji"],
        "L": "🍪",
        "1": "1️⃣",
        "2": "2️⃣",
        "3": "3️⃣",
        "4": "4️⃣",
        "5": "5️⃣",
        "6": "6️⃣",
        "7": "7️⃣",
        "8": "8️⃣",
        "9": "9️⃣",
        "0": "🔟",
        "α": "💍",
        "β": "👑",
        chr(300): "🗿",
        chr(301): "🗽",
        chr(302): "🗼",
        chr(303): "🚀",
        chr(304): "🌋",
        chr(305): "🏛",
        chr(310): "💧",
        chr(311): "🍀",
        chr(312): "🔥",
        chr(313): "⚡️",
        chr(314): "🌟"
    }

    badge_line = ""
    if player_id in pioneers:
        if pioneers[player_id]["gear_level"] >= 1000:
            badge_line += "🌐"
        elif pioneers[player_id]["gear_level"] >= 100:
            badge_line += "🎩"
        elif pioneers[player_id]["gear_level"] >= 10:
            badge_line += "👒"
        elif pioneers[player_id]["gear_level"] >= 1:
            badge_line += "🧢"
    if compress:
        if "badge_line" in nick_data:
            supergears = len(nick_data["badge_line"]) // 100
            cumul_badges_value = max(
                0,
                (len(nick_data["badge_line"]) % 100 - 1) // 5
            )
            shortened_badge_line = nick_data[
                "badge_line"][cumul_badges_value * 5 + supergears * 100:]
            if cumul_badges_value % 10 > 0 and cumul_badges_value > 0:
                shortened_badge_line = str(
                    cumul_badges_value % 10) + shortened_badge_line
            while cumul_badges_value >= 10:
                shortened_badge_line = "0" + shortened_badge_line
                cumul_badges_value -= 10
            shortened_badge_line = supergear_badges(
                player_id, supergears) + shortened_badge_line
            for badge in shortened_badge_line:
                badge_line += badgemoji[badge]
    else:
        supergears = len(nick_data["badge_line"]) // 100
        if supergears > 0:
            superbadges = supergear_badges(player_id, supergears)
            badge_line = "Super: " + badge_line
            for badge in superbadges:
                badge_line += badgemoji[badge]
            badge_line += "\n"
        badge_line += all_badges(nick_data["badge_line"][supergears * 100:])
        # badges_printed = 0
        # for badge in nick_data["badge_line"][supergears * 100:]:
        #    badge_line += badgemoji[badge]
        #    badges_printed += 1
        #    if badges_printed % 10 == 0:
        #        badge_line += '\n'

    nname = structure.format(
        adjective_1=apply_gender(language, adj1, gender),
        adjective_2=apply_gender(language, adj2, gender),
        noun=noun
    )
    if badge_line == "":
        return nname
    return nname + "\n" + badge_line


def all_badges(raw_line, summary=True):
    badgemoji = {
        "D": conv.name(membership="FED")["badgemoji"],
        "E": conv.name(membership="ECB")["badgemoji"],
        "Y": conv.name(membership="PBC")["badgemoji"],
        "O": conv.name(membership="RBA")["badgemoji"],
        "B": conv.name(membership="CBB")["badgemoji"],
        "I": conv.name(membership="RBI")["badgemoji"],
        "A": conv.name(membership="ACB")["badgemoji"]
    }
    badge_line = ""
    badges_in_line = 0
    i = 0
    while i < len(raw_line):
        badge_line += badgemoji[raw_line[i]]
        j = 0
        while raw_line[i] == raw_line[i + j]:
            j += 1
            if i + j >= len(raw_line):
                break
        if j in [2, 3]:
            badge_line += badgemoji[raw_line[i]] * (j - 1)
        elif j > 3:
            badge_line += "x" + str(j)
            badges_in_line += 1 + len(str(j))
        i += j
        badges_in_line += 1
        if badges_in_line >= 14:
            badges_in_line = 0
            badge_line += '\n'
    return badge_line + "\n"


def get_available_languages():
    return [i for i in strings["Done"]]


def nick_change(chat_id, current_data, field_to_change):
    new_data = current_data.copy()
    if field_to_change in ["adjective_1", "adjective_2", "noun"]:
        new_data[field_to_change] = (current_data[field_to_change] + 1) % len(
            strings["NICK " + field_to_change]["English"])
    elif field_to_change == "language":
        if current_data["language"] == "Translate":
            new_data["language"] = dbr.get_language(chat_id)
        else:
            new_data["language"] = "Translate"
    return new_data


def nick_query_pack(nick_data, query_name):
    query_data = [
        nick_data["language"],
        nick_data["adjective_1"],
        nick_data["adjective_2"],
        nick_data["noun"]
    ]
    return query_name + " " + json.dumps(query_data)


def nick_query_unpack(query_data, query_name):
    query_data = json.loads(query_data[(len(query_name) + 1):])
    if len(query_data) == 0:
        return
    nick_data = {}
    nick_data["language"] = query_data[0]
    nick_data["adjective_1"] = query_data[1]
    nick_data["adjective_2"] = query_data[2]
    nick_data["noun"] = query_data[3]
    return nick_data


def get_tutorial_line(chat_id, player_level):
    tut_keys = [
        "Newcomer",  # 0
        "Block Selling",  # 1
        "",
        "Global Production",  # 3
        "Leaderboard",  # 4
        "Minigame Daily News",  # 5
        "Minigame Ore Miner",  # 6
        "Block Requesting",  # 7
        "Minigame Investment Plan",  # 8
        "End of tips",  # 9
        "Minigame Coinopoly",  # 10
        "Minigame Global Steel Road"  # 11
    ]
    emojis = [
        "🆙",  # "Newcomer",                 #0
        "♻️",  # "Block Selling",            #1
        "",
        "🌐",  # "Global Production",        #3
        "🌐👥",  # "Leaderboard",              #4
        "🎮📰",  # "Minigame Daily News",      #5
        "🎮⛏",  # "Minigame Ore Miner",       #6
        "📦",  # "Block Requesting",         #7
        "🎮📈",  # "Minigame Investment Plan", #8
        "🆗",  # "End of tips"               #9
        "⛓️",  # "Minigame Coinopoly",  # 10
        "🚂"  # "Minigame Global Steel Road"  # 11
    ]

    lvls = {
        0: 0,
        1: 0,
        2: 1,
        3: 1,
        5: 4,
        6: 4,
        # 8: 4,
        # 9: 4,
        10: 5,
        11: 5,
        15: 10,
        16: 10,
        20: 6,
        21: 6,
        25: 11,
        26: 11,
        30: 7,
        31: 7,
        35: 8,
        36: 9
    }

    if player_level not in lvls:
        return ""

    tutorial_key = tut_keys[lvls[player_level]]
    emoji = emojis[lvls[player_level]]
    lang = dbr.get_language(chat_id)
    if lang not in strings["MM Tips"][tutorial_key]:
        lang = "English"
    return emoji + " " + strings["MM Tips"][tutorial_key][lang]


def date_string(chat_id, ts):
    date_struct_t = time.gmtime(ts)
    return str(
        date_struct_t.tm_mday) + " " + get(
        chat_id, "Month")[date_struct_t.tm_mon - 1] + " " + str(
        date_struct_t.tm_year
    )


news_agency_names = [
    "IBA", "Hot", "24", "Live", "Chan", "News", "TV", "DRJ", "Glob", "Line",
    "Free", "Ind", "Dash", "One", "On", "Air", "All", "Sat", "Sup", "Day", "Fin",
    "Info", "Uni", "Fast", "Cam", "Full", "In", "Plus", "Hack", "New", "Nova"
]
