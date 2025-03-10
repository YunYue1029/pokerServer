import random
import json

class Card_Method:
    def __init__(self):
        self.card_status = [1]*52
        self.player_status = [0]*6
        self.player_money = [0]*6
        self.player_card = [""]*2
        self.pot = 0
        self.three_card = 1
        self.fourth_card = 1
        self.fifth_card = 1

    def select_card(self):
        while True:
            random_number = random.randint(1, 52)
            if self.card_status[random_number - 1] == 1:
                self.card_status[random_number - 1] = 0
                return random_number
    
    def get_card(self,card_id):
        card_data = self.load_card_data()
        return card_data[card_id - 1]["card"]
    def load_card_data(self, card_info='poker.json'):
        try:
            with open(card_info, 'r') as file:
                card_data = json.load(file)
                return card_data
        except FileNotFoundError:
            print("Card data no found !")
            return []
        except json.JSONDecodeError:
            print("Error decoding JSON! Initializing with empty data.")
            return []

    def card_check(self, server_card, player_card):
        card = [0] * 7
        card_data = self.load_card_data()

        card[:5] = server_card[:5]
        card[5:7] = player_card

        flower_count = {"spade": 0, "Hearts": 0, "diamond": 0, "club": 0}
        number_count = [0] * 13
        Straight = []

        # 創建卡牌信息
        card_info = [
            {"card_id": "", "card_color": "", "card_num": ""}
            for _ in range(7)
        ]

        for i in range(7):
            for t in range(52):
                if card[i] == card_data[t]["card"]:
                    card_info[i]["card_num"] = card_data[t]["number"]
                    card_info[i]["card_color"] = card_data[t]["color"]
                    card_info[i]["card_id"] = card_data[t]["card_ID"]

        for i in range(7):
            color = card_info[i]["card_color"]
            num = card_info[i]["card_num"]
            if color in flower_count:
                flower_count[color] += 1
            if num == "A":
                Straight.append(14)
                number_count[0] += 1
            elif num.isdigit():
                Straight.append(int(num))
                number_count[int(num) - 1] += 1
            elif num == "J":
                Straight.append(11)
                number_count[10] += 1
            elif num == "Q":
                Straight.append(12)
                number_count[11] += 1
            elif num == "K":
                Straight.append(13)
                number_count[12] += 1

        is_flush = any(count >= 5 for count in flower_count.values())
        Straight.sort()
        is_straight = any(
            Straight[i + 1] - Straight[i] == 1 and
            Straight[i + 2] - Straight[i + 1] == 1 and
            Straight[i + 3] - Straight[i + 2] == 1 and
            Straight[i + 4] - Straight[i + 3] == 1
            for i in range(len(Straight) - 4)
        )
        is_four = 4 in number_count
        is_three = 3 in number_count
        is_pair = number_count.count(2)

        if is_flush and is_straight:
            return "FS"
        if is_four:
            return "F"
        if is_three and is_pair:
            return "H"
        if is_flush:
            return "FL"
        if is_straight:
            return "S"
        if is_three:
            return "3"
        if is_pair == 2:
            return "2P"
        if is_pair == 1:
            return "P"
        return "0"
    
    def winner(self, rank):
        rank_priority = {
            'FS': 8,  # 皇家同花順
            'F': 7,   # 四條
            'H': 6,   # 葫蘆
            'FL': 5,  # 同花
            'S': 4,   # 順子
            '3': 3,   # 三條
            '2P': 2,  # 兩對
            'P': 1,   # 一對
            '0': 0 ,  # 無牌
            '-1':-1   # 棄牌
        }
        max_priority = -1
        winner_id = -1
        for i in range(len(rank)):
            current_priority = rank_priority.get(rank[i], -1)
            if current_priority > max_priority:
                max_priority = current_priority
                winner_id = i

        return winner_id

    def crad_translate(self,card_num):
        if card_num == 'A':
            return 14
        elif card_num == '2':
            return 2
        elif card_num == '3':
            return 3
        elif card_num == '4':
            return 4
        elif card_num == '5':
            return 5
        elif card_num == '6':
            return 6
        elif card_num == '7':
            return 7
        elif card_num == '8':
            return 8
        elif card_num == '9':
            return 9
        elif card_num == '10':
            return 10
        elif card_num == 'J':
            return 11
        elif card_num == 'Q':
            return 12   
        elif card_num == 'K':
            return 13
        return 0         

    def reset(self):
        self.card_status = [1]*52
        self.player_status = [0]*6
        self.chips = 0
        self.three_card = 1
        self.fourth_card = 1
        self.fifth_card = 1

    def clear_card(self):
        self.card_status = [1]*52

    def clear_player_cards(self, players):
        for player in players:
            player["player_card"] = []

