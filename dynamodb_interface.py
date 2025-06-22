import os
import boto3
import decimal
import copy

tabname = os.environ["TABLE_NAME"]
dynamodb = boto3.client('dynamodb')
dynatable = boto3.resource('dynamodb', region_name='eu-south-1').Table(tabname)

game_code = "global"
game_prefix = ""

def game_set(new_game_code):
    global game_code,  game_prefix
    game_code = new_game_code
    game_prefix = f"{new_game_code}_" if new_game_code != "global" else ""
    

def game_get():
    global game_code
    return game_code


def fixpre(prefix):
    global game_prefix
    return game_prefix + prefix


def item_update(prefix, selection_dict, up_attribute, up_value_dict):
    global dynamodb, tabname
    # if "chat_id" in selection_dict:
    #    selection_dict["chat_id"]["N"] = str(selection_dict["chat_id"]["N"])
    selection_dict = copy.deepcopy(selection_dict)
    selection_dict["key"]["S"] =  fixpre(prefix) + str(selection_dict["key"]["S"])
    if "N" in up_value_dict:
        up_value_dict["N"] = str(up_value_dict["N"])
    if prefix == pre_user and up_attribute == "saved_balance":
        balance_exponent = max(0, len(up_value_dict["N"]) - 36)
        if balance_exponent > 0:
            up_value_dict["N"] = up_value_dict["N"][:-balance_exponent]
        dynamodb.update_item(
            TableName=tabname,
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
    tab_puts[prefix] += 1
    print( fixpre(prefix), "puts:", tab_puts[prefix])
# item_update('uselessbot-user_data', {'chat_id': {"N": str(chat_id)}},
#             "Aa_allowed_action", {"S": action})


def item_get(prefix, selection_dict, get_attribute, get_type):
    global dynamodb, tabname
    # if "chat_id" in selection_dict:
    #     selection_dict["chat_id"]["N"] = str(selection_dict["chat_id"]["N"])
    selection_dict = copy.deepcopy(selection_dict)
    selection_dict["key"]["S"] =  fixpre(prefix) + str(selection_dict["key"]["S"])
    res = dynamodb.get_item(TableName=tabname, Key=selection_dict)
    if "Item" in res:
        if get_attribute in res["Item"]:
            return res["Item"][get_attribute][get_type]
    return None
# item_get('uselessbot-user_data', {'chat_id': {"N": str(chat_id)}},
#          "Aa_allowed_action", "S")


# Only used to get user_data and market_data
def object_get(prefix, selection_dict):
    global dynamodb, tabname
    # if "chat_id" in selection_dict:
    #    selection_dict["chat_id"]["N"] = str(selection_dict["chat_id"]["N"])
    selection_dict_copy = copy.deepcopy(selection_dict)
    selection_dict_copy["key"]["S"] =  fixpre(prefix) + str(selection_dict_copy["key"]["S"])
    res = dynamodb.get_item(TableName=tabname, Key=selection_dict_copy)
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
        if prefix == pre_user:
            if "saved_balance" in ob:
                if "balance_exponent" not in ob:
                    balance_exponent = 0
                else:
                    balance_exponent = int(ob["balance_exponent"])
                ob["saved_balance"] = int(ob["saved_balance"] * (10**balance_exponent))
        if prefix == pre_market:
            if "money_exponent" not in ob:
                money_exponent = 0
            else:
                money_exponent = int(ob["money_exponent"])
            ob["money"] = int(ob["money"] * (10**money_exponent))
            ob["money_limit"] = int(ob["money_limit"] * (10**money_exponent))
        ob["key"] = selection_dict["key"]["S"]
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


def ezget_item(prefix, key_dict):
    global dynatable
    key_dict_copy = copy.deepcopy(key_dict)
    key_dict_copy["key"] =  fixpre(prefix) + str(key_dict_copy["key"])
    response = dynatable.get_item(Key=key_dict_copy)

    if "Item" not in response:
        return {}
    response["Item"]["key"] = key_dict["key"]
    return res_format(response["Item"])


def ezput_item(prefix, item):
    global dynatable
    item_copy = copy.deepcopy(item)
    assert prefix not in str(item_copy["key"])
    item_copy["key"] =  fixpre(prefix) + str(item_copy["key"])
    if prefix == pre_market:
        money_exponent = max(0, len(str(max(item_copy["money"], item_copy["money_limit"]))) - 36)
        item_copy["money"] = item_copy["money"] // (10 ** money_exponent)
        item_copy["money_limit"] = item_copy["money_limit"] // (10 ** money_exponent)
        item_copy["money_exponent"] = money_exponent
    dynatable.put_item(Item=item_copy)
    tab_puts[prefix] += 1
    print(fixpre(prefix), "puts:", tab_puts[prefix])


# Key prefixes
pre_board = "board_"
pre_user = "u_"
pre_market = "market_"
pre_event = "event_"
pre_minis = "minigame_"
pre_miniplayers = "p_"
pre_minimal_user = "mnm_u_"
pre_minimal_general = "mnm_board_"

# Counters for logging
tab_puts = {i: 0 for i in [
    pre_board,
    pre_user,
    pre_market,
    pre_event,
    pre_minis,
    pre_miniplayers,
    pre_minimal_user,
    pre_minimal_general
]}
