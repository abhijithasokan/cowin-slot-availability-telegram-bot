import logging

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, InlineKeyboardMarkup, InlineKeyboardButton
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


from bot_data_handler import BotDataHandler



class CowinBot:
    PIN_CODE, AGE, FETCH_CURRENT, UPDATE, AREA_SELECT_METHOD, SELECT_STATE, SELECT_DISTRICT = range(7)
    
    AGE_KEYBOARD = ReplyKeyboardMarkup( [ [ag_gp] for ag_gp in BotDataHandler.AGE_MAPPING.keys()], one_time_keyboard=True)
    AREA_TYPE_SELECT_KEYBOARD = ReplyKeyboardMarkup([['Pincode', 'District']], one_time_keyboard=True)
    # AREA_TYPE_SELECT_KEYBOARD = InlineKeyboardMarkup( [[
    #     InlineKeyboardButton("Pincode", callback_data = 'pin'),
    #     InlineKeyboardButton("District", callback_data ='dist')
    # ]])
    
    def __init__(self, bot_token, cowin_data_handler):
        self.data_handler = cowin_data_handler
        self.updater = Updater(token=bot_token, use_context=True)
        self.dispatcher = self.updater.dispatcher


    def start_listening(self):
        for handler in self._build_conv_handlers():
            self.dispatcher.add_handler(handler)       
        self.dispatcher.add_handler(MessageHandler(Filters.text, self._handler_for_help))
        self.updater.start_polling()
    

    def _build_conv_handlers(self):
        help_cmd_handler = CommandHandler('help', self._handler_for_help)
        update_cmd_handler = CommandHandler('getUpdate', self._handler_current_status)
        start_cmd_handler = CommandHandler('start', self._handler_for_start)
        conv_handler = ConversationHandler(
            entry_points=[start_cmd_handler, CommandHandler('update', self._handler_for_start)],
            states = {
                CowinBot.AREA_SELECT_METHOD: [help_cmd_handler, MessageHandler(Filters.text, self._handler_for_area_type)],
                CowinBot.PIN_CODE: [help_cmd_handler, MessageHandler(Filters.text, self._handler_update_pin_code)],
                CowinBot.AGE: [help_cmd_handler, MessageHandler(Filters.text, self._handler_update_age)],
                CowinBot.FETCH_CURRENT : [help_cmd_handler, MessageHandler(Filters.text, self._handler_current_status)],
                CowinBot.SELECT_STATE : [MessageHandler(Filters.text, self._handler_for_select_state)],
                CowinBot.SELECT_DISTRICT : [MessageHandler(Filters.text, self._handler_for_select_district)] 
            },
            fallbacks=[MessageHandler(Filters.text, self._handler_for_start)],
        )
        return help_cmd_handler, update_cmd_handler, conv_handler, start_cmd_handler

    def _handler_for_help(self, update, context):
        update.message.reply_text("Press here to start again /start \n\nPress here to /update your age/pincode")
        return ConversationHandler.END  

    def _handler_for_start(self, update, context):
        in_msg = update.message.text.strip() 
        if in_msg == '/start':
            update.message.reply_text(MESSAGES['welcome_message'])
        user = update.message.from_user
        update.message.reply_text("Choose an option to input your area " +  EMOJIS['location'], reply_markup=CowinBot.AREA_TYPE_SELECT_KEYBOARD)
        with open("user.txt", 'a') as ff:
            ff.write("\n {}, {}, {}, {}".format(user.id, user.username, user.first_name, user.last_name))
        
        return CowinBot.AREA_SELECT_METHOD

    def _handler_for_area_type(self, update, context):
        area_method = update.message.text.strip().lower()
        if area_method == "pincode":
            context.user_data['area_type'] = "pincode"
            update.message.reply_text("Enter your area pin code")
            return CowinBot.PIN_CODE
        elif area_method == "district":
            context.user_data['area_type'] = "district"
            state_names = self.data_handler.get_states_data()['state_name_to_id'].keys()
            kb = self.build_kb_layout(state_names)
            update.message.reply_text("Select your State", reply_markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True))
            return CowinBot.SELECT_STATE
        else:
            update.message.reply_text("That is not a valid way to input area. Choices are - Pincode, Area", 
                reply_markup=CowinBot.AREA_TYPE_SELECT_KEYBOARD)
            return CowinBot.AREA_SELECT_METHOD


    def build_kb_layout(self, keys, cols = 3):
        keys = sorted(keys)
        kb_layout = [ keys[ind: min(len(keys), ind + cols)] for ind in range(0, len(keys), cols) ]
        return kb_layout


    def _handler_for_select_state(self, update, context):
        state_name = update.message.text.strip()
        state_id = self.data_handler.get_states_data()['state_name_to_id'].get(state_name, None)
        if state_id is None:
            update.message.reply_text("Please select a valid state by clicking on the keyboard")
            return CowinBot.SELECT_STATE

        district_names = self.data_handler.get_states_data()['state_to_district_names'].get(state_id, None)
        if not district_names:
            update.message.reply_text("Sorry, bot encountered an unexpected error, please /start again")
            return ConversationHandler.END   
        
        kb = self.build_kb_layout(district_names)

        update.message.reply_text("Select your district", reply_markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True) )
        return CowinBot.SELECT_DISTRICT  

    def _handler_for_select_district(self, update, context):
        district_name = update.message.text.strip()
        district_id = self.data_handler.get_states_data()['district_name_to_id'].get(district_name, None)
        if district_id is None:
            update.message.reply_text("Please select a valid district by clicking on the keyboard")
            return CowinBot.SELECT_DISTRICT
        context.user_data['area_code'] = district_id
        context.user_data['area_name'] = "Dist - " + district_name
        update.message.reply_text("Select the age group which you want to receive updates for", reply_markup=CowinBot.AGE_KEYBOARD)
        return CowinBot.AGE
        
    def _handler_update_pin_code(self, update, context):
        pin_code_str = update.message.text.strip()
        print("update_pin_code", pin_code_str)
        if not pin_code_str.isdigit():
            update.message.reply_text("Please provide a valid pin_code")
            return CowinBot.PIN_CODE
        pin_code = int(pin_code_str)
        context.user_data['area_name'] = "Pincode - " + str(pin_code)
        context.user_data['area_code'] = pin_code
        update.message.reply_text("Select the age group which you want to receive updates for", 
            reply_markup=CowinBot.AGE_KEYBOARD,
        )
        return CowinBot.AGE



    def _handler_update_age(self, update, context):
        user_id = update.effective_chat.id
        age_str = update.message.text.strip()
        if not (age_str.isdigit() or age_str in ["Above 45", "Above 18", "All Age groups"]):
            update.message.reply_text("Please provide a valid age")
            return CowinBot.AGE
        age = age_str
        #self.data_handler.set_user_data(user_id, 'age', age)
        context.user_data['age'] = age
        print("update_age", age)
 
        print("DATAA --- ", context.user_data)
        user = update.message.from_user
        area_name = context.user_data['area_name']
        self.data_handler.add_user(user, context.user_data)
        update.message.reply_text("Will notify you when slots are available in your location %s, for age group %s"%(area_name, age))
        
        reply_keyboard = [['👍', 'Nope']]

        update.message.reply_text("Do you want to fetch current status?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )

        return CowinBot.FETCH_CURRENT



    def _handler_current_status(self, update, context):
        if update.message.text.strip() not in ['👍', '/getUpdate']:
            update.message.reply_text("Done")
            update.message.reply_text("Press here for /help \n\nPress here /update your age/pincode")
            return ConversationHandler.END
        
        user_id = update.effective_chat.id

        try:
            centers = self.data_handler.get_vaccine_centers_for_user(user_id)
            if centers is not None:
                if centers:
                    msg = '\n\n'.join(str(cc) for cc in centers)
                else:
                    msg = 'No centers have slots available'
            else:
                msg = "Couldn't fetch the result "
        except:
            msg = 'You have not provided Age and Area information. \n click here to /start'
            update.message.reply_text(msg)
            return ConversationHandler.END  
        

        send_message(msg, update.message.reply_text)
        
        reply_keyboard = [['👍', 'Nope']]

        update.message.reply_text("Do you want to fetch current status again?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return CowinBot.FETCH_CURRENT



from telegram import constants
def send_message(text, sender_func):
    if len(text) <= constants.MAX_MESSAGE_LENGTH:
        return sender_func(text)

    parts = []
    while len(text) > 0:
        if len(text) > constants.MAX_MESSAGE_LENGTH:
            part = text[:constants.MAX_MESSAGE_LENGTH]
            first_lnbr = part.rfind('\n')
            if first_lnbr != -1:
                parts.append(part[:first_lnbr])
                text = text[first_lnbr:]
            else:
                parts.append(part)
                text = text[constants.MAX_MESSAGE_LENGTH:]
        else:
            parts.append(text)
            break

    msg = None
    for part in parts:
        sender_func(part)
    return msg  # return only the last message

if __name__ == '__main__':
    import os
    token = os.environ.get('COWIN_TEL_BOT_KEY')

    
    if token is not None:
        data_handler = BotDataHandler()
        bot = CowinBot(token, data_handler)
        bot.start_listening()
