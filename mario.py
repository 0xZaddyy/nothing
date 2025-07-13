from flask import Flask, jsonify, send_from_directory
from dataclasses import dataclass, field
from websocket_server import WebsocketServer
import dolphin_memory_engine as dme
import requests
import threading
import json
import logging
import queue
import time
import os
import grpc
import codecs
from urllib.parse import urlencode
import lightning_pb2 as lnrpc
import lightning_pb2_grpc as lightningrpc

def get_dolphin():
    dme.hook()

    if dme.is_hooked():
        print("Connected to Dolphin!")
    else: 
        print("Waiting for Dolphin...")
        while not dme.is_hooked():
            dme.hook()
            if dme.is_hooked():
                print("Connected to Dolphin!")
            time.sleep(1)

get_dolphin()

courses = {
  # Mushroom Cup
  (0, 0): ["Luigi Circuit", ["🏁", "🚦"]],
  (0, 1): ["Peach Beach", ["🏖️", "🌴"]],
  (0, 2): ["Baby Park", ["🍼", "🎡"], 7],
  (0, 3): ["Dry Dry Desert", ["🏜️", "🌵"]],
  # Flower Cup
  (1, 0): ["Mushroom Bridge", ["🌉", "🍄"]],
  (1, 1): ["Mario Circuit", ["🍄", "⭐"]], # alt emojis: 🏎️, 🧱
  (1, 2): ["Daisy Cruiser", ["🛳️", "🌼"]],
  (1, 3): ["Waluigi Stadium", ["🏟️", "🚧"]], # alt emojis: 💣,💥
  # Star Cup
  (2, 0): ["Sherbet Land", ["❄️", "🐧"]], # alt emojis: 🧊
  (2, 1): ["Mushroom City", ["🌃", "🍄"]], # alt emojis: 🚧
  (2, 2): ["Yoshi Circuit", ["🥚", "🛣️"]], # alt emojis: 💚, 🏎️, ☁️
  (2, 3): ["DK Mountain", ["🌋", "🍌"]],
  # Special Cup 
  (3, 0): ["Wario Colosseum", ["🏛️", "🎢"], 2], # alt emojis: 🎪
  (3, 1): ["Dino Dino Jungle", ["🦕", "🌴"]],
  (3, 2): ["Bowser's Castle", ["🏰", "🔥"]],
  (3, 3): ["Rainbow Road", ["🌈", "⭐"]],
  # Award Ceremony
  (4, 0): ["Award Ceremony", ["🏆", "🎊"], 0]
}

cups = [
  "Mushroom Cup",
  "Flower Cup",
  "Star Cup",
  "Special Cup",
  "All Cup Tour"
]

@dataclass
class Player:
    name: str
    custom_name: str | None = None
    lap: int = 0
    position: int | None = None
    active: bool = True  # are they playing this round?
    locked: bool = False # do we want to make it so that they can't register for this player slot?
    has_items_a: bool = False
    has_items_b: bool = False
    struck_by_lightning: bool = False
    hit_cooldown: int = 0
    # lightning stuff
    sats_earned: int = 0 # per course
    unpaid_sats: int = 0 # sats that didn't go through due to rate limiting, timeouts, invalid address, etc
    total_sats_earned: int = 0
    lightning_address: str | None = None
    callback: str | None = None
    is_valid: bool = True
    # memory addresses
    lap_memory: int | None = None
    position_memory: int | None = None
    has_items_a_memory: int | None = None
    has_items_b_memory: int | None = None
    damage_timer_memory: int | None = None
    lightning_timer_memory: int | None = None

@dataclass
class Game:
    funding_source: str = os.getenv("FUNDING_SOURCE", "lnd").lower()
    offline: bool = False
    payments: bool = True
    started: bool = False # after it's true, don't allow for new registrations
    # bitcoin payout amounts
    stream_amount: int = 1
    lap_amount: int = 10
    course_amount: int = 100
    # game variables
    current_cup: str | None = None
    current_course: str | None = None
    current_course_emoji: str | None = None
    current_course_emoji_bonus: str | None = None
    current_course_laps: int = 3
    num_players: int | None = None
    game_mode: str | None = None # Grand Prix or Vs. mode
    game_mode_players: int | None = None # another way of reading the players in Grand Prix mode
    game_state: str | None = None
    game_state_prev: str | None = None
    gp_wait_time: int = 34 # how long to wait for grand prix games before starting payments
    vs_wait_time: int = 0  # how long to wait for vs. before starting payments
    course_over: bool = False 
    course_timer: int = 0
    players: list[Player] = field(default_factory=list) 
    # memory addresses
    course_state_memory: int = 0x803B0727 # when it's 1 you're on the title screen
    is_paused_memory: int = 0x803B0723 # 1 when paused, 0 when playing
    is_playing_memory: int = 0x810AC12C # 1 when playing, 0 when paused, 255 or 248 on title screen
    # cup and course memory addresses
    cup_memory: int = 0x803CB7AB
    course_memory: int = 0x803B0FCB
    game_mode_memory: int = 0x803B128B # will be 0 for vs, 1 for 1 player gp and 2 for 2 player gp!
   
player1 = Player(
    name="Player 1",
    lap_memory=0x8037FF62,
    position_memory=0x8037FFA3,
    damage_timer_memory=0x8037FF40, # half word
    lightning_timer_memory=0x8037FFC2, # half word
    # item_a_memory=0x80400018,
    # item_b_memory=0x8040001C,
    # lightning_address="dk@primal.net" # may want to rate limit primal addresses?
    # lightning_address="therealaustin@primal.net",
    # lightning_address="dksf@strike.me",
    # lightning_address="arata@walletofsatoshi.com",
    # lightning_address="testing3833939@walletofsatoshi.com",
    # lightning_address="dplusplus@zbd.gg",
    lightning_address="dplusplus@walletofsatoshi.com",
    # lightning_address="roisin@strike.me",
    # active=False
)
player2 = Player(
    name="Player 2",
    lap_memory=0x8037FF66,
    position_memory=0x8037FFA7,
    damage_timer_memory=0x8037FF44, # half word
    lightning_timer_memory=0x8037FFC6, # half word
    # lightning_address="alligator61@coinos.io", # leo
    # lightning_address="zap@dplus.plus", # maps to WoS
    # lightning_address="imelonmusk@strike.me",
    # lightning_address="dplusplus@coinos.io",
    lightning_address="dplusplus@zbd.gg",
    # active=False
)
player3 = Player(
    name="Player 3",
    lap_memory=0x8037FF6A,
    position_memory=0x8037FFAB,
    damage_timer_memory=0x8037FF48, # half word
    # lightning_address="dplusplus@walletofsatoshi.com",
    # lightning_address="nouser3408934@strike.me",
    # lightning_address="dplusplus@strike.me",
    # active=False
)
player4 = Player(
    name="Player 4",
    lap_memory=0x8037FF6E,
    position_memory=0x8037FFAF,
    damage_timer_memory=0x8037FF4C, # half word
    # lightning_address="nouser3438943@coinos.io",
    # lightning_address="dplusplus@strike.me",
    # lightning_address="dplusplus@walletofsatoshi.com",
    # active=False
)

game = Game()
game.players.append(player1)
game.players.append(player2)
game.players.append(player3)
game.players.append(player4)

# start LND stuff ##########################################################
if game.funding_source == "lnd":
    grpc_host = os.getenv("GRPC_HOST_URL")
    tls_path = 'tls.cert'
    admin_macaroon = codecs.encode(bytes.fromhex(os.getenv("ADMIN_MACAROON")), 'hex')

    def metadata_callback(context, callback):
        callback([('macaroon', admin_macaroon)], None)

    auth_creds = grpc.metadata_call_credentials(metadata_callback)

    def lnd_connect():
        global client
        auth_creds = grpc.metadata_call_credentials(metadata_callback)
        os.environ['GRPC_SSL_CIPHER_SUITES'] = 'HIGH+ECDSA'
        cert = None
        if tls_path and os.path.exists(tls_path):
            with open(tls_path, 'rb') as file:
                cert = file.read()
        ssl_creds = grpc.ssl_channel_credentials(cert)
        combined_creds = grpc.composite_channel_credentials(ssl_creds, auth_creds)
        channel = grpc.secure_channel(grpc_host, combined_creds)
        client = lightningrpc.LightningStub(channel)

    lnd_connect()
# end LND stuff ############################################################

# start phoenixd stuff #####################################################
if game.funding_source == "phoenixd":
    def pay_player_phoenixd(player, amount, message):
        address = player.lightning_address
        try:
            data = {
            'address': address,
            'amountSat': amount,
            'message': message
            }

            headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
            }

            auth = (os.getenv('PHOENIXD_HTTP_USER'), os.getenv('PHOENIXD_HTTP_PASSWORD'))

            try:
                response = requests.post(
                f"{os.getenv('PHOENIXD_HOST_URL')}/paylnaddress",
                    data=urlencode(data),
                    headers=headers,
                    auth=auth
                )
                response.raise_for_status()
                result = response.json()

            except Exception as error:
                # to do: add up a total of unpaid sats so that we can pay them when they finish the course
                player.unpaid_sats = player.unpaid_sats + amount
                send_message(f"Could not pay {player.name} {amount} sats:<br>{error}")
                return False
            
            player.sats_earned += amount

            print(f'Phoenixd payment result: {result}')

            preimage = f"{result['paymentPreimage'][:13]}..{result['paymentPreimage'][-14:]}"
            amount = result['recipientAmountSat']
            fee = result['routingFeeSat']
            send_message(
            f"Payment successful for {player.name}!<br>"

            # f"Payment Amount: <span class='b'>B</span><font style='font-size:2.5px'> </font>{amount} | "
            # f"Fee: <span class='b'>B</span><font style='font-size:2.5px'> </font>{fee}<br>"


            f"Payment Amount: <span class='b' style='margin-right:3px'>B</span>{amount} | "
            f"Fee: <span class='b' style='margin-right:3px'>B</span>{fee}<br>"

            f"Preimage: {preimage}", False)

            return True

# Invoice created: {'recipientAmountSat': 1, 'routingFeeSat': 4, 'paymentId': '2cd3496b-3dda-4fff-af42-677b9164d716', 'paymentHash': 'f740553555b3f55accef371dc3f9d899d7435cbedf4a849661371d2fca4c51c1', 'paymentPreimage': '92c946e4ed03fd60a20e58ae66f5866ee74f25274ce31f92d0a5b575096d013a'}
            # return response.json()

        except requests.exceptions.RequestException as error:
            player.unpaid_sats = player.unpaid_sats + amount
            if error.response:
                print(error.response.text)
                return error.response.text
            else:
                print(str(error))
                return str(error)
# end phoenixd stuff #######################################################

# start websockets stuff ###################################################
ws_server = WebsocketServer(host='127.0.0.1', port=8765)
message_queue = queue.Queue()
connected = threading.Event()

def on_new_client(client, server):
  print("WebSocket connected:", client['id'])
  connected.set()

def on_message_received(client, server, message):
  print(f"Received from client {client['id']}: {message}")
  message = json.loads(message)
  print("the message in json is:")
  print(message)
  address = message.get("address")
  custom_name = message.get("name")
  name = message.get("number")
  type = message.get("type")
  if type == "register":
      insert_player(address, name, custom_name)
      
ws_server.set_fn_new_client(on_new_client)
ws_server.set_fn_message_received(on_message_received)

threading.Thread(target=ws_server.run_forever, daemon=True).start()

def process_ws_queue():
  while True:
    msg = message_queue.get()
    try:
      ws_server.send_message_to_all(msg)
    except Exception as error:
      print("WebSocket send error:", error)

threading.Thread(target=process_ws_queue, daemon=True).start()
# end websockets stuff #####################################################

# start flask stuff ########################################################
app = Flask(__name__, static_folder="static", static_url_path="")
logging.getLogger('werkzeug').setLevel(logging.ERROR)

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

@app.route("/api/state")
def get_state():
    return jsonify(game)

def run_flask():
    app.run(debug=False)

threading.Thread(target=run_flask, daemon=True).start()
# end flask stuff ###########################################################

def get_callback(player):
    if game.offline:
        return

    if player.lightning_address == None:
        # print(f"{player.name} has not specified a Lightning Address.")
        return
        
    if player.lightning_address == "" or "@" not in player.lightning_address:
        send_message(f"Lightning address for {player.name} is invalid.")
        return
    
    user, domain = player.lightning_address.split("@", 1)

    try:
        response = requests.get(f"https://{domain}/.well-known/lnurlp/{user}")
        player.callback = response.json().get("callback")

        if not player.callback:
            reason = response.json().get("reason")          
            message = f"{player.name}: There was an error getting the callback for {player.lightning_address}"
            if reason:
                message += f": {reason}"
            send_message(message)
            player.is_valid = False
            return
        else:
            player.is_valid = True
    
    except Exception as error:
        error = "User not found." if "Expecting value: line 1 column 1 (char 0)" in str(error) else error
        send_message(f"There was an error with {player.name}'s Lightning Address {player.lightning_address}: {error}")    
        return
    
def send_message(message, print_message=True):
    message_queue.put(message)
    if print_message:
        print(message)

def pay_player(player, amount, comment):
    if not game.payments:
        return
    
    if not player.lightning_address:
        send_message(f"{player.name} has not specified a Lightning Address and thus cannot get paid.")
        player.unpaid_sats = player.unpaid_sats + amount
        return

    total_amount = amount + player.unpaid_sats
    player.unpaid_sats = 0

    if game.funding_source == "lnd":
        pay_player_lnd(player, total_amount, comment)
    if game.funding_source == "phoenixd":
        pay_player_phoenixd(player, total_amount, comment)

def pay_player_lnd(player, amount, comment):
    player.sats_earned += amount
    amount_msat = amount * 1000 # convert to millisats - danger! be careful here!!!

    print(comment)

    try:
        # todo: check if it's a json string and if so, parse it to json
        sep = '&' if '?' in player.callback else '?'
        response = requests.get(f"{player.callback}{sep}amount={amount_msat}&comment={comment}")
        invoice = response.json().get("pr")

        if not invoice:
            send_message("There was an issue retrieving the invoice.")
            player.unpaid_sats = player.unpaid_sats + amount
            return
        
        short_invoice = f"{invoice[:19]}..{invoice[-18:]}"
        send_message(f"Fetched <font style='font-size:2px'> </font><span class='b'>B</span><font style='font-size:2.5px'> </font>{amount} invoice for {player.name}:<br>{short_invoice}")

    except Exception as error:
        send_message(f"There was an issue retrieving the invoice: {error}")
        player.unpaid_sats = player.unpaid_sats + amount
        return
  
    try:
        request = lnrpc.SendRequest(payment_request=invoice)
        data = client.SendPaymentSync(request)

        print(data)
        
        error = data.payment_error
        if error:
            player.unpaid_sats = player.unpaid_sats + amount
            send_message(f"There was an error paying {player.name}: {error}")
            return
        
        s = '' if amount < 2 else 's'
        preimage = data.payment_preimage.hex()
        short_preimage = f"{preimage[:19]}..{preimage[-18:]}"
        total_fees_msat = data.payment_route.total_fees_msat
        num_hops = len(data.payment_route.hops)

        send_message(f"Payment successful for {player.name}!<br>{short_preimage}<br>Amount: <font style='font-size:5px'></font><span class='b'>B</span><font style='font-size:2.5px'> </font>{amount} | Fee: <font style='font-size:2px'> </font><span class='b'>B</span><font style='font-size:2.5px'> </font>{total_fees_msat/1000} | Hops: {num_hops}", False)
        
    except Exception as error:
        player.unpaid_sats = player.unpaid_sats + amount
        send_message(f"There was an error paying the invoice: {error}")

def read_course():
    mode = read_byte(game.game_mode_memory)
    game.game_mode_players = mode

    if mode == 0:
        game.game_mode = "Vs."
    else:
        game.game_mode = "Grand Prix"

    if game.game_state == "title screen":
        game.current_course = "Title Screen"
        return
    
    cup = read_byte(game.cup_memory)
    course = read_byte(game.course_memory)
    if course == None:
        return
    
    game.current_cup = cups[cup]
    
    if cup == 4: # All Cup Tour!
        # for now, don't pay out on laps since we don't know which course we're on for the All Cup Tour
        # this could be fixed by changing the settings in Double Dash to make all courses the same number of laps...
        course_list = list(courses.values())

        if course == 0 or course == 15 or course == 16: # we know the first and last courses will be luigi circuit and rainbow road
            game.current_course = course_list[course][0]        
            game.current_course_emoji = course_list[course][1][0]
            game.current_course_emoji = course_list[course][1][1]
            if course == 16:
                game.current_course_laps = course_list[course][2] # award ceremony
        else: 
            game.current_course = f"Course {course + 1}/16 of the All Cup Tour" 
            game.current_course_emoji = "🏎️"
            game.current_course_emoji_bonus = "🏆" 
    else:
        if course == 4: # award ceremony
            # add some logic here to send a single payment to them if they won first place in the gp
            # would need a flag to know if the payment has been sent
            current_course = courses[(4, 0)] # hard coded for award ceremony
        else:
            current_course = courses[(cup, course)]

        game.current_course = current_course[0]
        game.current_course_emoji = current_course[1][0]
        game.current_course_emoji_bonus = current_course[1][1]
        game.current_course_laps = current_course[2] if len(current_course) > 2 else 3

def read_byte(address): # read a single byte
    try:
        result = int.from_bytes(dme.read_bytes(address, 1), "big")
    except Exception as error:
        print(f"Error reading byte: {error}. Please restart Dolphin.")
        result = None
    return result

def read_bytes(address): # read half-word (2 bytes)
    try:
        result = int.from_bytes(dme.read_bytes(address, 2), "big")
    except Exception as error:
        print(f"Error reading bytes: {error}. Please restart Dolphin.")
        result = None
    return result

def read_game_state():
    # paused  playing  course_state  result
    # ------------------------------------------------------------
    #   0       0       1      title animation, but also course_state = 1
    #   0       0       3      after the course is over
    #   0      255             title screen or time trials 
    #   0       1              PLAYING - grand prix with one player
    #   1       0              PAUSED  - grand prix or vs
    #   0       0              PLAYING - vs or gp with two players - but also the animation after the play screen so gotta be careful here!
    #   2      255             CHANGING COURSES - vs
    #   2       0              PLAYING - after having changed courses in vs
    # note: course state is 4 briefly as the game is restarted (is it any other time?)
         
    paused = read_byte(game.is_paused_memory) # this goes to 2 when you're selecting a new course and doesn't go back when you resume playing...
    # in vs, this doesn't actually change when you hit pause, only 255 for title screen
    playing = read_byte(game.is_playing_memory) # this is set to 1 for grand prix but to 0 during vs while playing!!
    course_state = read_byte(game.course_state_memory) # don't pay out when it's 1

    game.game_state_prev = game.game_state

    # playing and paused are both 0 during title animation
    if paused is None or playing is None or course_state is None:
        game.game_state = "game is turned off"
    elif paused == 1 and playing == 0:
        game.game_state = "paused"
    elif playing == 255 or playing == 248 or (paused == 0 and playing == 0 and course_state == 0): # playing is 248 with the everything unlocked cheat, 255 otherwise
        game.game_state = "title screen"
    elif (paused == 0 or paused == 2) and playing != 255 and playing !=248 and course_state != 1 and course_state != 4:
        game.game_state = "playing"
    else:
        game.game_state = "menu" # for vs. mode

    if (game.game_state_prev != game.game_state and game.game_state_prev != None):
        # print(f'the game state just changed.\nprevious game state: {game.game_state_prev}\ncurrent game state: {game.game_state}')
        # if we go from title screen to playing don't wait as long
        # if we go from menu to playing, wait exactly how long we've specified
        if (game.game_state_prev == "title screen" and game.game_state == "playing"):
            # game just started so let reset the program counter to 0
            game.course_timer = 0
            game.vs_wait_time = 1 # don't wait as long if it's the first time playing this course
        elif (game.game_state_prev == "menu" and game.game_state == "playing"):
            # game just started so let reset the program counter to 0
            game.course_timer = 0
            game.vs_wait_time = 15 # wait longer if the course was restarted but we're still on the same course
        
    return game.game_state

def read_position(player):
    player.position = read_byte(player.position_memory)

def read_num_players():
    for player in game.players:
        read_position(player)

    if game.players[3].position == 255 and game.players[2].position == 255 and game.players[1].position == 255:
        game.num_players = 1
        return
    if game.players[3].position == 255 and game.players[2].position == 255:
        game.num_players = 2
        return
    if game.players[3].position == 255:
        game.num_players = 3
        return
    game.num_players = 4

def read_lap(player):
    return read_bytes(player.lap_memory)
    
def check_course_reset():
    for player in game.players[:game.num_players]:
        player.lap = read_lap(player)

    if all(player.lap == 0 for player in game.players): # there may be edge cases where this will not work for grand prix, because there are more than 4 players... ?
        # fresh new course!
        print("NEW COURSE TIME!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # todo: reset their sat counters here
        game.course_timer = 0
        game.course_over = False
        for player in game.players[:game.num_players]:
            player.total_sats_earned += player.sats_earned
            player.sats_earned = 0

def do_collision(player):
     send_message(f"{player.name} was hit!")

def check_collision(player):
    # don't check for collisions if the player has already completed the course
    if player.lap == game.current_course_laps:
        return

    if game.num_players < 3:
        # lightning timer doesn't work for 3 or more players; the data is stored elsewhere in memory (not sure where yet...) 
        lightning_timer = read_bytes(player.lightning_timer_memory)

        if lightning_timer != 0 and lightning_timer != None:
            if player.struck_by_lightning == False:
                player.struck_by_lightning = True
                send_message(f"{player.name} was struck by lightning!")
                return # don't check for regular collision if we know it's lightning
        else: 
            player.struck_by_lightning = False

    # for any damage, including Lightning
    damage_timer = read_bytes(player.damage_timer_memory)

    if damage_timer != 0 and player.struck_by_lightning == False:
        if player.hit_cooldown == 0:
            do_collision(player)
            player.hit_cooldown = 80 # we can test this figure, but it's around 30 frames or half a second right now. 70 is too short for dry dry desert tornado
  
    if player.hit_cooldown > 0:
        player.hit_cooldown -= 1


def frame_loop():
    while True:
        read_num_players()
        if game.game_state == "playing" and game.course_over == False and game.started:
            for player in game.players[:game.num_players]:
                check_collision(player)
        time.sleep(0.016)  # ~60 FPS (every frame)

def game_loop(player):
    if game.current_course == "Award Ceremony":
        # don't pay them for the award ceremony
        # at least not until we compile the grand prix total scores
        return
        
    new_lap = read_lap(player)

    # todo: could check to see if the game has actually been playing so we don't double pay someone here when the mario.py is reset
    if new_lap > player.lap and game.course_timer > 20: # they got a new lap!
        player.lap = new_lap
        if player.position == 1: # they're in first place
            if player.lap == game.current_course_laps: # they completed the course in first place
                message = f"🥇 {game.current_course} completed! {game.current_course_emoji} You finished in first place! {game.current_course_emoji_bonus}"
                pay_player(player, game.course_amount, message)

                # pay the other players a consolation prize + unpaid sats in their "mempools"
                other_players = [p for p in game.players[:game.num_players] if p != player]
                for other_player in other_players:
                    pay_player(other_player, 1, "🍌 Better luck next time! Your princess is in another castle. 👸🏰")

                game.course_over = True # stop paying players until the next course starts
            else:
                message = f"Lap {player.lap} complete! {game.current_course_emoji} You're in the lead on {game.current_course} and are now on lap {player.lap + 1}. {game.current_course_emoji_bonus}" # the '&' breaks ZBD
                pay_player(player, game.lap_amount, message)


    # stream sats to player in first position
    # phoenixd - got 20 payments in luigi circuit (not including lap and course bonuses, definitely slower...)
    # will see how it speeds up with the persistent http connection!!


    # phoenixd luigi circuit to phoenix wallet - 7 first lap
    # phoenixd peach beach to wallet of satoshi - 19 first lap (14 second time)

    # expecting about 30 - 33 stream payments (luigi circuit was 30, peach beach 33, dk mountain 33 (including multple falls))
    # 35 payments with new python code! (152 sats in luigi circuit)
    elif player.position == 1 and game.course_timer % 3 == 0 and game.course_timer > 0: # pay every three cycles
        # it's not a new lap but they're in first so pay them the streaming amount!
        if (game.game_mode == "Grand Prix" and game.course_timer > game.gp_wait_time or game.game_mode == "Vs." and game.course_timer > game.vs_wait_time):
            # btw... the amount here is very much a product of the frequency in which the game loops, this value works for game
            # sleeps .5 seconds between loops and pays every 3rd time (course_timer % 3)
            # but i could change it to actual time to be more accurate
            message = f"{game.current_course_emoji} You're in first place on {game.current_course}! {game.current_course_emoji_bonus}"
            # can add bitcoin facts for each message - perhaps supplied by 4o??
            # \n works on both ZBD and WoS
            # message += "\n\nDid you know that there are 100 million satoshis per bitcoin?"
            pay_player(player, game.stream_amount, message)
            
        else:
            print("game hasn't started yet")
        
    if player.lap != 0 and new_lap == 0: # reset the lap counter & game timer on a new course!
        game.course_timer = 0
        player.lap = 0

def insert_player(address, name, custom_name):
    player = next((p for p in game.players if p.name == name), None)
    player.custom_name = custom_name
    player.lightning_address = address
    if game.funding_source == "lnd":
        get_callback(player)
    if game.funding_source == "phoenixd":
        validate_player_phoenixd(player)
    player.sats_earned = 0

def validate_player_phoenixd(player):
    if player.lightning_address == None:
        return

    player.is_valid = pay_player_phoenixd(player, 1, "🎮 You're registered to play Mario Kart: Double Sats by D++! 🏎️💨")
        
def start_here():
    for player in game.players:
        print(f"{player.name} - {player.lightning_address}")
        if game.funding_source == "lnd":
            get_callback(player)
        if game.funding_source == "phoenixd":
            validate_player_phoenixd(player)

    if all(player.is_valid == True for player in game.players):
        print("Starting game...")
        game.started = True
    else:
        send_message("Unable to start game due to invalid lightning address(es).")
        game.started = False


connected.wait()
start_here()
# place the collision_loop in a separate thread as it checks every frame, much faster than the game_loop
threading.Thread(target=frame_loop, daemon=True).start() 

while True:
    read_game_state()
    read_course()
    
    if game.course_over:
        check_course_reset()

    if game.game_state == "playing" and game.course_over == False and game.started:
        for player in game.players[:game.num_players]:
            game_loop(player)
    
    if game.game_state != "title screen" and game.game_state != "paused":
        game.course_timer += 1

    time.sleep(0.5)
