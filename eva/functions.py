def check_and_buy_arbitrage_XTF_amount(positions, category, amount_to_match):
    if category == "XTF":
        XTF_pos = positions["XTF"]
        # not enough, buy more xtf
        if XTF_pos - amount_to_match["XTF"] < 0:
            exchange.send_add_message(symbol="XLF", dir=Dir.BUY, price=market_price["XLF"], size=amount_to_match["XTF"]-XTF_pos) 

    elif category == "components":
        current_pos = {"BOND":positions["BOND"], "GS":positions["GS"], "MS":positions["MS"], "WFC":positions["WFC"]}
        amount_pending = {'BOND':0, 'GS':0, 'MS':0, 'WFC':0}
        for comp in amount_pending.keys():
            if positions[comp] - amount_to_match[comp] < 0:
                exchange.send_add_message(symbol=comp, dir=Dir.BUY, price=market_price[comp], size=amount_to_match[comp]-current_pos[comp]) 


def arbitrage_XTF(market_price):
    conversion_fee = 100
    BOND, GS, MS, WFC = market_price["BOND"], market_price["GS"], market_price["MS"], market_price["WFC"]
    # compute how curernt market price add up for 10 xtf
    add_on_market_price_for_XTF = 3*BOND + 2*GS + 3*MS + 2*WFC
    stock_amount = {'BOND':3, 'GS':2, 'MS':3, 'WFC':2}
    amount_to_match = {'BOND':3, 'GS':2, 'MS':3, 'WFC':2, 'XFC':10}
    diff = XLF - add_on_market_price_for_XTF
    
    # if current XLF price is greater than all stocks adding up
    # then we should convert all stocks and sell XLF
    # it also means we need to buy all stocks seperately
    if diff > 100: 
        # sell all XLF we have
        exchange.send_add_message(symbol="XLF", dir=Dir.SELL, price=market_price["XLF"], size=positions["XLF"]) 
        
        # if we don't have enough stocks, buy them first so we have 3,2,3,2
        check_and_buy_arbitrage_XTF_amount(positions,"components",amount_to_match)

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
        check_and_buy_arbitrage_XTF_amount(positions,"XLF",amount_to_match)
        
        # convert XLF to stocks, SELL gives out XLF and gives us components
        exchange.send_convert_message(symbol="XLF",dir=Dir.SELL, size=10)

        # sell seperate stocks 3 BOND, 2 GS, 3 MS, 2 WFC 
        # TODO This needs to be based on our current position
        for stock, amount in stock_amount.items():
            exchange.send_add_message(symbol=stock, dir=Dir.SELL, price=market_price[stock], size=amount) 

        # Buy up to 10 XLF
        exchange.send_add_message(symbol="XLF", dir=Dir.BUY, price=market_price["XLF"], size=10) 
