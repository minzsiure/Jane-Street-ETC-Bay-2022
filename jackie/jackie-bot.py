#!/usr/bin/env python3
# ~~~~~==============   HOW TO RUN   ==============~~~~~
# 1) Configure things in CONFIGURATION section
# 2) Change permissions: chmod +x bot.py
# 3) Run in loop: 
# while true; do ./bot.py --test prod-like; sleep 1; done
# while true; do ./jackie-bot.py --test prod-like; sleep 1; done

import argparse
from collections import deque
from enum import Enum
from lib2to3.pytree import convert
import time
import socket
import json

# ~~~~~============== CONFIGURATION  ==============~~~~~
# Replace "REPLACEME" with your team name!
team_name = "BASKINGSHARKS"
all_orders = {} 
convert_orders = {}
pending_positions = {}
positions = {}
limits = {
    "BOND": 100, 
    "VALBZ": 10, 
    "VALE": 10, 
    "GS": 100, 
    "MS": 100, 
    "WFC": 100, 
    "XLS": 100
}
market_price = {}
bid_price = {}
ask_price = {}
past_weight = 0.9
current_weight = 1 - past_weight

# ~~~~~============== MAIN LOOP ==============~~~~~

# You should put your code here! We provide some starter code as an example,
# but feel free to change/remove/edit/update any of it as you'd like. If you
# have any questions about the starter code, or what to do next, please ask us!
#
# To help you get started, the sample code below tries to buy BOND for a low
# price, and it prints the current prices for VALE every second. The sample
# code is intended to be a working example, but it needs some improvement
# before it will start making good trades!

def main():
    args = parse_arguments()

    symbols = ["BOND", "VALE", "VALBZ", "GS", "MS", "WFC", "XLF"]

    for symbol in symbols:
        positions[symbol] = 0
        pending_positions[symbol] = {}
        pending_positions[symbol]["buy"] = 0
        pending_positions[symbol]["sell"] = 0
        market_price[symbol] = None
        bid_price[symbol] = None
        ask_price[symbol] = None

    exchange = ExchangeConnection(args=args)

    # Store and print the "hello" message received from the exchange. This
    # contains useful information about your positions. Normally you start with
    # all positions at zero, but if you reconnect during a round, you might
    # have already bought/sold symbols and have non-zero positions.
    hello_message = exchange.read_message()
    print("First message from exchange:", hello_message)
    for record in hello_message["symbols"]:
        symbol = record["symbol"]
        position = record["position"]
        positions[symbol] = position

    #fair value
    fair_unit_price_in_cash = {'BOND':1000,'XLF':300,'GS':1500,'MS':1000,'WFC':1500}

    # Send an order for BOND at a good price, but it is low enough that it is
    # unlikely it will be traded against. Maybe there is a better price to
    # pick? Also, you will need to send more orders over time.
    exchange.send_limit_add_message(symbol="BOND", dir=Dir.BUY, price=999)
    exchange.send_limit_add_message(symbol="BOND", dir=Dir.SELL, price=1001)

    # Set up some variables to track the bid and ask price of a symbol. Right
    # now this doesn't track much information, but it's enough to get a sense
    # of the VALE market.
    vale_bid_price, vale_ask_price = None, None
    vale_last_print_time = time.time()

    # Here is the main loop of the program. It will continue to read and
    # process messages in a loop until a "close" message is received. You
    # should write to code handle more types of messages (and not just print
    # the message). Feel free to modify any of the starter code below.
    #
    # Note: a common mistake people make is to call write_message() at least
    # once for every read_message() response.
    #
    # Every message sent to the exchange generates at least one response
    # message. Sending a message in response to every exchange message will
    # cause a feedback loop where your bot's messages will quickly be
    # rate-limited and ignored. Please, don't do that!
    while True:
        message = exchange.read_message()

        # Some of the message types below happen infrequently and contain
        # important information to help you understand what your bot is doing,
        # so they are printed in full. We recommend not always printing every
        # message because it can be a lot of information to read. Instead, let
        # your code handle the messages and just print the information
        # important for you!
        if message["type"] == "close":
            print("The round has ended")
            break
        elif message["type"] == "error":
            print(message)
        elif message["type"] == "reject":
            print(message)
        elif message["type"] == "fill":
            print(message)

            symbol = message["symbol"]
            dir = message["dir"]
            size = message["size"]
            message_type = all_orders[message["order_id"]]["type"]

            if dir == Dir.BUY:
                positions[symbol] += size
                pending_positions[symbol]["buy"] -= size

                if message_type == "convert":
                    if symbol == "VALE":
                        exchange.send_limit_add_message(symbol="VALE", dir=Dir.SELL, price=bid_price["VALE"])
                else:
                    if symbol == "BOND":
                        exchange.send_limit_add_message(symbol="BOND", dir=Dir.SELL, price=1001)
                    if symbol == "VALE":
                        exchange.send_limit_convert_message(symbol="VALE", dir=Dir.SELL, size=size)
                    if symbol == "VALBZ":
                        exchange.send_limit_convert_message(symbol="VALE", dir=Dir.BUY, size=size)
                
            else:
                positions[symbol] -= size
                pending_positions[symbol]["sell"] -= size

                if message_type == "convert":
                    if symbol == "VALE":
                        exchange.send_limit_add_message(symbol="VALBZ", dir=Dir.SELL, price=bid_price["VALBZ"])
                else:
                    if symbol == "BOND":
                        exchange.send_limit_add_message(symbol="BOND", dir=Dir.BUY, price=999)

        elif message["type"] == "book":
            update_market_price(message)

            # Always run arbitrage buying engine. 
            vale_valbz_arbitrage(exchange=exchange)


def update_market_price(message):
    symbol = message["symbol"]

    if message["buy"]:
        bid_price[symbol] = message["buy"][0][0]
    if message["sell"]:
        ask_price[symbol] = message["sell"][0][0]

    if message["buy"] and message["sell"]:
        current_price = (message["buy"][0][1] * bid_price[symbol] + message["sell"][0][1] * ask_price[symbol]) / (message["buy"][0][1] + message["sell"][0][1])
    elif message["buy"]:
        current_price = bid_price[symbol]
    elif message["sell"]:
        current_price = ask_price[symbol]
    
    market_price[symbol] = current_price

def vale_valbz_arbitrage(exchange):
    if bid_price["VALE"] and ask_price["VALBZ"]:
        vale_valbz_difference = bid_price["VALE"] - ask_price["VALBZ"]
        if vale_valbz_difference > 10: 
            exchange.send_limit_add_message(symbol="VALBZ", dir=Dir.BUY, price=ask_price["VALBZ"])

    if bid_price["VALBZ"] and ask_price["VALE"]:
        valbz_vale_difference = bid_price["VALBZ"] - ask_price["VALE"]
        if valbz_vale_difference > 10: 
            exchange.send_limit_add_message(symbol="VALE", dir=Dir.BUY, price=ask_price["VALE"])

# ~~~~~============== PROVIDED CODE ==============~~~~~

# You probably don't need to edit anything below this line, but feel free to
# ask if you have any questions about what it is doing or how it works. If you
# do need to change anything below this line, please feel free to


class Dir(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class ExchangeConnection:
    def __init__(self, args):
        self.message_timestamps = deque(maxlen=500)
        self.exchange_hostname = args.exchange_hostname
        self.port = args.port
        self.exchange_socket = self._connect(add_socket_timeout=args.add_socket_timeout)
        self.order_id = 0

        self._write_message({"type": "hello", "team": team_name.upper()})

    def read_message(self):
        """Read a single message from the exchange"""
        message = json.loads(self.exchange_socket.readline())
        if "dir" in message:
            message["dir"] = Dir(message["dir"])
        return message

    def send_add_message(
        self, symbol: str, dir: Dir, price: int, size: int
    ):
        """Add a new order"""
        buy_limit = limits[symbol] - positions[symbol] - pending_positions[symbol]["buy"]
        sell_limit = limits[symbol] + positions[symbol] - pending_positions[symbol]["sell"]

        if dir == Dir.BUY and size > buy_limit:
            print("!!!BUYING POSITION LIMIT EXCEEDED!!!", positions[symbol], size)
        elif dir == Dir.SELL and size > sell_limit: 
            print("!!!SELLING POSITION LIMIT EXCEEDED!!!", positions[symbol], size)
        else:
            self.order_id += 1

            self._write_message(
                {
                    "type": "add",
                    "order_id": self.order_id,
                    "symbol": symbol,
                    "dir": dir,
                    "price": price,
                    "size": size,
                }
            )

            all_orders[self.order_id] = {
                "type": "add",
                "symbol": symbol,
                "dir": dir,
                "price": price,
                "size": size
            }

            if dir == Dir.BUY:
                pending_positions[symbol]["buy"] += size
            else: 
                pending_positions[symbol]["sell"] += size

    def send_limit_add_message(self, symbol:str, dir: Dir, price: int):
        """Send an order with maximum size possible based on existing limits and current orders."""
        if dir == Dir.BUY:
            buy_limit = limits[symbol] - positions[symbol] - pending_positions[symbol]["buy"]
            self.send_add_message(symbol, dir, price, buy_limit)
        else: 
            sell_limit = limits[symbol] + positions[symbol] - pending_positions[symbol]["sell"]
            self.send_add_message(symbol, dir, price, sell_limit)


    def send_convert_message(self, symbol: str, dir: Dir, size: int):
        """Convert between related symbols"""
        self.order_id += 1

        self._write_message(
            {
                "type": "convert",
                "order_id": self.order_id,
                "symbol": symbol,
                "dir": dir,
                "size": size,
            }
        )
        all_orders[self.order_id] = {
            "type": "convert",
            "symbol": symbol,
            "dir": dir,
            "size": size
        }

        if dir == Dir.BUY and symbol == "VALE":
            pending_positions["VALE"]["buy"] += size 
        if dir == Dir.SELL and symbol == "VALE":
            pending_positions["VALBZ"]["buy"] += size 
    
    def send_limit_convert_message(self, symbol: str, dir: Dir, size: int):
        if symbol == "VALE":
            if dir == Dir.BUY:
                limit = limits["VALE"] - positions["VALE"] - pending_positions["VALE"]["buy"]
                size = max(size, limit)
            else:
                limit = limits["VALBZ"] - positions["VALBZ"] - pending_positions["VALBZ"]["buy"]
                size = max(size, limit)

            self.send_convert_message(symbol, dir, size)

    def send_cancel_message(self, order_id: int):
        """Cancel an existing order"""
        self._write_message({"type": "cancel", "order_id": order_id})
        all_orders.pop(order_id, None)

    def _connect(self, add_socket_timeout):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if add_socket_timeout:
            # Automatically raise an exception if no data has been recieved for
            # multiple seconds. This should not be enabled on an "empty" test
            # exchange.
            s.settimeout(5)
        s.connect((self.exchange_hostname, self.port))
        return s.makefile("rw", 1)

    def _write_message(self, message):
        json.dump(message, self.exchange_socket)
        self.exchange_socket.write("\n")

        now = time.time()
        self.message_timestamps.append(now)
        if len(
            self.message_timestamps
        ) == self.message_timestamps.maxlen and self.message_timestamps[0] > (now - 1):
            print(
                "WARNING: You are sending messages too frequently. The exchange will start ignoring your messages. Make sure you are not sending a message in response to every exchange message."
            )


def parse_arguments():
    test_exchange_port_offsets = {"prod-like": 0, "slower": 1, "empty": 2}

    parser = argparse.ArgumentParser(description="Trade on an ETC exchange!")
    exchange_address_group = parser.add_mutually_exclusive_group(required=True)
    exchange_address_group.add_argument(
        "--production", action="store_true", help="Connect to the production exchange."
    )
    exchange_address_group.add_argument(
        "--test",
        type=str,
        choices=test_exchange_port_offsets.keys(),
        help="Connect to a test exchange.",
    )

    # Connect to a specific host. This is only intended to be used for debugging.
    exchange_address_group.add_argument(
        "--specific-address", type=str, metavar="HOST:PORT", help=argparse.SUPPRESS
    )

    args = parser.parse_args()
    args.add_socket_timeout = True

    if args.production:
        args.exchange_hostname = "production"
        args.port = 25000
    elif args.test:
        args.exchange_hostname = "test-exch-" + team_name
        args.port = 25000 + test_exchange_port_offsets[args.test]
        if args.test == "empty":
            args.add_socket_timeout = False
    elif args.specific_address:
        args.exchange_hostname, port = args.specific_address.split(":")
        args.port = int(port)

    return args


if __name__ == "__main__":
    # Check that [team_name] has been updated.
    assert (
        team_name != ""
    ), "Please put your team name in the variable [team_name]."

    main()
