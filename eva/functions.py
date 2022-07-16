# do XLF arbitrage
            if symbol == "XLF" and fair_value["BOND"] and fair_value["GS"] and fair_value["MS"] and fair_value["WFC"] and fair_value["XLF"]:
                arbitrage_XLF(exchange, fair_value)

###########

def check_and_buy_arbitrage_XLF_amount(exchange, positions, category, amount_to_match,fair_value):
    if category == "XLF":
        XLF_pos = positions["XLF"]
        # not enough, buy more xLf
        if XLF_pos - amount_to_match["XLF"] < 0:
            exchange.send_add_message(symbol="XLF", dir=Dir.BUY, price=fair_value["XLF"], size=amount_to_match["XLF"]-XLF_pos) 
            print("checked. not enough XLF", "buying", amount_to_match["XLF"]-XLF_pos, "at", fair_value["XLF"])

    elif category == "components":
        current_pos = {"BOND":positions["BOND"], "GS":positions["GS"], "MS":positions["MS"], "WFC":positions["WFC"]}
        for comp in current_pos.keys():
            if positions[comp] - amount_to_match[comp] < 0:
                exchange.send_add_message(symbol=comp, dir=Dir.BUY, price=fair_value[comp], size=amount_to_match[comp]-current_pos[comp]) 
                print("checked. not enough", comp, "buying", amount_to_match[comp]-current_pos[comp], "at", fair_value[comp])

def arbitrage_XLF(exchange, fair_value):
    conversion_fee = 100
    BOND, GS, MS, WFC, XLF = fair_value["BOND"], fair_value["GS"], fair_value["MS"], fair_value["WFC"], fair_value["XLF"]
    # compute how curernt market price add up for 10 xLf
    add_on_fair_value_for_XLF = 3*BOND + 2*GS + 3*MS + 2*WFC
    stock_amount = {'BOND':3, 'GS':2, 'MS':3, 'WFC':2}
    amount_to_match = {'BOND':3, 'GS':2, 'MS':3, 'WFC':2, 'XLF':10}
    diff = XLF - add_on_fair_value_for_XLF
    
    # if current XLF price is greater than all stocks adding up
    # then we should convert all stocks and sell XLF
    # it also means we need to buy all stocks seperately
    if diff > 100: 
        # sell all XLF we have
        if positions["XLF"] > 0:
            exchange.send_add_message(symbol="XLF", dir=Dir.SELL, price=fair_value["XLF"], size=positions["XLF"]) 
            print("selling all XLF")
        
        # if we don't have enough stocks, buy them first so we have 3,2,3,2
        check_and_buy_arbitrage_XLF_amount(exchange, positions,"components",amount_to_match, fair_value)

        # convert stocks into XLF, BUY receives XLF
        exchange.send_convert_message(symbol="XLF",dir=Dir.BUY, size=10)
        print("converting stocks into 10 XLF")

        # sell all XLF we have
        exchange.send_add_message(symbol="XLF", dir=Dir.SELL, price=fair_value["XLF"], size=positions["XLF"]) 
        print("selling as many XLF as we can")
        
        # buy stocks 3 BOND, 2 GS, 3 MS, 2 WFC 
        # TODO This amt needs to be based on our current position
        for stock, amount in stock_amount.items():
            exchange.send_add_message(symbol=stock, dir=Dir.BUY, price=fair_value[stock], size=amount) 
            print("sending orders to buy 3:2:3:2 stocks, buying", amount, stock, "at", fair_value[stock])

    # if all stocks adding up is greater than current XLF market price, 
    # it means we have more profits trading seperately
    # then we should convert XLF and trade seperate stocks
    # it also means we need to buy XLF
    elif diff < -100:
        # convert XLF to stocks, SELL gives out XLF and gives us components
        if positions["BOND"] < 97 and positions["GS"] < 98 and positions["MS"] < 97 and positions["WFC"] < 98:
            # TODO if we don't have enough XLF, buy XLF such that we have 10
            check_and_buy_arbitrage_XLF_amount(exchange,positions,"XLF",amount_to_match,fair_value)

            exchange.send_convert_message(symbol="XLF",dir=Dir.SELL, size=10)
            print("converting 10XLFs to stocks")

        # sell seperate stocks 3 BOND, 2 GS, 3 MS, 2 WFC 
        # TODO This needs to be based on our current position
        for stock, amount in stock_amount.items():
            exchange.send_add_message(symbol=stock, dir=Dir.SELL, price=fair_value[stock], size=amount) 
            print("selling stock", stock, "at", fair_value[stock])

        # Buy up to 10 XLF
        exchange.send_add_message(symbol="XLF", dir=Dir.BUY, price=fair_value["XLF"], size=max(10, 100-positions["XLF"]) )
        print("buy XLF up to 10")

