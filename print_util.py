# Before this, I thought all numers would stay low enough to be easy to read.
# What a fool!

def shorten(value, to=None, cut=None):
    if to:
        digits = len(str(value))
        cut = digits - to
    if cut:
        return (value + 5 * 10**(cut - 1)) // (10**cut)


def readable(value):
    if value >= 1000:
        return readable(value // 1000) + "'" + str(value)[-3:]
    else:
        return str(value)


def pretty_old(value):
    if value < 10**4:
        return readable(value) + " "
    if value < 10**7:
        return readable(shorten(value, cut=3)) + " k"
    if value < 10**10:
        return readable(shorten(value, cut=6)) + " m"
    return pretty(shorten(value, cut=9)) + "b"


def pretty(value):
    value = str(value)
    order = len(value) - 1
    if order == 0:
        return value + " "
    prefix = ""
    while order >= 9:
        prefix += "b"
        order -= 9
    if order >= 6:
        prefix = "m" + prefix
        order -= 6
    elif order >= 3:
        prefix = "k" + prefix
        order -= 3
    if order == 0:
        return value[0] + "." + value[1] + " " + prefix
    return value[0:order + 1] + " " + prefix


def pretty_time(timestamp):
    pretty_str = ""
    days_ts = timestamp // (60 * 60 * 24)
    hours_ts = (timestamp // (60 * 60)) % 24
    minutes_ts = (timestamp // 60) % 60
    seconds_ts = timestamp % 60
    if days_ts >= 7:
        pretty_str += str(days_ts) + "d"
    elif days_ts >= 1:
        pretty_str += str(days_ts) + "d" + str(hours_ts) + "h"
    elif hours_ts >= 1:
        pretty_str += str(hours_ts) + "h" + str(minutes_ts) + "m"
    else:
        pretty_str += "0h" + str(minutes_ts) + "m" + str(seconds_ts) + "s"
    return pretty_str
