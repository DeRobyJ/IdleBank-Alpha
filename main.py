# Handle for the AWS lambda functions
import os
import json
import traceback
import time

import urllib.request
import urllib.error
import socket

import user_interface as ui
from game_actions import get_nickname,  game_start
import uistr
from dynamodb_interface import game_set


TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


maintenance = False
instance_time = time.time()
start_time = time.time()
print(instance_time, "\n", time.gmtime(instance_time))
no_username_emojis = [
    "🐵", "🐶", "🐺", "🐱", "🦁", "🐯", "🦒", "🦊", "🦝", "🐮", "🐷", "🐗", "🐭", 
    "🐹", "🐰", "🐻", "🐨", "🐼", "🐸", "🦩", "🦚", "🦉", "🐧", "🐥", "🦋", "🐌"
]


def post_to_telegram(url, data):
    data_encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=data_encoded)

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read())

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            error_data = json.loads(error_body)
        except json.JSONDecodeError:
            error_data = {"description": error_body}

        status_code = e.code
        description = error_data.get("description", "No description")

        if status_code == 429:
            retry_after = error_data.get("parameters", {}).get("retry_after", "?")
            print(f"[429] Flood control: retry after {retry_after}s.")
            return "Flood"
        elif status_code == 400:
            print("[400] Bad Request:", description)
            return False
        elif status_code == 403:
            print("[403] Unauthorized - bot cannot message this user.")
            return False
        else:
            print(f"[{status_code}] Unexpected HTTP error:", description)
            return False

    except urllib.error.URLError as e:
        print("Network error:", e.reason)
        return False

    except socket.timeout:
        print("Request timed out.")
        return False

    except Exception as e:
        print("Unexpected error:", e)
        return False


# a list of dictionaries, each dict is a row {"string" : "querydata"}
def create_keyboard(kblist):
    inline_keyboard = []
    for row in kblist:
        inline_keyboard.append([])
        for element in row:
            inline_keyboard[-1].append({"text": element,  "callback_data": row[element]})
    return {"inline_keyboard": inline_keyboard}


def respond_with_keyboard(chat_id, text, keyboard=None, update=False, update_message_id=None,  ignore_markdown=False):
    url = TELEGRAM_API_URL + ("/editMessageText" if update else "/sendMessage")
    
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    if keyboard:
        payload["reply_markup"] = json.dumps(create_keyboard(keyboard))
    if not ignore_markdown:
        payload["parse_mode"] = "Markdown"

    if update:
        if update_message_id is None:
            raise ValueError("update_message_id must be provided when update=True")
        payload["message_id"] = update_message_id

    post_to_telegram(url, data=payload)
    return True


def acknowledge_callback(callback_query_id):
    url = TELEGRAM_API_URL + "/answerCallbackQuery"
    post_to_telegram(
        url, 
        data={
            "callback_query_id": callback_query_id, 
            #"text": "",
            #"show_alert": False
        }
    )


def delete_message(chat_id,  message_id):
    post_to_telegram(
            TELEGRAM_API_URL + "/deleteMessage",
            data={
                "chat_id": chat_id,
                "message_id": message_id
            }
        )


def get_username(update):
    if "callback_query" in update:
        return update["callback_query"]["from"].get("username")
    elif "message" in update:
        return update["message"]["from"].get("username")
    else:
        return None


def is_chat_allowed(chat_id):
    if os.environ["TABLE_NAME"] == "idlebank_alpha_testing":
        return chat_id in [int(os.environ["ADMIN_CHAT_ID"]),  int(os.environ["GROUP_TEST_CHAT_ID"])]
    else:
        return True


def manage_notifications(notifications,  is_private,  respond_id):
    if not notifications:
        print(time.time() - start_time,  "No notifications to manage")
        return
    print(time.time() - start_time, "Managing notifications")
    for notification in notifications:
        notification_keyboard = []
        if "context_keyboard" in notification:
            notification_keyboard += notification["context_keyboard"]
        notification_keyboard += [
            {uistr.get(notification["chat_id"], "button dismiss notification"):
             "Main menu",
             "✖️": "delete message"}]
        
        if is_private:
            respond_with_keyboard(
                chat_id=notification["chat_id"],
                text=notification["message"],
                keyboard=notification_keyboard
            )
        else:
            try:
                nickname = uistr.nickname(notification["chat_id"],  notification["chat_id"], get_nickname(notification["chat_id"]))
            except TypeError:
                nickname = ""
            message = nickname + "\n" + notification["message"]
            respond_with_keyboard(
                chat_id=respond_id,
                text=message,
                keyboard=notification_keyboard
            )
    print(time.time() - start_time, "Notifications managed")


def update_text(pre_text, message):
    if not pre_text:
        pre_text = "."
    if len(pre_text) == 0:
        pre_text = "."
    return pre_text + "\n" + "-" * 60 + "\n" + message


def fill_output(mes_key_not):
    if len(mes_key_not) == 1:
        return mes_key_not[0], None,  None
    if len(mes_key_not) == 2:
        return mes_key_not[0],  mes_key_not[1], None
    return mes_key_not[0],  mes_key_not[1],  mes_key_not[2]


def handle_new_group(body):
    bot_user_id = int(os.environ["BOT_CHAT_ID"])
    
    if "message" in body and "new_chat_members" in body["message"]:
        for member in body["message"]["new_chat_members"]:
            if member["id"] == bot_user_id:
                chat = body["message"]["chat"]
                print(f"✅ Bot was added to group '{chat.get('title')}' (ID: {chat['id']})")
                respond_with_keyboard(
                    chat_id=int(os.environ["ADMIN_CHAT_ID"]), 
                    text=f"Bot was added to group '{chat.get('title')}' (ID: {chat['id']})", 
                    ignore_markdown=True
                )
                return int(chat['id'])
    
    if "my_chat_member" in body:
        member_update = body["my_chat_member"]
        new_status = member_update["new_chat_member"]["status"]
        is_bot = member_update["new_chat_member"]["user"]["is_bot"]
        chat = member_update["chat"]

        if new_status == "member" and is_bot:
            print(f"✅ Bot added to group: {chat.get('title')} (ID: {chat['id']})")
            respond_with_keyboard(
                chat_id=int(os.environ["ADMIN_CHAT_ID"]), 
                text=f"Bot was added to group '{chat.get('title')}' (ID: {chat['id']})", 
                ignore_markdown=True
            )
            return int(chat['id'])
    
    return False


def bot_handler(event, context):
    print("🚨 RAW EVENT:", json.dumps(event))
    
    if event["httpMethod"] != "POST":
        print("Received a non-POST request\n",  event)
        return {"statusCode": 400}
    
    try:
        body = json.loads(event["body"])
        # Handling messages (such as "/start")
        if "message" in body:
            message = body["message"]
            query = body["message"].get("text", "")
            is_button = False
        # Handling buttons
        elif "callback_query" in body:
            message = body["callback_query"]["message"]
            query = body["callback_query"]["data"]
            acknowledge_callback(body["callback_query"]["id"])
            is_button = True
        elif "channel_post" in body:
            respond_with_keyboard(
                chat_id=body["channel_post"]["chat"]["id"], 
                text="Channels not supported"
            )
            return {'statusCode': 200}
        else:
            new_group_id = handle_new_group(body)
            if new_group_id:
                game_set(f"g_{-new_group_id}")
                game_start()
                return {'statusCode': 200}
            return {"statusCode": 200}
        chat_id = message["chat"]["id"]
        chat_type = message["chat"]["type"]
        message_id = message["message_id"]
        
        if query == "delete message":
            delete_message(chat_id,  message_id)
            return {"statusCode": 200}
        
        if maintenance or not is_chat_allowed(chat_id):
                respond_with_keyboard(
                    chat_id=chat_id, 
                    text=uistr.get(chat_id, "Maintenance message")
                )
                print(f"Trying to use the bot {chat_id}")
                return {'statusCode': 200}
          
        
        if chat_type == "private":
            is_private = True
            respond_id = chat_id
        elif chat_type in ["group",  "supergroup"]:
            is_private = False
            # Getting correct chat_id from sender, and  collecting group_id and username
            respond_id = chat_id
            if is_button:
                chat_id = body["callback_query"]["from"]["id"]
                username = body["callback_query"]["from"].get("username")
            else:
                chat_id = message["from"]["id"]
                username = message["from"].get("username")
            if not username:
                username = no_username_emojis[chat_id%len(no_username_emojis)]
        
        # Special response for feedback query
        if "feedback" in query:
            feedback_emoji = query[len("feedback "):]
            user_identification = str(chat_id)
            username = get_username(body)
            if username:
                user_identification = "@" + username
            respond_with_keyboard(
                chat_id=int(os.environ["ADMIN_CHAT_ID"]),
                text=("Feedback from " + user_identification +
                      ": " + feedback_emoji + "\n\n/start"), 
                ignore_markdown=True
            )
            query = "Main menu"
        
        # Setting game
        if is_private:
            game_set("global")
        else:
            game_set(f"g_{-respond_id}")
            if handle_new_group(body):
                game_start()
                return {'statusCode': 200}


        # happens when somebody sends media to the bot
        if len(query) == 0:
            if is_private:
                query = "/start"
            else:
                return {'statusCode': 200}
        
        # Normal input
        if is_button:
            r_message,  r_keyboard,  r_notifications = fill_output(ui.exe_and_reply(query, chat_id))
        else:
            r_message,  r_keyboard,  r_notifications = fill_output(ui.handle_message(chat_id, query))
        
        manage_notifications(r_notifications,  is_private,  respond_id)
        
        # No-keyboard "confirmation " messages
        if r_keyboard is None:
            if not r_message or len(r_message) == 0:
                return {'statusCode': 200}
            pre_text = r_message
            r_message,  r_keyboard,  r_notifications = fill_output(ui.last_menu(chat_id))
            r_message = update_text(pre_text,  r_message)
            manage_notifications(r_notifications,  is_private,  respond_id)
            
        # Normal output
        if not is_private:
            r_message = f"@{username}\n" + r_message
        result = respond_with_keyboard(respond_id,  r_message,  r_keyboard,  is_button,  message_id)
        
        if result == "Flood":
            r_message,  r_keyboard,  r_notifications = fill_output(ui.handle_message(chat_id, "/start"))
            manage_notifications(r_notifications,  is_private,  respond_id)
            pre_text = "Telegram Flood Control!"
            r_message = update_text(pre_text,  r_message)
            if not is_private:
                r_message = f"@{username}\n" + r_message
            respond_with_keyboard(respond_id, r_message, r_keyboard)
        
    except Exception:
        if is_private:
            respond_with_keyboard(
                chat_id=int(os.environ["ADMIN_CHAT_ID"]),
                text=traceback.format_exc() + "\n/fixed_" + str(respond_id), 
                ignore_markdown=True
            )
            respond_with_keyboard(
                chat_id=respond_id,
                text=("Bug!\n/start -> try again\n" +
                      "/help -> Ask for help in the public channel!")
            )
        else:
            respond_with_keyboard(
                chat_id=int(os.environ["ADMIN_CHAT_ID"]),
                text=traceback.format_exc() + "\n/fixed_g" + str(-respond_id) + "_" + str(chat_id), 
                ignore_markdown=True
            )
            respond_with_keyboard(
                chat_id=respond_id,
                text=(f"@{username} " + "Bug!\n/start -> try again\n" +
                      "/help -> Ask for help in the public channel!")
            )

    print(time.time() - start_time, "Function done")
    return {'statusCode': 200}


''' bot commands info
start - Load the main menu
gear - See gear menu (after tutorial)
help - Info and contacts
credits - About the game and contributions
'''
