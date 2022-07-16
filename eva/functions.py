# do XLF arbitrage
            if symbol == "XLF" and fair_value["BOND"] and fair_value["GS"] and fair_value["MS"] and fair_value["WFC"] and fair_value["XLF"]:
                arbitrage_XLF(exchange, fair_value)

###########

############## XLF Arbitrage ##############
def check_and_buy_arbitrage_XLF_amount(exchange, positions, category, amount_to_match,fair_value):
    if category == "XLF":
        XLF_pos = positions["XLF"]
        # not enough, buy more xLf
        print("trying to buy XLF, condition:", XLF_pos - amount_to_match["XLF"] < 0)
        print("We have", XLF_pos, "many XLF, and current ask is", ask_price["XLF"], "comparing .95 fair is",0.95*fair_value["XLF"])
        if XLF_pos - amount_to_match["XLF"] < 0:
            exchange.send_limit_add_message(symbol="XLF", dir=Dir.BUY, price=round(bid_price["XLF"]))
            print("checked. not enough XLF", "buying", amount_to_match["XLF"]-XLF_pos, "at", fair_value["XLF"])
            return True

    elif category == "components":
        current_pos = {"BOND":positions["BOND"], "GS":positions["GS"], "MS":positions["MS"], "WFC":positions["WFC"]}
        for comp in current_pos.keys():
            print("trying to buy stocks for conversion, condition:", positions[comp] - amount_to_match[comp] < 0 and ask_price[comp] <= 0.95*fair_value["XLF"])
            if positions[comp] - amount_to_match[comp] < 0 and ask_price[comp] <= 0.95*fair_value["XLF"]:
                exchange.send_limit_add_message(symbol=comp, dir=Dir.BUY, price=round(ask_price[comp]))
                print("checked. not enough", comp, "buying", amount_to_match[comp]-current_pos[comp], "at", fair_value[comp])
                return True
    return False

def arbitrage_XLF(exchange, fair_value):
    conversion_fee = 100
    BOND, GS, MS, WFC, XLF = fair_value["BOND"], fair_value["GS"], fair_value["MS"], fair_value["WFC"], fair_value["XLF"]
    # compute how curernt market price add up for 10 xLf
    add_on_fair_value_for_XLF = 3*BOND + 2*GS + 3*MS + 2*WFC
    stock_amount = {'BOND':3, 'GS':2, 'MS':3, 'WFC':2}
    amount_to_match = {'BOND':3, 'GS':2, 'MS':3, 'WFC':2, 'XLF':10}
    diff = XLF - add_on_fair_value_for_XLF
    print("currt diff", diff)
    
    # if current XLF price is greater than all stocks adding up
    # then we should convert all stocks and sell XLF
    # it also means we need to buy all stocks seperately
    if diff > 100: 
        # sell all XLF we have
        if positions["XLF"] > 0 and bid_price["XLF"] > 1.05*fair_value["XLF"]:
            exchange.send_limit_add_message(symbol="XLF", dir=Dir.SELL, price=round(bid_price["XLF"]))
            print("selling all XLF at", round(bid_price["XLF"]))
        
            # if we don't have enough stocks, buy them first so we have 3,2,3,2
            if check_and_buy_arbitrage_XLF_amount(exchange, positions,"components",amount_to_match, fair_value):

                # convert stocks into XLF, BUY receives XLF
                exchange.send_limit_convert_message(symbol="XLF", dir=Dir.BUY, size=10)
                print("converting stocks into 10 XLF")

                # sell all XLF we have
                exchange.send_limit_add_message(symbol="XLF", dir=Dir.SELL, price=round(fair_value["XLF"]))
                print("selling as many XLF as we can")
            
                # buy stocks 3 BOND, 2 GS, 3 MS, 2 WFC 
                for stock, amount in stock_amount.items():
                    if ask_price[stock] <= 0.95 * fair_value[stock]:
                        exchange.send_limit_add_message(symbol=stock, dir=Dir.BUY, price=round(ask_price[stock]))
                        print("sending orders to buy 3:2:3:2 stocks, buying", amount, stock, "at", ask_price[stock])

    # if all stocks adding up is greater than current XLF market price, 
    # it means we have more profits trading seperately
    # then we should convert XLF and trade seperate stocks
    # it also means we need to buy XLF
    elif diff < -100:
        # convert XLF to stocks, SELL gives out XLF and gives us components
        
        print("hitting here 1")
        # TODO if we don't have enough XLF, buy XLF such that we have 10
        if check_and_buy_arbitrage_XLF_amount(exchange,positions,"XLF",amount_to_match,fair_value):
            exchange.send_limit_convert_message(symbol="XLF", dir=Dir.SELL, size=10)
            print("converting 10XLFs to stocks")

            # sell seperate stocks 3 BOND, 2 GS, 3 MS, 2 WFC 
            # TODO This needs to be based on our current position
            for stock, amount in stock_amount.items():
                if bid_price[stock] >= 1.05 * fair_value[stock]:
                    exchange.send_limit_add_message(symbol=stock, dir=Dir.SELL, price=round(bid_price[stock]))
                    print("selling stock", stock, "at", bid_price[stock])

            # Buy up to 10 XLF
            if ask_price["XLF"] <= 0.95 * fair_value["XLF"]:
                exchange.send_limit_add_message(symbol="XLF", dir=Dir.BUY, price=round(ask_price["XLF"]))
                print("buy XLF up to 10")

