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
from telegram import constants

from bot_data_handler import BotDataHandler
from emojis import EMOJIS

AREA_INPUT_METHODS = ['Pincode', 'District']
MESSAGES = {
    'welcome_message' : '''Hi,\nSend me your PINCODE & AGE and I will update you when new slots for vaccination are available in your area ''' + EMOJIS['syringe'],
    'help' : 'Press here to /start again or update age/location\n\nPress here to /get_latest slot availability status ',
    'ask_age' : 'Select the age group for which you want to receive vaccine availability updates',
    'invalid_area_type' : 'That is not a valid way to input area ' + EMOJIS['sad'] + '\nChoices are - %s'%(', '.join(AREA_INPUT_METHODS)),
    'unexpected_error' : 'Sorry, bot encountered an unexpected error, please /start again',
    'no_slots' : 'Currently no vaccinations slots are available in your area ' + EMOJIS['sad'] + ' \nStay tuned for updates',
    'invalid_age_group' : "Please provide a valid age group\nChoices are - " + ', '.join(BotDataHandler.AGE_MAPPING.keys()),
}


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

DBG_LVL = ''
from datetime import datetime
def log_deco(func):
    def new_func(self, update, context, *args, **kwargs):
        if DBG_LVL == 'DBG':
            in_msg = update.message.text.strip() 
            udata = context.user_data
            user = update.message.from_user
            print("<%s>"%datetime.now().strftime("%H:%M:%S"), "@{} -- {}<{}>:  -- {}".format(func.__name__, user.first_name, user.id, in_msg, context) )
        return func(self, update, context, *args, **kwargs)
        
    return new_func




class CowinBot:
    PIN_CODE, AGE, FETCH_CURRENT, UPDATE, AREA_SELECT_METHOD, SELECT_STATE, SELECT_DISTRICT = range(7)
    
    AGE_KEYBOARD = ReplyKeyboardMarkup( [ [ag_gp] for ag_gp in BotDataHandler.AGE_MAPPING.keys()], one_time_keyboard=True)
    AREA_TYPE_SELECT_KEYBOARD = ReplyKeyboardMarkup([AREA_INPUT_METHODS], one_time_keyboard=True)
 
    
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
        update_cmd_handler = CommandHandler('get_latest', self._handler_current_status)
        start_cmd_handler = CommandHandler('start', self._handler_for_start)
        conv_handler = ConversationHandler(
            entry_points=[start_cmd_handler],
            states = {
                CowinBot.AREA_SELECT_METHOD: [help_cmd_handler, MessageHandler(Filters.text, self._handler_for_area_type)],
                CowinBot.PIN_CODE: [help_cmd_handler, MessageHandler(Filters.text, self._handler_update_pin_code)],
                CowinBot.AGE: [help_cmd_handler, MessageHandler(Filters.text, self._handler_update_age)],
                CowinBot.FETCH_CURRENT : [help_cmd_handler, MessageHandler(Filters.text, self._handler_current_status)],
                CowinBot.SELECT_STATE : [help_cmd_handler, MessageHandler(Filters.text, self._handler_for_select_state)],
                CowinBot.SELECT_DISTRICT : [help_cmd_handler, MessageHandler(Filters.text, self._handler_for_select_district)] 
            },
            fallbacks=[MessageHandler(Filters.text, self._handler_for_start)],
        )
        return help_cmd_handler, update_cmd_handler, conv_handler, start_cmd_handler

    def _handler_for_help(self, update, context):
        update.message.reply_text(MESSAGES['help'])
        return ConversationHandler.END  

    def _handler_for_start(self, update, context):
        in_msg = update.message.text.strip() 
        if in_msg == '/start' and (not context.user_data): # when its start and its new user
            update.message.reply_text(MESSAGES['welcome_message'])
        user = update.message.from_user
        update.message.reply_text("Choose an option to input your area " +  EMOJIS['location'], reply_markup=CowinBot.AREA_TYPE_SELECT_KEYBOARD)
        with open("user.txt", 'a') as ff:
            ff.write("\n {}, {}, {}, {}".format(user.id, user.username, user.first_name, user.last_name))
        
        return CowinBot.AREA_SELECT_METHOD

    @log_deco
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
            update.message.reply_text(MESSAGES['invalid_area_type'], reply_markup=CowinBot.AREA_TYPE_SELECT_KEYBOARD)
            return CowinBot.AREA_SELECT_METHOD

    def build_kb_layout(self, keys, cols = 3):
        keys = sorted(keys)
        kb_layout = [ keys[ind: min(len(keys), ind + cols)] for ind in range(0, len(keys), cols) ]
        return kb_layout

    @log_deco
    def _handler_for_select_state(self, update, context):
        state_name = update.message.text.strip()
        state_id = self.data_handler.get_states_data()['state_name_to_id'].get(state_name, None)
        if state_id is None:
            update.message.reply_text("Please select a valid state by clicking on the keyboard")
            return CowinBot.SELECT_STATE

        district_names = self.data_handler.get_states_data()['state_to_district_names'].get(state_id, None)
        if not district_names:
            update.message.reply_text(MESSAGES['unexpected_error'])
            return ConversationHandler.END   
        
        kb = self.build_kb_layout(district_names)
        update.message.reply_text("Select your district", reply_markup = ReplyKeyboardMarkup(kb, one_time_keyboard=True) )
        return CowinBot.SELECT_DISTRICT  
    @log_deco
    def _handler_for_select_district(self, update, context):
        district_name = update.message.text.strip()
        district_id = self.data_handler.get_states_data()['district_name_to_id'].get(district_name, None)
        if district_id is None:
            update.message.reply_text("Please select a valid district by clicking on the keyboard")
            return CowinBot.SELECT_DISTRICT
        context.user_data['area_code'] = district_id
        context.user_data['area_name'] = "Dist - " + district_name
        update.message.reply_text(MESSAGES['ask_age'], reply_markup=CowinBot.AGE_KEYBOARD)
        return CowinBot.AGE
    
    @log_deco
    def _handler_update_pin_code(self, update, context):
        pin_code_str = update.message.text.strip()
        print("update_pin_code", pin_code_str)
        if not pin_code_str.isdigit():
            update.message.reply_text("Please provide a valid pin_code")
            return CowinBot.PIN_CODE
        pin_code = int(pin_code_str)
        context.user_data['area_name'] = "Pincode - " + str(pin_code)
        context.user_data['area_code'] = pin_code
        update.message.reply_text(MESSAGES['ask_age'], reply_markup=CowinBot.AGE_KEYBOARD)
        return CowinBot.AGE


    @log_deco
    def _handler_update_age(self, update, context):  
        user_id = update.effective_chat.id
        age_str = update.message.text.strip()
        if age_str not in BotDataHandler.AGE_MAPPING:
            update.message.reply_text(MESSAGES['invalid_age_group'])
            return CowinBot.AGE
        age = age_str
        #self.data_handler.set_user_data(user_id, 'age', age)
        context.user_data['age'] = age
        print("update_age", age)
 
        print("DATAA --- ", context.user_data)
        user = update.message.from_user
        area_name = context.user_data['area_name']
        self.data_handler.add_user(user, context.user_data)
        age_msg_str = self.data_handler.get_age_str(age_str)
        update.message.reply_text("Will notify you when slots are available in your location %s, for %s age group %s"%(area_name, age_msg_str, EMOJIS['thumbs_up']))
        
        reply_keyboard = [[EMOJIS['thumbs_up'], 'Nope']]

        update.message.reply_text("Do you want to fetch current status?",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )

        return CowinBot.FETCH_CURRENT


    @log_deco
    def _handler_current_status(self, update, context):
        if update.message.text.strip() not in [EMOJIS['thumbs_up'], '/get_latest']:
            update.message.reply_text("Done " + EMOJIS['thumbs_up'] +'\n\n' + MESSAGES['help'])
            return ConversationHandler.END
        
        user_id = update.effective_chat.id

        try:
            centers = self.data_handler.get_vaccine_centers_for_user(user_id)
            if centers is not None:
                if centers:
                    chunks = self.data_handler.get_chunked_msg_text(centers, constants.MAX_MESSAGE_LENGTH)
                    for chunk_msg in chunks:
                        update.message.reply_text(chunk_msg)
                    return ConversationHandler.END  
                    #msg = '\n\n'.join(str(cc) for cc in centers)
                else:
                    msg = MESSAGES['no_slots']
            else:
                msg = "Couldn't fetch the result "
        except Exception as ee:
            print("Exception here - ", ee) 
            #msg = 'You have not provided locality and age information. \n click here to /start'
            #update.message.reply_text(msg)
            return ConversationHandler.END  
        

        update.message.reply_text(msg)
        return ConversationHandler.END  

        # reply_keyboard = [['👍', 'Nope']]

        # update.message.reply_text("Do you want to fetch current status again?",
        #     reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        # )
        # return CowinBot.FETCH_CURRENT




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
    import sys
    token = os.environ.get('COWIN_TEL_BOT_KEY')
    if '--dbg' in sys.argv:
        print("RUNNING IN DBG MODE")
        DBG_LVL = 'DBG'
    
    if token is not None:
        data_handler = BotDataHandler()
        bot = CowinBot(token, data_handler)
        bot.start_listening()
