# Handle for the AWS lambda functions
# The telegram bot logic is kinda spaghetti, but I'm Italian so I have a license to do it

# No ok kidding this needs cleaning
# 																						Like Italian politics

# Ok let's say this: the day the Italian Parliament and Government will be free of
# fascists and people with mafia allegations, I'll clean this code.
# Otherwise, Spaghetti Cacio e Pepe it is
import os
import telegram
import json
import user_interface as ui
import uistr
import traceback
import time


maintenance = False
instance_time = time.time()
start_time = time.time()
print(instance_time, "\n", time.gmtime(instance_time))


def is_player_allowed(chat_id):
    if os.environ["TABLES_PREFIX"] == "IdleBank_testing":
        return chat_id in [int(os.environ["ADMIN_CHAT_ID"])]
    else:
        return True


# a list of dictionaries, each dict is a row {"string" : "querydata"}
def create_keyboard(kblist):
    keyboard = []
    for row in kblist:
        keyboard.append([])
        for element in row:
            keyboard[-1].append(telegram.InlineKeyboardButton(element,
                                callback_data=row[element]))
    return telegram.InlineKeyboardMarkup(keyboard)


def manage_notifications(bot, mesKeyNot):
    print(time.time() - start_time, "Managing notifications")
    if len(mesKeyNot) < 3:
        return
    # print(mesKeyNot[2])
    for notification in mesKeyNot[2]:
        # print(time.time() - start_time)
        notification_keyboard = []
        if "context_keyboard" in notification:
            notification_keyboard += notification["context_keyboard"]
        notification_keyboard += [
            {uistr.get(notification["chat_id"], "button dismiss notification"):
             "Main menu",
             "✖️": "delete message"}]
        try:
            bot.sendMessage(
                chat_id=notification["chat_id"],
                text=notification["message"],
                reply_markup=create_keyboard(notification_keyboard),
                parse_mode='markdown')
        except telegram.error.Unauthorized:
            pass
    print(time.time() - start_time, "Notifications managed")


def update_text(pre_text, mesKeyNot):
    if not pre_text:
        pre_text = "."
    if len(pre_text) == 0:
        pre_text = "."
    if len(mesKeyNot) < 3:
        return (pre_text + mesKeyNot[0], mesKeyNot[1])
    return (pre_text + mesKeyNot[0], mesKeyNot[1], mesKeyNot[2])


def bot_handler(event, context):
    # print(event)
    if event["httpMethod"] == "POST":
        bot = telegram.Bot(token=os.environ["TELEGRAM_TOKEN"])
        try:
            update = telegram.Update.de_json(json.loads(event["body"]), bot)
            if update.callback_query:
                query = update.callback_query
                if not hasattr(query.message, "chat"):
                    print("no attr chat")
                    return {'statusCode': 200}
                if query.message.chat.type != "private":
                    return {'statusCode': 200}
                chat_id = query.from_user.id
                # See https://core.telegram.org/bots/api#callbackquery
                try:
                    query.answer()
                except telegram.error.BadRequest:
                    return {'statusCode': 200}

                if maintenance or not is_player_allowed(chat_id):
                    query.edit_message_text(text=uistr.get(
                        chat_id, "Maintenance message"))
                    return {'statusCode': 200}

                if query.data == "delete message":
                    try:
                        bot.deleteMessage(chat_id, query.message.message_id)
                    except telegram.error.BadRequest:
                        pass
                    return {'statusCode': 200}
                if "feedback" in query.data:
                    feedback_emoji = query.data[len("feedback "):]
                    user_identification = str(chat_id)
                    if query.from_user.username:
                        user_identification = "@" + query.from_user.username
                    bot.sendMessage(
                        chat_id=int(os.environ["ADMIN_CHAT_ID"]),
                        text=("Feedback from " + user_identification +
                              ": " + feedback_emoji + "\n\n/start")
                    )
                    mesKeyNot = ui.exe_and_reply("Main menu", chat_id)
                else:
                    mesKeyNot = ui.exe_and_reply(query.data, chat_id)
                manage_notifications(bot, mesKeyNot)
                if mesKeyNot[1] is None:
                    pre_text = mesKeyNot[0]
                    if pre_text:
                        mesKeyNot = ui.last_menu(chat_id)
                        manage_notifications(bot, mesKeyNot)
                        if type(pre_text) is not str:
                            mesKeyNot = update_text(
                                "." + "\n" + "-" * 60 + "\n", mesKeyNot)
                            print(pre_text)
                            bot.sendMessage(
                                chat_id=int(os.environ["ADMIN_CHAT_ID"]),
                                text="strange pre_text: " + str(pre_text))
                        else:
                            mesKeyNot = update_text(
                                pre_text + "\n" + "-" * 60 + "\n", mesKeyNot)
                if mesKeyNot[1] is not None:
                    try:
                        query.edit_message_text(
                            text=mesKeyNot[0],
                            reply_markup=create_keyboard(mesKeyNot[1]),
                            parse_mode='markdown')
                    except telegram.error.TimedOut:
                        bot.sendMessage(chat_id=chat_id, text=uistr.get(
                            chat_id, "timeout"))
                        bot.sendMessage(chat_id=int(
                            os.environ["ADMIN_CHAT_ID"]),
                            text="Timeout from /view@" + str(chat_id)
                        )
                        return {'statusCode': 200}
                    except telegram.error.BadRequest:
                        return {'statusCode': 200}
                    return {'statusCode': 200}

            elif update.message:
                if not hasattr(update.message, "chat"):
                    return {'statusCode': 200}
                if update.message.chat.type != "private":
                    return {'statusCode': 200}
                chat_id = update.message.chat.id
                if maintenance or not is_player_allowed(chat_id):
                    bot.sendMessage(chat_id=chat_id, text=uistr.get(
                        chat_id, "Maintenance message"))
                    return {'statusCode': 200}
                if update.message.text:
                    mesKeyNot = ui.handle_message(chat_id, update.message.text)
                    manage_notifications(bot, mesKeyNot)
                else:
                    try:
                        bot.forwardMessage(
                            chat_id=int(os.environ["ADMIN_CHAT_ID"]),
                            from_chat_id=chat_id,
                            message_id=update.message.message_id
                        )
                    except telegram.error.BadRequest:
                        bot.sendMessage(chat_id=int(
                            os.environ["ADMIN_CHAT_ID"]),
                            text="Media forwarding fail\n\n" +
                            traceback.format_exc()
                        )
                    mesKeyNot = ui.handle_message(chat_id, "/start")
                    manage_notifications(bot, mesKeyNot)
            else:
                return {'statusCode': 200}

            if mesKeyNot[1] is None:
                if mesKeyNot[0] is None:
                    return {'statusCode': 200}
                if len(mesKeyNot[0]) == 0:
                    return {'statusCode': 200}
                bot.sendMessage(chat_id=chat_id,
                                text=mesKeyNot[0], parse_mode='markdown')
                mesKeyNot = ui.exe_and_reply("Main menu", chat_id)
                manage_notifications(bot, mesKeyNot)
            bot.sendMessage(
                chat_id=chat_id,
                text=mesKeyNot[0],
                reply_markup=create_keyboard(mesKeyNot[1]),
                parse_mode='markdown')
        except telegram.error.RetryAfter:
            mesKeyNot = ui.handle_message(chat_id, "/start")
            manage_notifications(bot, mesKeyNot)
            bot.sendMessage(
                chat_id=chat_id,
                text=("Telegram Flood Control!\n" +
                      "-" * 60 + "\n" + mesKeyNot[0]),
                parse_mode='markdown')
        except Exception:
            bot.sendMessage(chat_id=int(
                os.environ["ADMIN_CHAT_ID"]),
                text=traceback.format_exc() + "\n/fixed_" + str(chat_id)
            )
            bot.sendMessage(
                chat_id=chat_id,
                text=("Bug!\n/start -> try again\n" +
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
