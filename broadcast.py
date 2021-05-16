from bot_data_handler import BotDataHandler
from datetime import datetime
import os

from telegram import Bot, constants

MESSAGES = {
    'stop_resume_updates' : 'Click here to /stop_receiving_updates\nYou can later /resume_updates',
    'view_complete' : 'To view *complete list* press /get_latest',
    'view_updated' : 'To view *complete & updated list* press /get_latest',
}


def log_msg(msg):
    print("<%s>  %s"%(datetime.now().strftime("%H:%M %d-%m"), msg))

class BroadCaster:
    def __init__(self):
        token = os.environ.get('COWIN_TEL_BOT_KEY')
        if token is None:
            raise Exception("Bot token not available, can't proceed")
        self.data_handler = BotDataHandler()
        self.bot = Bot(token)

        self.dist_code_to_name = self.data_handler.get_dist_code_to_name_from_disk()

    def get_slot_count(self, centers):
        return sum( sum(ss.available_capacity_ for ss in center.sessions_) for center in centers )

    def summarize(self, slot_count, num_centers, age, area_code, is_pincode):
        msg  = 'There %s ' %('are' if slot_count != 1 else 'is' ) 
        msg += str(slot_count) if slot_count else 'no'
        msg += ' slots ' if slot_count != 1 else ' slot ' 
        msg += 'available across %d %s '%(num_centers, 'centres' if slot_count !=1 else 'centre') if slot_count else ''
        msg += 'in '
        msg += '[pin] %s'%(area_code) if is_pincode else self.dist_code_to_name.get(area_code, '[district] %s'%area_code)
        msg += ' for {} age group'.format(self.data_handler.get_age_str2(age))
        return msg

    def get_few_from_top(self, centers, limit):
        centers = sorted(centers, key = lambda ct: -sum(ss.available_capacity_ for ss in ct.sessions_) )
        return centers[:min(limit, len(centers))]


    def build_msg_in_chunks(self, summary_msg, centers):
        MAX_CENTERS_IN_MSG = 5
        can_send_all_data_now = (len(centers) <= MAX_CENTERS_IN_MSG)

        items  = [summary_msg + '\n\n']
        items += ["Here are few of them\n\n"]  if (not can_send_all_data_now) else [] 
        items += centers if can_send_all_data_now else self.get_few_from_top(centers, MAX_CENTERS_IN_MSG)
        items += ["\n\n"]
        items += [MESSAGES['view_complete']] if (not can_send_all_data_now) else [MESSAGES['view_updated']]
        items += ['\n\n' + MESSAGES['stop_resume_updates']]

        return self.data_handler.get_chunked_msg_text(items, constants.MAX_MESSAGE_LENGTH)


    def push_updates(self):
        dist_to_age_to_user_ids, pincode_to_age_to_user_ids = self.data_handler.segregate_user_groups()
        num_queries = len(dist_to_age_to_user_ids) + len(pincode_to_age_to_user_ids)
        users_who_got_broadcast = []
        for area_to_agewise_users, is_pincode in [(dist_to_age_to_user_ids, False), (pincode_to_age_to_user_ids, True)]:
            print("----")
            for area_code, age_wise_users in area_to_agewise_users.items():
                age_groups = age_wise_users.keys()
                data_gen = self.data_handler.get_filtered_data_for_location(age_groups, area_code, is_pincode, slot_threshold = 1)
                print("Handle - %s" % area_code)
                for age_gp, centers in data_gen:
                    slot_count = self.get_slot_count(centers)
                    if not slot_count:
                        continue
                    log_msg("area - {}, slot - {}, age - {}".format(area_code, slot_count, age_gp))
                    # add check for slot count here .. 
                    summary_msg = self.summarize(slot_count, len(centers), age_gp, area_code, is_pincode)
                    
                    msg_chunks = self.build_msg_in_chunks(summary_msg, centers)
                    for user_id in age_wise_users[age_gp]:
                        try:
                            for chunk in msg_chunks:
                                self.bot.send_message(user_id, chunk)
                            users_who_got_broadcast.append(user_id)
                        except Exception as ee:
                            log_msg("Failed for user {} reason {}".format(user_id, str(ee)))

        self.data_handler.update_broadcast_count_for_users(users_who_got_broadcast)

if __name__ == '__main__':  
    brd = BroadCaster()
    brd.push_updates()