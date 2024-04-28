import os

import boto3
import decimal
dynamodb = boto3.client('dynamodb')
dynaresource = boto3.resource('dynamodb', region_name='eu-south-1')


def item_update(tabname, selection_dict, up_attribute, up_value_dict):
    global dynamodb
    if "chat_id" in selection_dict:
        selection_dict["chat_id"]["N"] = str(selection_dict["chat_id"]["N"])
    if "N" in up_value_dict:
        up_value_dict["N"] = str(up_value_dict["N"])
    if tabname == tabname_user and up_attribute == "saved_balance":
        balance_exponent = max(0, len(up_value_dict["N"]) - 36)
        if balance_exponent > 0:
            up_value_dict["N"] = up_value_dict["N"][:-balance_exponent]
        dynamodb.update_item(
            TableName=tabname_user,
            Key=selection_dict,
            UpdateExpression='SET #attr1 = :val1',
            ExpressionAttributeNames={'#attr1': "balance_exponent"},
            ExpressionAttributeValues={':val1': {"S": str(balance_exponent)}}
        )

    dynamodb.update_item(
        TableName=tabname,
        Key=selection_dict,
        UpdateExpression='SET #attr1 = :val1',
        ExpressionAttributeNames={'#attr1': up_attribute},
        ExpressionAttributeValues={':val1': up_value_dict}
    )
    tab_puts[tabname] += 1
    print(tabname, "puts:", tab_puts[tabname])
# item_update('uselessbot-user_data', {'chat_id': {"N": str(chat_id)}},
#             "Aa_allowed_action", {"S": action})


def item_get(tabname, selection_dict, get_attribute, get_type):
    global dynamodb
    if "chat_id" in selection_dict:
        selection_dict["chat_id"]["N"] = str(selection_dict["chat_id"]["N"])
    res = dynamodb.get_item(TableName=tabname, Key=selection_dict)
    if "Item" in res:
        if get_attribute in res["Item"]:
            return res["Item"][get_attribute][get_type]
    return None
# item_get('uselessbot-user_data', {'chat_id': {"N": str(chat_id)}},
#          "Aa_allowed_action", "S")


# Only used to get user_data and market_data
def object_get(tabname, selection_dict):
    global dynamodb
    if "chat_id" in selection_dict:
        selection_dict["chat_id"]["N"] = str(selection_dict["chat_id"]["N"])
    res = dynamodb.get_item(TableName=tabname, Key=selection_dict)
    if "Item" in res:
        ob = {}
        for attr in res["Item"].keys():
            if "N" in res["Item"][attr]:
                ob[attr] = int(res["Item"][attr]["N"])
            elif "S" in res["Item"][attr]:
                ob[attr] = res["Item"][attr]["S"]
            elif "M" in res["Item"][attr]:
                ob[attr] = res["Item"][attr]["M"]
            elif "NS" in res["Item"][attr]:
                ob[attr] = res["Item"][attr]["NS"]
        if tabname == tabname_user:
            if "saved_balance" in ob:
                if "balance_exponent" not in ob:
                    balance_exponent = 0
                else:
                    balance_exponent = int(ob["balance_exponent"])
                ob["saved_balance"] = int(ob["saved_balance"] * (10**balance_exponent))
        if tabname == tabname_market:
            if "money_exponent" not in ob:
                money_exponent = 0
            else:
                money_exponent = int(ob["money_exponent"])
            ob["money"] = int(ob["money"] * (10**money_exponent))
            ob["money_limit"] = int(ob["money_limit"] * (10**money_exponent))
        return ob
    return None


# Convert all whole number decimals in `obj` to integers,
# convert all sets in lists
def res_format(obj):
    if isinstance(obj, list) or isinstance(obj, set):
        return [res_format(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: res_format(v) for k, v in obj.items()}
    elif isinstance(obj, decimal.Decimal):
        return int(obj) if obj % 1 == 0 else obj
    return obj


def ezget_item(tabname, key):
    global dynaresource
    response = dynaresource.Table(tabname).get_item(Key=key)

    if "Item" not in response:
        return {}

    return res_format(response["Item"])


def ezput_item(tabname, item):
    global dynaresource
    if tabname == tabname_market:
        money_exponent = max(0, len(str(max(item["money"], item["money_limit"]))) - 36)
        item["money"] = item["money"] // (10 ** money_exponent)
        item["money_limit"] = item["money_limit"] // (10 ** money_exponent)
        item["money_exponent"] = money_exponent
    dynaresource.Table(tabname).put_item(Item=item)
    tab_puts[tabname] += 1
    print(tabname, "puts:", tab_puts[tabname])


# It was an inefficient choice, to have multiple tables with integer keys
# But to change this we'd need a big migration.
# Future fork projects might prefer moving to 1 table with formatted string keys
tabname_general = os.environ["TABLES_PREFIX"] + "_general"
tabname_user = os.environ["TABLES_PREFIX"] + "_user"
tabname_market = os.environ["TABLES_PREFIX"] + "_market"
tabname_event = os.environ["TABLES_PREFIX"] + "_event"
tabname_minis = os.environ["TABLES_PREFIX"] + "_minigames_general"
tabname_miniplayers = os.environ["TABLES_PREFIX"] + "_minigames_players"


# Counters for logging
tab_puts = {i: 0 for i in [
    tabname_general,
    tabname_user,
    tabname_market,
    tabname_event,
    tabname_minis,
    tabname_miniplayers
]}
