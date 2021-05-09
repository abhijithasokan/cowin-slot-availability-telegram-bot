from bot_data_handler import BotDataHandler
from datetime import time
import os

from telegram import Bot, constants

class BroadCaster:
    def __init__(self):
        token = os.environ.get('COWIN_TEL_BOT_KEY')
        if token is None:
            raise Exception("Bot token not available, can't proceed")
        self.data_handler = BotDataHandler()
        self.bot = Bot(token)

        self.dist_code_to_name = self.data_handler.get_dist_code_to_name()

    def get_slot_count(self, centers):
        return sum( len(center.sessions_) for center in centers )

    def summarize(self, slot_count, num_centers, age, area_code, is_pincode):
        msg  = 'There are ' 
        msg += str(slot_count) if slot_count else 'no'
        msg += ' slots '
        msg += 'available across %d centers '%(num_centers) if slot_count else ''
        msg += 'in '
        msg += '[Pin] %d'%(area_code) if is_pincode else self.dist_code_to_name.get(area_code, '[District] %d'%area_code)
        msg += ' for age group ' + self.data_handler.get_rev_age_mapping(age)
        return msg

    def get_few_from_top(self, centers, limit):
        centers = sorted(centers, key = lambda ct: -sum(ss.available_capacity_ for ss in ct.sessions_) )
        return centers[:min(limit, len(centers))]

    def push_updates(self):
        dist_to_age_to_user_ids, pincode_to_age_to_user_ids = self.data_handler.segregate_user_groups()
        num_queries = len(dist_to_age_to_user_ids) + len(pincode_to_age_to_user_ids)

        for area_to_agewise_users, is_pincode in [(dist_to_age_to_user_ids, False), (pincode_to_age_to_user_ids, True)]:
            print("----")
            for area_code, age_wise_users in area_to_agewise_users.items():
                age_groups = age_wise_users.keys()
                data_gen = self.data_handler.get_filtered_data_for_location(age_groups, area_code, is_pincode, slot_threshold = 1)
                print("Handle - %d" % area_code)
                if data_gen is None:
                    print("Query failed for dist code - ", area_code)
                for age_gp, centers in data_gen:
                    slot_count = self.get_slot_count(centers)
                    if not slot_count:
                        continue
                    # add check for slot count here .. 
                    msg = self.summarize(slot_count, len(centers), age_gp, area_code, is_pincode)
                    items = [msg, "\n\nHere are few of them\n\n"] + self.get_few_from_top(centers, 5) +  ["\n\nClick here to get full current status /get_latest"]
                    chunks = self.data_handler.get_chunked_msg_text(items, constants.MAX_MESSAGE_LENGTH)
                    for user_id in age_wise_users[age_gp]:
                        for chunk in chunks:
                            self.bot.send_message(user_id, chunk)


if __name__ == '__main__':  
    brd = BroadCaster()
    brd.push_updates()