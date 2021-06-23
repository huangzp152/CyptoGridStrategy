"""
    币安推荐码:  返佣10%
    https://www.binancezh.pro/cn/register?ref=AIR1GC70

    币安合约推荐码: 返佣10%
    https://www.binancezh.com/cn/futures/ref/51bitquant

    if you don't have a binance account, you can use the invitation link to register one:
    https://www.binancezh.com/cn/futures/ref/51bitquant

    or use the inviation code: 51bitquant

    网格交易: 适合币圈的高波动率的品种，适合现货， 如果交易合约，需要注意防止极端行情爆仓。


    服务器购买地址: https://www.ucloud.cn/site/global.html?invitation_code=C1x2EA81CD79B8C#dongjing

"""
import time

from gateway import BinanceSpotHttp, OrderStatus, OrderType, OrderSide
from utils import config
from utils import utility, round_to
from enum import Enum
import logging
from datetime import datetime

class BinanceTrader(object):

    def __init__(self):
        """
        :param api_key:
        :param secret:
        :param trade_type: 交易的类型， only support future and spot.
        """
        self.http_client = BinanceSpotHttp(api_key=config.api_key, secret=config.api_secret, proxy_host=config.proxy_host, proxy_port=config.proxy_port)

        #其实本来就是预设它一直跑着的，所以不存在需要存储下次使用的问题，下次应再从服务器中获取添加
        self.buy_orders = []  # 买单. buy orders
        self.sell_orders = [] # 卖单. sell orders


    def get_bid_ask_price(self):

        ticker = self.http_client.get_ticker(config.symbol)

        bid_price = 0
        ask_price = 0
        if ticker:
            bid_price = float(ticker.get('bidPrice', 0))
            ask_price = float(ticker.get('askPrice', 0))

        return bid_price, ask_price

    #modify backup
    # def grid_trader(self):
    #     """
    #     执行核心逻辑，网格交易的逻辑.
    #     :return:
    #     """
    #
    #     bid_price, ask_price = self.get_bid_ask_price()
    #     print(f"bid_price: {bid_price}, ask_price: {ask_price}")
    #
    #     quantity = round_to(float(config.quantity), float(config.min_qty))
    #
    #     self.buy_orders.sort(key=lambda x: float(x['price']), reverse=True)  # 最高价到最低价.
    #     self.sell_orders.sort(key=lambda x: float(x['price']), reverse=True)  # 最高价到最低价.
    #     print(f"buy orders: {self.buy_orders}")
    #     print("------------------------------")
    #     print(f"sell orders: {self.sell_orders}")
    #
    #     buy_delete_orders = []  # 需要删除买单
    #     sell_delete_orders = [] # 需要删除的卖单
    #
    #
    #     # 买单逻辑,检查成交的情况.
    #     for buy_order in self.buy_orders:
    #
    #         check_order = self.http_client.get_order(buy_order.get('symbol', config.symbol),client_order_id=buy_order.get('clientOrderId'))
    #
    #         if check_order:
    #             if check_order.get('status') == OrderStatus.CANCELED.value:
    #                 buy_delete_orders.append(buy_order)
    #                 print(f"buy order status was canceled: {check_order.get('status')}")
    #             elif check_order.get('status') == OrderStatus.FILLED.value:
    #                 # 买单成交，挂卖单.
    #                 logging.info(f"买单成交时间: {datetime.now()}, 价格: {check_order.get('price')}, 数量: {check_order.get('origQty')}")
    #
    #
    #                 sell_price = round_to(float(check_order.get("price")) * (1 + float(config.gap_percent)), float(config.min_price))
    #
    #                 if 0 < sell_price < ask_price:#卖高一点
    #                     # 防止价格
    #                     sell_price = round_to(ask_price, float(config.min_price))
    #
    #                 new_sell_order = self.http_client.place_order(symbol=config.symbol, order_side=OrderSide.SELL, order_type=OrderType.LIMIT, quantity=quantity, price=sell_price)
    #                 if new_sell_order:
    #                     buy_delete_orders.append(buy_order)#买单列表删除
    #                     self.sell_orders.append(new_sell_order)#加入卖单列表
    #
    #                 buy_price = round_to(float(check_order.get("price")) * (1 - float(config.gap_percent)),
    #                                  config.min_price)
    #                 if buy_price > bid_price > 0:#买低一点
    #                     buy_price = round_to(bid_price, float(config.min_price))
    #
    #                 new_buy_order = self.http_client.place_order(symbol=config.symbol, order_side=OrderSide.BUY, order_type=OrderType.LIMIT, quantity=quantity, price=buy_price)
    #                 if new_buy_order:
    #                     self.buy_orders.append(new_buy_order)
    #
    #
    #             elif check_order.get('status') == OrderStatus.NEW.value:
    #                 print("buy order status is: New")
    #             else:
    #                 print(f"buy order status is not above options: {check_order.get('status')}")
    #
    #     # 过期或者拒绝的订单删除掉.
    #     for delete_order in buy_delete_orders:
    #         self.buy_orders.remove(delete_order)
    #
    #     # 卖单逻辑, 检查卖单成交情况.
    #     for sell_order in self.sell_orders:
    #
    #         check_order = self.http_client.get_order(sell_order.get('symbol', config.symbol),
    #                                            client_order_id=sell_order.get('clientOrderId'))
    #         if check_order:
    #             if check_order.get('status') == OrderStatus.CANCELED.value:
    #                 sell_delete_orders.append(sell_order)
    #
    #                 print(f"sell order status was canceled: {check_order.get('status')}")
    #             elif check_order.get('status') == OrderStatus.FILLED.value:
    #                 logging.info(
    #                     f"卖单成交时间: {datetime.now()}, 价格: {check_order.get('price')}, 数量: {check_order.get('origQty')}")
    #                 # 卖单成交，先下买单.
    #                 buy_price = round_to(float(check_order.get("price")) * (1 - float(config.gap_percent)), float(config.min_price))
    #                 if buy_price > bid_price > 0:
    #                     buy_price = round_to(bid_price, float(config.min_price))
    #
    #                 new_buy_order = self.http_client.place_order(symbol=config.symbol, order_side=OrderSide.BUY,
    #                                                          order_type=OrderType.LIMIT, quantity=quantity, price=buy_price)
    #                 if new_buy_order:
    #                     sell_delete_orders.append(sell_order)
    #                     self.buy_orders.append(new_buy_order)
    #
    #                 sell_price = round_to(float(check_order.get("price")) * (1 + float(config.gap_percent)), float(config.min_price))
    #
    #                 if 0 < sell_price < ask_price:
    #                     # 防止价格
    #                     sell_price = round_to(ask_price, float(config.min_price))
    #
    #                 new_sell_order = self.http_client.place_order(symbol=config.symbol, order_side=OrderSide.SELL,
    #                                                              order_type=OrderType.LIMIT, quantity=quantity,
    #                                                              price=sell_price)
    #                 if new_sell_order:
    #                     self.sell_orders.append(new_sell_order)
    #
    #             elif check_order.get('status') == OrderStatus.NEW.value:
    #                 print("sell order status is: New")
    #             else:
    #                 print(f"sell order status is not in above options: {check_order.get('status')}")
    #
    #     # 过期或者拒绝的订单删除掉.
    #     for delete_order in sell_delete_orders:
    #         self.sell_orders.remove(delete_order)
    #
    #     # 没有买单的时候.
    #     if len(self.buy_orders) <= 0:
    #         if bid_price > 0:
    #             price = round_to(bid_price * (1 - float(config.gap_percent)), float(config.min_price))
    #             buy_order = self.http_client.place_order(symbol=config.symbol,order_side=OrderSide.BUY, order_type=OrderType.LIMIT, quantity=quantity,price=price)
    #             if buy_order:
    #                 self.buy_orders.append(buy_order)
    #
    #     elif len(self.buy_orders) > int(config.max_orders): # 最多允许的挂单数量.
    #         # 订单数量比较多的时候.
    #         self.buy_orders.sort(key=lambda x: float(x['price']), reverse=False)  # 最低价到最高价
    #
    #         delete_order = self.buy_orders[0]#把最低价的买单删掉
    #         order = self.http_client.cancel_order(delete_order.get('symbol'), client_order_id=delete_order.get('clientOrderId'))
    #         if order:
    #             self.buy_orders.remove(delete_order)
    #
    #     # 没有卖单的时候.
    #     if len(self.sell_orders) <= 0:
    #         if ask_price > 0:
    #             price = round_to(ask_price * (1 + float(config.gap_percent)), float(config.min_price))
    #             order = self.http_client.place_order(symbol=config.symbol,order_side=OrderSide.SELL, order_type=OrderType.LIMIT, quantity=quantity,price=price)
    #             if order:
    #                 self.sell_orders.append(order)
    #
    #     elif len(self.sell_orders) > int(config.max_orders): # 最多允许的挂单数量.
    #         # 订单数量比较多的时候.
    #         self.sell_orders.sort(key=lambda x: x['price'], reverse=True)  # 最高价到最低价
    #
    #         delete_order = self.sell_orders[0]#把最高价的删掉
    #         order = self.http_client.cancel_order(delete_order.get('symbol'),
    #                                               client_order_id=delete_order.get('clientOrderId'))
    #         if order:
    #             self.sell_orders.remove(delete_order)


    '''
    10个格子，初始价格37500，
    
    价格list：[37100,37200,37300,37400,【37500】,37600,37700,37800,37900,38000]
    
    多单
    for piece in list:遍历每个价格，
        第一个价格，检查状态（get order）是否持有（Fill），如果持有，检查有没有挂多单（place_order），如果没有就挂多单
        其它每个价格，如果没挂买单，则挂上去
    
    空单  
    for piece in list:遍历每个价格，
        第一个价格，检查状态（get order）是否持有（Fill），如果持有，检查有没有挂空单（place_order），如果没有就挂空单
        其它每个价格，如果没挂买单，则挂上去
    
    '''

    def henged_grid_strategy(self):

        #先查询价格
        bid_price, ask_price = self.get_bid_ask_price()
        print(f"买价 bid_price: {bid_price}, 卖价 ask_price: {ask_price}")
        # print(f"我的账户信息：get account info: {self.http_client.get_account_info()}")
        # print(f"我的这是啥：get exchange info: {self.http_client.get_exchange_info()}")
        # print(f"我的交易：get my trades info: {self.http_client.get_my_trades(config.symbol)}")
        # print(f"我的交易：get all trades info: {self.http_client.get_all_orders(config.symbol)}")

        # print("check specific order :" + str(self.http_client.get_order(config.symbol, "x-A6SIDXVS16242842419521000005")))

        quantity = self._format(float(config.quantity))# 买多少个
        initial_price = config.initial_price
        grid_number = config.grid_number
        max_border_price = config.max_border_price
        min_border_price = config.min_border_price
        price_interval = float((max_border_price - min_border_price) / float(grid_number))
        price_list = [self._format(float(min_border_price + price_interval * i)) for i in range(0, grid_number + 1)]
        price_list.sort(reverse=False)
        print("price list:" + str(price_list))

        open_orders = self.http_client.get_open_orders(config.symbol)#获取挂着的单
        # print("open_order before:")


        if open_orders and len(open_orders) > 0:

            for i in range(0, len(open_orders)):
                # print(str(open_orders[i]))

                #把未添加的挂着的买单添加到买单列表里
                has_add_in_buy_order = False
                for j in range(0, len(self.buy_orders)):
                    if open_orders[i].get("clientOrderId") == self.buy_orders[j].get("clientOrderId") and open_orders[i].get("side") == OrderSide.BUY.value:
                        has_add_in_buy_order = True
                        break
                if not has_add_in_buy_order:
                    if open_orders[i].get("side") == OrderSide.BUY.value:
                        if len(self.buy_orders) > 0 and open_orders[i].get("status") != self.buy_orders[j].get("status"):
                            self.buy_orders.remove(self.buy_orders[j])
                        self.buy_orders.append(open_orders[i])

                #把未添加的挂着的卖单添加到卖单列表里
                has_add_in_sell_order = False
                for j in range(0, len(self.sell_orders)):
                    if open_orders[i].get("clientOrderId") == self.sell_orders[j].get("clientOrderId") and open_orders[i].get("side") == OrderSide.SELL.value:
                        has_add_in_sell_order = True
                        break
                if not has_add_in_sell_order:
                    if open_orders[i].get("side") == OrderSide.SELL.value:
                        if len(self.sell_orders) > 0 and open_orders[i].get("status") != self.sell_orders[j].get("status"):
                            self.sell_orders.remove(self.sell_orders[j])
                        self.sell_orders.append(open_orders[i])


        #挂买单
        for i in range(0, len(price_list) - 1):
        # for price in price_list:
            need_place_buy_order = True
            if self.buy_orders or len(self.buy_orders) > 0:
                for j in range(0, len(self.buy_orders)):
                    if price_list[i] == self._format(float(self.buy_orders[j].get("price"))):
                        print(str(price_list[i]) + "这个价格已经有买单了，无需重复下单～")
                        need_place_buy_order = False
                        break
                    if self.buy_orders[j].get("status") == OrderStatus.FILLED.value:
                        print(str(price_list[i]) + "这个价格的买单成交了，无需重复下单～")
                        need_place_buy_order = False
                        break
            if need_place_buy_order:
                print("以" + str(price_list[i]) + "的价格下单～")
                new_buy_order = self.http_client.place_order(config.symbol, OrderSide.BUY, OrderType.LIMIT, quantity, price_list[i])
                self.buy_orders.append(new_buy_order)
            # time.sleep(1)

        # check open buy order
        open_orders_after = self.http_client.get_open_orders(config.symbol)
        for order in open_orders_after:
            if order.get("side") == OrderSide.BUY.value:
                print("挂着的买单:" + str(order))

        # check open sell order
        open_orders_after = self.http_client.get_open_orders(config.symbol)
        for order in open_orders_after:
            if order.get("side") == OrderSide.SELL.value:
                print("挂着的卖单:" + str(order))

        # 买入成交了的就挂卖单
        for buy_order in self.buy_orders:
            current_remote_order = self.http_client.get_order(config.symbol, buy_order.get("clientOrderId"))
            # print("check buy order status after:" + str(current_remote_order.get("status") + ", id:" + str(current_remote_order.get("clientOrderId")) + ", price:" + str(current_remote_order.get("price"))))
            if current_remote_order.get("status") != buy_order.get("status"):#更新订单
                self.buy_orders.remove(buy_order)
                self.buy_orders.append(current_remote_order)

            if current_remote_order.get("side") == OrderSide.BUY.value and current_remote_order.get("status") == OrderStatus.FILLED.value:#已成交的，挂卖单
                print("buy order is filled, place sell order:" + str(current_remote_order.get("clientOrderId")))
                need_place_sell_order = True
                for i in range(0, len(self.sell_orders)):
                    if current_remote_order.get("clientOrderId") == self.sell_orders[i].get("clientOrderId"):
                        need_place_sell_order = False
                        break
                if need_place_sell_order:
                    new_sell_order = self.http_client.place_order(config.symbol, OrderSide.SELL, OrderType.LIMIT, quantity, float(current_remote_order.get("price")) + price_interval)
                    self.sell_orders.append(new_sell_order)

        #check
        open_sell_orders_after = []
        for sell_order in self.sell_orders:
            open_sell_orders_after.append(self.http_client.get_order(config.symbol, sell_order.get("clientOrderId")))
        # for order in open_sell_orders_after:
        #     if order.get("side") == OrderSide.SELL.value:
        #         print("check open sell order after:" + str(order))

        # check_order = self.http_client.get_order(buy_order.get('symbol', config.symbol),
        #                                          client_order_id=buy_order.get('clientOrderId'))
        # if check_order.get('status') == OrderStatus.NEW.value:



        # for i in range(0, len(price_list) - 1):


        #遍历买单

        # 买一份
        # self.buy_one_piece()
        # 挂卖单
        # self.place_one_piece()

        # 卖一份
        # self.sell_one_piece()

    def _format(self, price):
        return "{:.6f}".format(price)


    def buy_one_piece(self):
        #先查询价格
        bid_price, ask_price = self.get_bid_ask_price()
        print(f"买价 bid_price: {bid_price}, 卖价 ask_price: {ask_price}")
        quantity = self._format(float(config.quantity))# 买多少个
        #买一份
        if bid_price > 0:
            price = self._format(bid_price * (1 - float(config.gap_percent)))#价格为买价下跌设定的百分比，按这个价格下单
            print(f"以:" + str(price) + "这个价格买入,比买价低的百分比：" + str(config.gap_percent) + "，买的产品:" + str(config.symbol) + ", 买的数量：" + str(quantity) + "(需要" + str(round(price*quantity,2))+ "U)")
            buy_order = self.http_client.place_order(symbol=config.symbol, order_side=OrderSide.BUY, order_type=OrderType.LIMIT, quantity=quantity, price=price)
            print(f"check buy_order:" + str(buy_order))

            check_order = self.http_client.get_order(buy_order.get('symbol', config.symbol), client_order_id=buy_order.get('clientOrderId'))
            if check_order.get('status') == OrderStatus.NEW.value:
                print(f"订单状态 order current status:{check_order.get('status')}，新增（挂着？）")
            else:
                print(f"订单状态order current status:{check_order.get('status')}")

    def sell_one_piece(self):
        #先查询价格
        bid_price, ask_price = self.get_bid_ask_price()
        print(f"买价 bid_price: {bid_price}, 卖价 ask_price: {ask_price}")
        quantity = round_to(float(config.quantity), float(config.min_qty))# 买多少个
        #卖一份
        if ask_price > 0:
            price = round_to(ask_price * (1 + float(config.gap_percent)), float(config.min_price))
            print(f"以:" + str(price) + "这个价格卖出,比卖价高的百分比：" + str(config.gap_percent) + "，卖的产品:" + str(config.symbol) + ", 卖的数量：" + str(quantity) + "(需要" + str(round(price*quantity,2))+ "U)")
            sell_order = self.http_client.place_order(symbol=config.symbol, order_side=OrderSide.SELL, order_type=OrderType.LIMIT, quantity=quantity, price=price)
            print(f"check sell_order:" + str(sell_order))
        #
            check_order = self.http_client.get_order(sell_order.get('symbol', config.symbol), client_order_id=sell_order.get('clientOrderId'))
            if check_order.get('status') == OrderStatus.NEW.value:
                print(f"订单状态 order current status:{check_order.get('status')}，新增（挂着？）")
            else:
                print(f"订单状态order current status:{check_order.get('status')}")

    # def grid_trader_new(self):
    #     """
    #     执行核心逻辑，网格交易的逻辑.
    #     :return:
    #     """
    #
    #     bid_price, ask_price = self.get_bid_ask_price()
    #     print(f"bid_price: {bid_price}, ask_price: {ask_price}")
    #
    #     quantity = round_to(float(config.quantity), float(config.min_qty)) # 买多少个
    #
    #     self.buy_orders.sort(key=lambda x: float(x['price']), reverse=True)  # 最高价到最低价.
    #     self.sell_orders.sort(key=lambda x: float(x['price']), reverse=True)  # 最高价到最低价.
    #     print(f"buy orders: {self.buy_orders}")
    #     print("------------------------------")
    #     print(f"sell orders: {self.sell_orders}")
    #
    #     buy_delete_orders = []# 需要删除买单
    #     sell_delete_orders = []# 需要删除的卖单
    #
    #
    #     # 买单逻辑,检查成交的情况.
    #     for buy_order in self.buy_orders:
    #
    #         check_order = self.http_client.get_order(buy_order.get('symbol', config.symbol),client_order_id=buy_order.get('clientOrderId'))
    #
    #         if check_order:
    #             if check_order.get('status') == OrderStatus.CANCELED.value:
    #                 buy_delete_orders.append(buy_order)
    #                 print(f"buy order status was canceled: {check_order.get('status')}")
    #             elif check_order.get('status') == OrderStatus.FILLED.value:
    #                 # 买单成交，挂卖单.
    #                 logging.info(f"买单成交时间: {datetime.now()}, 价格: {check_order.get('price')}, 数量: {check_order.get('origQty')}")
    #
    #
    #                 sell_price = round_to(float(check_order.get("price")) * (1 + float(config.gap_percent)), float(config.min_price))
    #
    #                 if 0 < sell_price < ask_price:#卖高一点
    #                     # 防止价格
    #                     sell_price = round_to(ask_price, float(config.min_price))
    #
    #                 new_sell_order = self.http_client.place_order(symbol=config.symbol, order_side=OrderSide.SELL, order_type=OrderType.LIMIT, quantity=quantity, price=sell_price)
    #                 if new_sell_order:
    #                     buy_delete_orders.append(buy_order)#买单列表删除
    #                     self.sell_orders.append(new_sell_order)#加入卖单列表
    #
    #                 buy_price = round_to(float(check_order.get("price")) * (1 - float(config.gap_percent)),
    #                                  config.min_price)
    #                 if buy_price > bid_price > 0:#买低一点
    #                     buy_price = round_to(bid_price, float(config.min_price))
    #
    #                 new_buy_order = self.http_client.place_order(symbol=config.symbol, order_side=OrderSide.BUY, order_type=OrderType.LIMIT, quantity=quantity, price=buy_price)
    #                 if new_buy_order:
    #                     self.buy_orders.append(new_buy_order)
    #
    #
    #             elif check_order.get('status') == OrderStatus.NEW.value:
    #                 print("buy order status is: New")
    #             else:
    #                 print(f"buy order status is not above options: {check_order.get('status')}")
    #
    #     # 过期或者拒绝的订单删除掉.
    #     for delete_order in buy_delete_orders:
    #         self.buy_orders.remove(delete_order)
    #
    #     # 卖单逻辑, 检查卖单成交情况.
    #     for sell_order in self.sell_orders:
    #
    #         check_order = self.http_client.get_order(sell_order.get('symbol', config.symbol),
    #                                            client_order_id=sell_order.get('clientOrderId'))
    #         if check_order:
    #             if check_order.get('status') == OrderStatus.CANCELED.value:
    #                 sell_delete_orders.append(sell_order)
    #
    #                 print(f"sell order status was canceled: {check_order.get('status')}")
    #             elif check_order.get('status') == OrderStatus.FILLED.value:
    #                 logging.info(
    #                     f"卖单成交时间: {datetime.now()}, 价格: {check_order.get('price')}, 数量: {check_order.get('origQty')}")
    #                 # 卖单成交，先下买单.
    #                 buy_price = round_to(float(check_order.get("price")) * (1 - float(config.gap_percent)), float(config.min_price))
    #                 if buy_price > bid_price > 0:
    #                     buy_price = round_to(bid_price, float(config.min_price))
    #
    #                 new_buy_order = self.http_client.place_order(symbol=config.symbol, order_side=OrderSide.BUY,
    #                                                          order_type=OrderType.LIMIT, quantity=quantity, price=buy_price)
    #                 if new_buy_order:
    #                     sell_delete_orders.append(sell_order)
    #                     self.buy_orders.append(new_buy_order)
    #
    #                 sell_price = round_to(float(check_order.get("price")) * (1 + float(config.gap_percent)), float(config.min_price))
    #
    #                 if 0 < sell_price < ask_price:
    #                     # 防止价格
    #                     sell_price = round_to(ask_price, float(config.min_price))
    #
    #                 new_sell_order = self.http_client.place_order(symbol=config.symbol, order_side=OrderSide.SELL,
    #                                                              order_type=OrderType.LIMIT, quantity=quantity,
    #                                                              price=sell_price)
    #                 if new_sell_order:
    #                     self.sell_orders.append(new_sell_order)
    #
    #             elif check_order.get('status') == OrderStatus.NEW.value:
    #                 print("sell order status is: New")
    #             else:
    #                 print(f"sell order status is not in above options: {check_order.get('status')}")
    #
    #     # 过期或者拒绝的订单删除掉.
    #     for delete_order in sell_delete_orders:
    #         self.sell_orders.remove(delete_order)
    #
    #     # 没有买单的时候.
    #     if len(self.buy_orders) <= 0:
    #         if bid_price > 0:
    #             price = round_to(bid_price * (1 - float(config.gap_percent)), float(config.min_price))
    #             buy_order = self.http_client.place_order(symbol=config.symbol,order_side=OrderSide.BUY, order_type=OrderType.LIMIT, quantity=quantity,price=price)
    #             if buy_order:
    #                 self.buy_orders.append(buy_order)
    #
    #     elif len(self.buy_orders) > int(config.max_orders): # 最多允许的挂单数量.
    #         # 订单数量比较多的时候.
    #         self.buy_orders.sort(key=lambda x: float(x['price']), reverse=False)  # 最低价到最高价
    #
    #         delete_order = self.buy_orders[0]#把最低价的买单删掉
    #         order = self.http_client.cancel_order(delete_order.get('symbol'), client_order_id=delete_order.get('clientOrderId'))
    #         if order:
    #             self.buy_orders.remove(delete_order)
    #
    #     # 没有卖单的时候.
    #     if len(self.sell_orders) <= 0:
    #         if ask_price > 0:
    #             price = round_to(ask_price * (1 + float(config.gap_percent)), float(config.min_price))
    #             order = self.http_client.place_order(symbol=config.symbol,order_side=OrderSide.SELL, order_type=OrderType.LIMIT, quantity=quantity,price=price)
    #             if order:
    #                 self.sell_orders.append(order)
    #
    #     elif len(self.sell_orders) > int(config.max_orders): # 最多允许的挂单数量.
    #         # 订单数量比较多的时候.
    #         self.sell_orders.sort(key=lambda x: x['price'], reverse=True)  # 最高价到最低价
    #
    #         delete_order = self.sell_orders[0]#把最高价的删掉
    #         order = self.http_client.cancel_order(delete_order.get('symbol'),
    #                                               client_order_id=delete_order.get('clientOrderId'))
    #         if order:
    #             self.sell_orders.remove(delete_order)
