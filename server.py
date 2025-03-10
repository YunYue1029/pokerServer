import socket
import threading
import json
import time
import card

class ServerConnect:
    def __init__(self):
        # server setting
        self.port = 8888
        self.host = '0.0.0.0'
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}
        # player setting
        self.clear_player_info()
        self.reset_user_status()
        self.user_data = self.load_user_data()
        self.players_information = self.load_player_info()
        # player id status
        self.id_status = [0]*6
        self.players_status = [-1]*6
        self.players_money = [0]*6
        self.player_in_game = 0
        # game status
        self.game_round = 0
        self.play_round = 1
        self.current_turn = 1
        self.turn_lock = threading.Condition()
        self.game_start_now = 0

        self.card = card.Card_Method()
        self.server_card = ["","","","",""]
        self.rank = ['0']*6
        self.player_left = 0
        #  money
        self.call_money = 0
        self.all_in_now = 0
        self.all_in_money = 0
        self.raise_now = 0
        self.raise_money = 20


    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(6)
        print(f"Server started, listening on {self.host}:{self.port}...")
        threading.Thread(target=self.accept_clients, daemon=True).start()

    def accept_clients(self):
        while True:
            try:
                client_socket, client_address = self.server_socket.accept()
                self.clients[client_socket] = client_address
                print(f"Connected by {client_address}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
            except Exception as e:
                print(f"Error accepting clients: {e}")
                break

    def handle_client(self, client_socket):
        try:
            while True:
                data = self.receive_data(client_socket)
                print(data)
                status = data.get('status')
                username = data.get('username')
                password = data.get('password')
                if status == "login":
                    if self.login(username, password):
                        
                        client_id = None
                        for i in range(6):
                            if self.id_status[i] == 0:
                                client_id = i+1
                                self.id_status[i] = 1
                                break

                        client_socket.send(json.dumps({"status": "login_success","id":client_id}).encode('utf-8'))
                        players = {
                            "player_id": client_id,
                            "name": username,
                            "player_card_1": "",
                            "player_card_2": ""
                        }
                        
                        self.players_status[client_id-1] = 1
                        self.players_money[client_id-1] = 200
                        self.players_information.append(players)
                        self.save_player_info()
                        self.run(client_socket,client_id,username)
                        break
                    else:
                        client_socket.send(json.dumps({"status": "login_fail", "message": "Invalid username or password."}).encode('utf-8'))
                elif status == "register":
                    if self.register(username, password):
                        client_socket.send(json.dumps({"status": "register_success"}).encode('utf-8'))
                    else:
                        client_socket.send(json.dumps({"status": "register_fail", "message": "Username already exists."}).encode('utf-8'))
                if status == "disconnect":
                    break
        except Exception as e:
            print("Error handling client:", e)
        except ConnectionError:
            print(f"Client {self.clients.get(client_socket, 'Unknown')} disconnected unexpectedly.")
        finally:
            if client_id:
                self.cleanup_player(client_id)
            client_socket.close()
    # game run
    def run(self,client_socket,client_id,username):
        try:
            while self.game_start_now == 1:
                time.sleep(0.1)
                client_socket.send(json.dumps({"status": "waiting_new_game"}).encode('utf-8'))
                continue
            while True:
                # setting new game
                self.initialize_game()
                time.sleep(2.0)
                for i in range(6):
                    if self.id_status[i] == 1:
                        if self.players_money[i] == 0:
                            self.players_status[i] = 0
                        else:
                            self.players_status[i] = 1
                
                if self.players_status[client_id -1] == 0:
                    self.stop()
                    break
                # waiting for player to join
                while True:
                    self.player_in_game = self.get_now_player()
                    if self.player_in_game >= 2:
                        client_socket.send(json.dumps({"status": "game_start","player_status":self.players_status,"player_money":self.players_money}).encode('utf-8'))
                        self.player_left = self.player_in_game
                        break
                    else:
                        client_socket.send(json.dumps({"status": "wait_for_player"}).encode('utf-8'))
                    time.sleep(1.0)
                print("Game Start !")
                self.game_start_now = 1
                time.sleep(1.0)
                self.players_money[client_id - 1] -= 20
                self.card.pot += 20
                #start play the game
                with self.turn_lock:
                    while True:
                        print(self.current_turn)
                        print(self.game_round)
                        print(self.rank)
                        print(self.players_status)
                        print(self.players_money)
                        print(self.play_round)

                        while client_id != self.current_turn:
                            print(f"wait:{client_id}")
                            time.sleep(0.1)
                            self.send_data(client_socket,{"status": "wait","game":self.game_round,"player":self.current_turn,"player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot})
                            self.turn_lock.wait(timeout = 2.0)
                            if client_id != self.current_turn:
                                continue
                        
                        if self.player_left == 1:
                            while True:
                                self.play_round += 1
                                self.current_turn = (self.current_turn % 6 +1)
                                if self.id_status[self.current_turn-1] == 1:
                                    break
                            self.turn_lock.notify_all()
                            break
                        
                        if self.game_round == 0:
                            print("round_0")
                            card_1 = self.card.select_card()
                            card_2 = self.card.select_card()
                            poker_1 = self.card.get_card(card_1)
                            poker_2 = self.card.get_card(card_2)
                            for player in self.players_information:
                                if player["player_id"] == client_id:
                                    player["player_card_1"] = poker_1
                                    player["player_card_2"] = poker_2
                            self.save_player_info()
                            client_socket.send(json.dumps({"status": "round_0", "card_1": poker_1, "card_2": poker_2,"player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                            self.play_round += 1
                        elif self.game_round == 1:
                            print("round_1")
                            client_socket.send(json.dumps({"status": "round_1","player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                            time.sleep(0.1)
                            while True:
                                if self.players_status[self.current_turn - 1] == 3:
                                    break
                                elif self.players_status[self.current_turn - 1] == 0:
                                    break
                                data = self.receive_data(client_socket)
                                status = data.get('status')
                                print(status)
                                if status == "call":
                                    print(f"{self.current_turn} : call")
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.players_status[self.current_turn-1] = 1
                                    if self.all_in_now == 1:
                                        if self.players_money[self.current_turn - 1] < self.all_in_money:
                                            self.players_status[self.current_turn - 1] = 3
                                            self.card.pot += self.players_money[self.current_turn - 1]
                                            self.player_money[self.current_turn - 1] = 0
                                        else:
                                            self.players_status[self.current_turn - 1] = 3
                                            self.players_money[self.current_turn-1] -= self.all_in_money
                                            self.card.pot += self.all_in_money
                                    elif self.raise_now == 1:
                                        if self.players_money[self.current_turn - 1] < self.call_money:
                                            client_socket.send(json.dumps({"status": "round_1","player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                                            continue
                                        else:
                                            self.players_money[self.current_turn-1] -= self.call_money
                                            self.card.pot += self.call_money
                                    break
                                elif status == "raise":
                                    print(f"{self.current_turn} : raise")
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.players_status[self.current_turn-1] = 2
                                    if self.players_money[self.current_turn - 1] < self.raise_money:
                                        client_socket.send(json.dumps({"status": "round_1","player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                                        continue
                                    else:
                                        self.players_money[self.current_turn-1] -= self.raise_money
                                    self.card.pot += self.raise_money
                                    self.call_money = self.raise_money
                                    self.raise_money += 20
                                    self.raise_now = 1
                                    self.play_round = 1
                                    break
                                elif status == "all_in":
                                    print(f"{self.current_turn} : all in")
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.players_status[self.current_turn-1] = 3
                                    self.all_in_money = self.players_money[self.current_turn-1]
                                    self.card.pot += self.players_money[self.current_turn-1]
                                    self.players_money[self.current_turn-1] = 0
                                    self.all_in_now = 1
                                    self.play_round = 1
                                    break
                                elif status == "fold":
                                    print(f"{self.current_turn} : fold")
                                    self.players_status[self.current_turn-1] = -1
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.player_left -= 1
                                    self.rank[self.current_turn-1] = -1
                                    break
                                else:
                                    client_socket.send(json.dumps({"status": "round_1","player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                                    time.sleep(0.1)
                            self.play_round += 1
                        elif self.game_round == 2:
                            print("round_2")
                            if self.card.three_card == 1:
                                for i in range(3):
                                    card = self.card.select_card()
                                    self.server_card[i] = self.card.get_card(card)
                                self.card.three_card = 0
                            client_socket.send(json.dumps({"status": "round_2","server_card_1":self.server_card[0],"server_card_2":self.server_card[1],"server_card_3":self.server_card[2],"player_status":self.players_status,"player_money":self.players_money}).encode('utf-8'))
                            time.sleep(0.1)
                            self.play_round += 1
                        elif self.game_round == 3:
                            print("round_3")
                            client_socket.send(json.dumps({"status": "round_3", "card_1": poker_1, "card_2": poker_2,"player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                            time.sleep(0.1)
                            while True:
                                if self.players_status[self.current_turn - 1] == 3:
                                    break
                                elif self.players_status[self.current_turn - 1] == 0:
                                    break
                                data = self.receive_data(client_socket)
                                status = data.get('status')
                                print(status)
                                if status == "call":
                                    print(f"{self.current_turn} : call")
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.players_status[self.current_turn-1] = 1
                                    if self.all_in_now == 1:
                                        if self.players_money[self.current_turn - 1] < self.all_in_money:
                                            self.players_status[self.current_turn - 1] = 3
                                            self.card.pot += self.players_money[self.current_turn - 1]
                                            self.player_money[self.current_turn - 1] = 0
                                        else:
                                            self.players_status[self.current_turn - 1] = 3
                                            self.players_money[self.current_turn-1] -= self.all_in_money
                                            self.card.pot += self.all_in_money
                                    elif self.raise_now == 1:
                                        if self.players_money[self.current_turn - 1] < self.call_money:
                                            client_socket.send(json.dumps({"status": "round_3","player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                                            continue
                                        else:
                                            self.players_money[self.current_turn-1] -= self.call_money
                                            self.card.pot += self.call_money
                                    break
                                elif status == "raise":
                                    print(f"{self.current_turn} : raise")
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.players_status[self.current_turn-1] = 2
                                    if self.players_money[self.current_turn - 1] < self.raise_money:
                                        client_socket.send(json.dumps({"status": "round_5","player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                                        continue
                                    else:
                                        self.players_money[self.current_turn-1] -= self.raise_money
                                    self.card.pot += self.raise_money
                                    self.call_money +=self.raise_money
                                    self.raise_money += 20
                                    self.raise_now = 1
                                    self.play_round = 1
                                    break
                                elif status == "all_in":
                                    print(f"{self.current_turn} : all in")
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.players_status[self.current_turn-1] = 3
                                    self.all_in_money = self.players_money[self.current_turn-1]
                                    self.card.pot += self.players_money[self.current_turn-1]
                                    self.players_money[self.current_turn-1] = 0
                                    self.all_in_now = 1
                                    self.play_round = 1
                                    break
                                elif status == "fold":
                                    print(f"{self.current_turn} : fold")
                                    self.players_status[self.current_turn-1] = -1
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.player_left -= 1
                                    self.rank[self.current_turn-1] = -1
                                    break
                                else:
                                    client_socket.send(json.dumps({"status": "round_3","player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                            self.play_round += 1
                        elif self.game_round == 4:
                            print("round_4")
                            if self.card.fourth_card == 1:
                                card = self.card.select_card()
                                self.server_card[3] = self.card.get_card(card)
                                self.card.fourth_card = 0
                            client_socket.send(json.dumps({"status": "round_4","server_card_4":self.server_card[3],"player_status":self.players_status,"player_money":self.players_money}).encode('utf-8'))
                            time.sleep(0.1)
                            self.play_round += 1
                        elif self.game_round == 5:
                            print("round_5")
                            client_socket.send(json.dumps({"status": "round_5","player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                            time.sleep(0.1)
                            while True:
                                if self.players_status[self.current_turn - 1] == 3:
                                    break
                                elif self.players_status[self.current_turn - 1] == 0:
                                    break
                                data = self.receive_data(client_socket)
                                status = data.get('status')
                                print(status)
                                if status == "call":
                                    print(f"{self.current_turn} : call")
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.players_status[self.current_turn-1] = 1
                                    if self.all_in_now == 1:
                                        if self.players_money[self.current_turn - 1] < self.all_in_money:
                                            self.players_status[self.current_turn - 1] = 3
                                            self.card.pot += self.players_money[self.current_turn - 1]
                                            self.player_money[self.current_turn - 1] = 0
                                        else:
                                            self.players_status[self.current_turn - 1] = 3
                                            self.players_money[self.current_turn-1] -= self.all_in_money
                                            self.card.pot += self.all_in_money
                                    elif self.raise_now == 1:
                                        if self.players_money[self.current_turn - 1] < self.call_money:
                                            client_socket.send(json.dumps({"status": "round_5","player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                                            continue
                                        else:
                                            self.players_money[self.current_turn-1] -= self.call_money
                                            self.card.pot += self.call_money
                                    break
                                elif status == "raise":
                                    print(f"{self.current_turn} : raise")
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.players_status[self.current_turn-1] = 2
                                    if self.players_money[self.current_turn - 1] < self.raise_money:
                                        client_socket.send(json.dumps({"status": "round_5","player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                                        continue
                                    else:
                                        self.players_money[self.current_turn-1] -= self.raise_money
                                    self.card.pot += self.raise_money
                                    self.call_money = self.raise_money
                                    self.raise_money += 20
                                    self.raise_now = 1
                                    self.play_round = 1
                                    break
                                elif status == "all_in":
                                    print(f"{self.current_turn} : all in")
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.players_status[self.current_turn-1] = 3
                                    self.all_in_money = self.players_money[self.current_turn-1]
                                    self.card.pot += self.players_money[self.current_turn-1]
                                    self.players_money[self.current_turn-1] = 0
                                    self.all_in_now = 1
                                    self.play_round = 1
                                    break
                                elif status == "fold":
                                    print(f"{self.current_turn} : fold")
                                    self.players_status[self.current_turn-1] = -1
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.player_left -= 1
                                    self.rank[self.current_turn-1] = -1
                                    break
                                else:
                                    client_socket.send(json.dumps({"status": "round_5","player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                            self.play_round += 1
                        elif self.game_round == 6:
                            print("round_6")
                            if self.card.fifth_card == 1:
                                card = self.card.select_card()
                                self.server_card[4] = self.card.get_card(card)
                                self.card.fifth_card = 0
                            client_socket.send(json.dumps({"status": "round_6","server_card_5":self.server_card[4],"player_status":self.players_status,"player_money":self.players_money}).encode('utf-8'))
                            time.sleep(0.1)
                            self.play_round += 1
                        elif self.game_round == 7:
                            print("round_7")
                            client_socket.send(json.dumps({"status": "round_7","player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                            time.sleep(0.1)
                            while True:
                                if self.players_status[self.current_turn - 1] == 3:
                                    break
                                elif self.players_status[self.current_turn - 1] == 0:
                                    break
                                data = self.receive_data(client_socket)
                                status = data.get('status')
                                print(status)
                                if status == "call":
                                    print(f"{self.current_turn} : call")
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.players_status[self.current_turn-1] = 1
                                    if self.all_in_now == 1:
                                        if self.players_money[self.current_turn - 1] < self.all_in_money:
                                            self.players_status[self.current_turn - 1] = 3
                                            self.card.pot += self.players_money[self.current_turn - 1]
                                            self.player_money[self.current_turn - 1] = 0
                                        else:
                                            self.players_status[self.current_turn - 1] = 3
                                            self.players_money[self.current_turn-1] -= self.all_in_money
                                            self.card.pot += self.all_in_money
                                    elif self.raise_now == 1:
                                        if self.players_money[self.current_turn - 1] < self.call_money:
                                            client_socket.send(json.dumps({"status": "round_7","player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                                            continue
                                        else:
                                            self.players_money[self.current_turn-1] -= self.call_money
                                            self.card.pot += self.call_money
                                    break
                                elif status == "raise":
                                    print(f"{self.current_turn} : raise")
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.players_status[self.current_turn-1] = 2
                                    if self.players_money[self.current_turn - 1] < self.raise_money:
                                        client_socket.send(json.dumps({"status": "round_5","player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                                        continue
                                    else:
                                        self.players_money[self.current_turn-1] -= self.raise_money
                                    self.card.pot += self.raise_money
                                    self.call_money = self.raise_money
                                    self.raise_money += 20
                                    self.raise_now = 1
                                    self.play_round = 1
                                    break
                                elif status == "all_in":
                                    print(f"{self.current_turn} : all in")
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.players_status[self.current_turn-1] = 3
                                    self.all_in_money = self.players_money[self.current_turn-1]
                                    self.card.pot += self.players_money[self.current_turn-1]
                                    self.players_money[self.current_turn-1] = 0
                                    self.all_in_now = 1
                                    self.play_round = 1
                                    break
                                elif status == "fold":
                                    print(f"{self.current_turn} : fold")
                                    self.players_status[self.current_turn-1] = -1
                                    client_socket.send(json.dumps({"status": "OK"}).encode('utf-8'))
                                    self.player_left -= 1
                                    self.rank[self.current_turn-1] = -1
                                    break
                                else:
                                    client_socket.send(json.dumps({"status": "round_7","player_status":self.players_status,"player_money":self.players_money,"pot": self.card.pot}).encode('utf-8'))
                            self.play_round += 1
                        elif self.game_round == 8:
                            print("round_8")
                            if self.rank[self.current_turn-1] != -1:
                                for player in self.players_information:
                                    if player["player_id"] == self.current_turn:
                                        self.card.player_card[0] = player["player_card_1"]
                                        self.card.player_card[1] = player["player_card_2"]
                                        break
                                ans = self.card.card_check(self.server_card,self.card.player_card)
                                self.rank[self.current_turn-1] = ans
                                client_socket.send(json.dumps({"status": "round_8","hand_rank": ans,"player_status":self.players_status,"player_money":self.players_money}).encode('utf-8'))
                                time.sleep(0.1)
                            self.play_round += 1
                            while True:
                                self.current_turn = (self.current_turn % 6 +1)
                                if self.id_status[self.current_turn-1] == 1:
                                    break
                            self.turn_lock.notify_all()
                            break
                        print("==============")
                        print(self.play_round)
                        print(self.player_in_game)
                        print("==============")
                        if self.play_round == self.player_in_game +1:
                            print("next game round")
                            self.raise_now = 0
                            self.play_round = 1
                            self.game_round += 1
                            self.current_turn = 1
                            self.turn_lock.notify_all()
                            continue
                        while True:
                            self.current_turn = (self.current_turn % 6 +1)
                            if self.id_status[self.current_turn-1] == 1:
                                break
                        time.sleep(0.5)
                        self.turn_lock.notify_all()
                        
                time.sleep(1.0)
                print(f"rank :{self.rank}")
                print(f"player_status: {self.card.player_status}")
                print(f"player_money: {self.players_money}")
                winner_id = self.card.winner(self.rank)+1
                if self.player_left == 1:
                    for i in range(6):
                        if self.players_status[i] != -1:
                            winner_id = i + 1
                            break
                print(f"winner : {winner_id}")
                client_socket.send(json.dumps({"status":"check_winner","winner":winner_id}).encode('utf-8'))
                self.players_money[winner_id-1] += self.card.pot
                self.card.pot = 0
                self.game_start_now = 0
                time.sleep(2.0)
                # new game
                print("game over")
        except Exception as e:
            print("Error running client 541:", e)
            self.players_money[client_id] = 0
            self.players_status[client_id] = -1
            self.logout(username)
        finally:
            with self.turn_lock:
                self.players_money[client_id] = 0
                self.players_status[client_id] = -1
                self.logout(username)
                self.cleanup_player(client_id)
                self.turn_lock.notify_all()
            
    def send_data(self, client_socket, data):
        try:
            json_data = json.dumps(data)+"\n"
            client_socket.send(json_data.encode('utf-8'))
        except ConnectionError:
            print("send_data error !")
            client_socket.close()
            
    # logout
    def logout(self,username):
        users = self.load_user_data()
        for user in users:
            if user['name'] == username:
                user['status'] = 0
                try:
                    with open('user.json', 'w') as file:
                        json.dump(users, file, indent=4)
                except Exception as e:
                    print("Error saving user data:", e)
    # login
    def login(self, username, password):
        users = self.load_user_data()
        for user in users:
            if user['name'] == username and user['password'] == password:
                if user['status'] == 1:
                    return False
                else:
                    user['status'] = 1
                    try:
                        with open('user.json', 'w') as file:
                            json.dump(users, file, indent=4)
                    except Exception as e:
                        print("Error saving user data:", e)
                        return False
                return True
        return False
    # register
    def register(self, username, password):
        users = self.load_user_data()
        for user in users:
            if user['name'] == username:
                return False
        users.append({'name': username, 'password': password, 'status':0})
        try:
            with open('user.json', 'w') as file:
                json.dump(users, file, indent=4)
            return True
        except Exception as e:
            print("Error saving user data:", e)
            return False
    # get receive data
    def receive_data(self, client_socket):
        try:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                return None
            return json.loads(data)
        except (json.JSONDecodeError, ConnectionError):
            print("receive_data error !")
            return None
    # nonblock
    def receive_latest_data(self,client_socket):
        client_socket.setblocking(False)  # 設置非阻塞模式
        data = None
        try:
            while True:
                latest_data = client_socket.recv(1024).decode('utf-8')
                if latest_data:
                    data = latest_data  # 更新為最新封包
        except BlockingIOError:
            pass
        finally:
            if data:
                return json.loads(data)  # 返回最新的 JSON 資料
            return None
    # loading user data
    def load_user_data(self, user_info='user.json'):
        try:
            with open(user_info, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            return []
    # reset status
    def reset_user_status(self):
        users = self.load_user_data()
        for user in users:
            user['status'] = 0
        try:
            with open('user.json', 'w') as file:
                json.dump(users, file, indent=4)
            print("All user statuses have been reset to 0.")
        except Exception as e:
            print(f"Error resetting user statuses: {e}")
    def clear_player_info(self):
        try:
            with open('players_information.json', 'w') as file:
                file.write('')
            print("player_info.json has been cleared.")
        except Exception as e:
            print(f"Error clearing player.json: {e}")
    # load player information
    def load_player_info(self, player_info='players_information.json'):
        try:
            with open(player_info, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            return []
    # save player info
    def save_player_info(self, player_info='players_information.json'):
        try:
            with open(player_info, 'w') as file:
                json.dump(self.players_information, file, indent=4)
            print(f"Player information saved to {player_info}")
        except Exception as e:
            print(f"Error saving player information: {e}")
    # reset game
    def initialize_game(self):
        self.game_round = 0
        self.play_round = 1
        self.current_turn = 1
        self.game_start_now = 0
        self.card.pot = 0
        self.card.reset()
        self.rank = [0]*6
        for player in self.players_information:
                player["player_card_1"] = ""
                player["player_card_2"] = ""
        self.all_in_now = 0
        self.all_in_money = 0
        self.raise_now = 0
        self.raise_money = 20

    def get_now_player(self):
        count = 0
        for i in range(6):
            if self.players_status[i] >= 1:
                count += 1
        return count
    # remove the player
    def cleanup_player(self, client_id):
        try:
            player_to_remove = next((player for player in self.players_information if player["player_id"] == client_id), None)
            if player_to_remove:
                self.players_information.remove(player_to_remove)
                print(f"Player {client_id} has been removed.")
            self.id_status[client_id - 1] = 0
            self.save_player_info()
        except Exception as e:
            print(f"Error cleaning up player {client_id}: {e}")
    # stop the server
    def stop(self):
        print("Stopping server...")
        for client_socket in self.clients.keys():
            try:
                client_socket.send(json.dumps({"status": "server_stop", "message": "Server is shutting down."}).encode('utf-8'))
                client_socket.close()
            except:
                pass
        self.server_socket.close()

if __name__ == "__main__":
    server = ServerConnect()
    try:
        server.start()
        while True:
            command = input()
            if command.lower() == "stop":
                server.stop()
                break
    except KeyboardInterrupt:
        server.stop()