import logging

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)


EMOJIS = {
    'location' : str(u'\U0001F4CD'),
    'syringe' : str(u'\U0001F489')
}


MESSAGES = {
    'welcome_message' : '''Hi,\nSend me your PINCODE & AGE and I will update you when new slots for vaccination are available in your area ''' + EMOJIS['syringe'],
}


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)



from collections import defaultdict
from datetime import datetime

from fetch_cowin_data import CowinDataConnector
from parse_data import CowinCenter


class BotDataHandler:
    def __init__(self):
        self.data_conn = CowinDataConnector()
        self.user_info = defaultdict(dict)

    def set_user_data(self, user_id, key, val):
        self.user_info[user_id][key] = val

    def get_user_data(self, user_id, *keys):
        res = []
        udata = self.user_info[user_id]
        for key in keys:
            res.append(udata[key])
        return res

    def get_vaccine_centers_for_user(self, user_id):
        pin_code,  = self.get_user_data(user_id, 'pin_code')
        api_data = self.data_conn.fetch_data(pin_code, datetime.now())
        if api_data:
            centers = list(CowinCenter.build_from_json(api_data.get("centers", [])))
        else:
            centers = None
        return centers




class CowinBot:
    PIN_CODE, AGE, FETCH_CURRENT, UPDATE = 0, 1, 2, 3
    def __init__(self, bot_token, cowin_data_handler):
        self.data_handler = cowin_data_handler
        self.updater = Updater(token=bot_token, use_context=True)
        self.dispatcher = self.updater.dispatcher


    def start_listening(self):
        self.dispatcher.add_handler(self._build_conv_handler())
        self.updater.start_polling()
    

    def _build_conv_handler(self):
        help_cmd_handler = CommandHandler('help', self._handler_for_help)
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self._handler_for_start), CommandHandler('update', self._handler_for_update), help_cmd_handler],
            states = {
                CowinBot.PIN_CODE: [help_cmd_handler, MessageHandler(Filters.text, self._handler_update_pin_code)],
                CowinBot.AGE: [help_cmd_handler, MessageHandler(Filters.text, self._handler_update_age)],
                CowinBot.FETCH_CURRENT : [help_cmd_handler, MessageHandler(Filters.text, self._handler_current_status)],
                #CowinBot.UPDATE : [CommandHandler('update', self._handler_for_update)],
                # AGE: [MessageHandler(Filters.photo, photo), CommandHandler('skip', skip_photo)],
                # BIO: [MessageHandler(Filters.text & ~Filters.command, bio)],
            },
            fallbacks=[CommandHandler('start', self._handler_for_start)],
        )
        return conv_handler

    def _handler_for_help(self, update, context):
        update.message.reply_text("Press here to start again /start \n\nPress here /update your age/pincode")
        return ConversationHandler.END  

    def _handler_for_start(self, update, context):
        update.message.reply_text(MESSAGES['welcome_message'])
        user = update.message.from_user
        update.message.reply_text("Send your PIN CODE " +  EMOJIS['location'])
        self.data_handler.set_user_data(user.id, 'username', user.username)
        with open("user.txt", 'a') as ff:
            ff.write("\n {}, {}, {}, {}".format(user.id, user.username, user.first_name, user.last_name))
        
        return CowinBot.PIN_CODE

    def _handler_for_update(self, update, context):
        update.message.reply_text("Send your PIN CODE " + EMOJIS['location'])
        return CowinBot.PIN_CODE

    def _handler_update_pin_code(self, update, context):
        pin_code_str = update.message.text.strip()
        print("update_pin_code", pin_code_str)
        if not pin_code_str.isdigit():
            update.message.reply_text("Please provide a valid pin_code")
            return CowinBot.PIN_CODE
        pin_code = int(pin_code_str)
        user_id = update.effective_chat.id
        self.data_handler.set_user_data(user_id, 'pin_code', pin_code)
        update.message.reply_text("What is your age?", 
            reply_markup=ReplyKeyboardMarkup([ ["Above 60", "Above 40"], ["Above 18"], ["Below 18"] ] , one_time_keyboard=True),
        )
        return CowinBot.AGE



    def _handler_update_age(self, update, context):
        user_id = update.effective_chat.id
        age_str = update.message.text.strip()
        if not (age_str.isdigit() or age_str in ["Above 60", "Above 40", "Above 18", "Below 18"]):
            update.message.reply_text("Please provide a valid age")
            return CowinBot.AGE
        age = age_str
        self.data_handler.set_user_data(user_id, 'age', age)
        print("update_age", age)
        pin_code, age = self.data_handler.get_user_data(user_id, 'pin_code', 'age') 
        update.message.reply_text("Will notify you when slots are available in your location %d for age group %s"%(pin_code, age))
        
        reply_keyboard = [['👍', 'Nope']]

        update.message.reply_text("Do you want to fetch current status?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )

        return CowinBot.FETCH_CURRENT



    def _handler_current_status(self, update, context):
        if update.message.text.strip() != '👍':
            update.message.reply_text("Done")
            update.message.reply_text("Press here for /help \n\nPress here /update your age/pincode")
            return ConversationHandler.END
        
        user_id = update.effective_chat.id

        centers = self.data_handler.get_vaccine_centers_for_user(user_id)
        if centers is not None:
            if centers:
                msg = '\n\n'.join(str(cc) for cc in centers)
            else:
                msg = 'No centers have slots available'
        else:
            msg = "Couldn't fetch the result "

        update.message.reply_text(msg)
        
        reply_keyboard = [['👍', 'Nope']]

        update.message.reply_text("Do you want to fetch current status again?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return CowinBot.FETCH_CURRENT






if __name__ == '__main__':
    import os
    token = os.environ.get('COWIN_TEL_BOT_KEY')
    if token is not None:
        data_handler = BotDataHandler()
        bot = CowinBot(token, data_handler)
        bot.start_listening()
    