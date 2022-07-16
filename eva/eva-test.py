#!/usr/bin/env python3
# ~~~~~==============   HOW TO RUN   ==============~~~~~
# 1) Configure things in CONFIGURATION section
# 2) Change permissions: chmod +x bot.py
# 3) Run in loop: while true; do ./bot.py --test prod-like; sleep 1; done

import argparse
from collections import deque
from enum import Enum
import time
import socket
import json

# ~~~~~============== CONFIGURATION  ==============~~~~~
# Replace "REPLACEME" with your team name!
team_name = "BASKINGSHARKS"
all_orders = {} 
positions = {}
pending_positions = {}
limits = {
    "BOND": 100, 
    "VALBZ": 10, 
    "VALE": 10, 
    "GS": 100, 
    "MS": 100, 
    "WFC": 100, 
    "XLS": 100
}

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

    for symbol in symbols: 
        pending_positions[symbol] = {}
        pending_positions[symbol]["buy"] = 0
        pending_positions[symbol]["sell"] = 0

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
    exchange.send_add_message(symbol="BOND", dir=Dir.BUY, price=999, size=100)
    exchange.send_add_message(symbol="BOND", dir=Dir.SELL, price=1001, size=100)

    # Set up some variables to track the bid and ask price of a symbol. Right
    # now this doesn't track much information, but it's enough to get a sense
    # of the VALE market.
    symbols = ["BOND", "VALBZ", "VALE", "GS", "MS", "WFC", "XLS"]
    limits = {"BOND":100, "VALBZ":10, "VALE":10, "GS":100, "MS":100, "WFC":100, "XLS":100}
    bid_price = {}
    ask_price = {}
    market_price = {}
    for symbol in symbols:
        bid_price[symbol] = None
        ask_price[symbol] = None
        market_price[symbol] = None
    market_price["BOND"] = 1000

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

            if dir == Dir.BUY:
                positions[symbol] += size
                pending_positions[symbol]["buy"] -= size

                if symbol == "BOND":
                    exchange.send_limit_add_message(symbol="BOND", dir=Dir.SELL, price=1001)
            else:
                positions[symbol] -= size
                pending_positions[symbol]["sell"] -= size

                if symbol == "BOND":
                    exchange.send_limit_add_message(symbol="BOND", dir=Dir.BUY, price=999)

        elif message["type"] == "book":
            symbol = message["symbol"]
            if message["buy"]:
                bid_price[symbol] = message["buy"][0][0]
            if message["sell"]:
                ask_price[symbol] = message["sell"][0][0]
            if symbol in {"VALBZ", "GS", "MS", "WFC"}:
                if bid_price[symbol] and ask_price[symbol]:
                    market_price[symbol] = (bid_price[symbol] + ask_price[symbol]) / 2
                elif bid_price[symbol]:
                    market_price[symbol] = bid_price[symbol]
                elif ask_price[symbol]:
                    market_price[symbol] = ask_price[symbol]
            market_price["VALE"] = market_price["VALBZ"]
            if market_price["BOND"] and market_price["GS"] and market_price["MS"] and market_price["WFC"]:
                market_price["XLF"] = (3 * market_price["BOND"] + 2 * market_price["GS"] + 3 * market_price["MS"] + 2 * market_price["WFC"]) / 10
        
        # do XLF arbitrage
        if market_price["BOND"] and market_price["GS"] and market_price["MS"] and market_price["WFC"] and market_price["XLF"]:
            arbitrage_XLF(market_price)

def check_and_buy_arbitrage_XLF_amount(positions, category, amount_to_match):
    if category == "XLF":
        XLF_pos = positions["XLF"]
        # not enough, buy more xLf
        if XLF_pos - amount_to_match["XLF"] < 0:
            exchange.send_add_message(symbol="XLF", dir=Dir.BUY, price=market_price["XLF"], size=amount_to_match["XLF"]-XLF_pos) 

    elif category == "components":
        current_pos = {"BOND":positions["BOND"], "GS":positions["GS"], "MS":positions["MS"], "WFC":positions["WFC"]}
        amount_pending = {'BOND':0, 'GS':0, 'MS':0, 'WFC':0}
        for comp in amount_pending.keys():
            if positions[comp] - amount_to_match[comp] < 0:
                exchange.send_add_message(symbol=comp, dir=Dir.BUY, price=market_price[comp], size=amount_to_match[comp]-current_pos[comp]) 


def arbitrage_XLF(market_price):
    conversion_fee = 100
    BOND, GS, MS, WFC, XLF = market_price["BOND"], market_price["GS"], market_price["MS"], market_price["WFC"], market_price["XLF"]
    # compute how curernt market price add up for 10 xLf
    add_on_market_price_for_XLF = 3*BOND + 2*GS + 3*MS + 2*WFC
    stock_amount = {'BOND':3, 'GS':2, 'MS':3, 'WFC':2}
    amount_to_match = {'BOND':3, 'GS':2, 'MS':3, 'WFC':2, 'XFC':10}
    diff = XLF - add_on_market_price_for_XLF
    
    # if current XLF price is greater than all stocks adding up
    # then we should convert all stocks and sell XLF
    # it also means we need to buy all stocks seperately
    if diff > 100: 
        # sell all XLF we have
        exchange.send_add_message(symbol="XLF", dir=Dir.SELL, price=market_price["XLF"], size=positions["XLF"]) 
        
        # if we don't have enough stocks, buy them first so we have 3,2,3,2
        check_and_buy_arbitrage_XLF_amount(positions,"components",amount_to_match)

        # convert stocks into XLF, BUY receives XLF
        exchange.send_convert_message(symbol="XLF",dir=Dir.BUY, size=10)

        # sell all XLF we have
        exchange.send_add_message(symbol="XLF", dir=Dir.SELL, price=market_price["XLF"], size=10) 
        
        # buy stocks 3 BOND, 2 GS, 3 MS, 2 WFC 
        # TODO This amt needs to be based on our current position
        for stock, amount in stock_amount.items():
            exchange.send_add_message(symbol=stock, dir=Dir.BUY, price=market_price[stock], size=amount) 

    # if all stocks adding up is greater than current XLF market price, 
    # it means we have more profits trading seperately
    # then we should convert XLF and trade seperate stocks
    # it also means we need to buy XLF
    elif diff < -100:
        # TODO if we don't have enough XLF, buy XLF such that we have 10
        check_and_buy_arbitrage_XLF_amount(positions,"XLF",amount_to_match)
        
        # convert XLF to stocks, SELL gives out XLF and gives us components
        exchange.send_convert_message(symbol="XLF",dir=Dir.SELL, size=10)

        # sell seperate stocks 3 BOND, 2 GS, 3 MS, 2 WFC 
        # TODO This needs to be based on our current position
        for stock, amount in stock_amount.items():
            exchange.send_add_message(symbol=stock, dir=Dir.SELL, price=market_price[stock], size=amount) 

        # Buy up to 10 XLF
        exchange.send_add_message(symbol="XLF", dir=Dir.BUY, price=market_price["XLF"], size=10) 


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

    def send_cancel_message(self, order_id: int):
        """Cancel an existing order"""
        self._write_message({"type": "cancel", "order_id": order_id})

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
