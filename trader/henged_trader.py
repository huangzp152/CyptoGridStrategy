# -*- coding: utf-8 -*-
'''
自己学习理解的策略
带趋势判断的多空对冲网格

对于做多网格，连续上涨时不平多（获利），连续下跌时不补仓
对于做空网格，连续下跌时不平空（获利），连续上涨时不补仓

每次获取6条五分钟(或者是其它分钟的)趋势线，0-5分钟趋势线均价大于等于1-6分钟的话，说明在下跌
每次获取6条五分钟趋势线，0-5分钟趋势线均价小于等于1-6分钟的话，说明在上涨

'''
import csv
import random
import time

from gateway import BinanceSpotHttp, OrderSide, OrderType
from trader.calcIndex import CalcIndex
from utils import config
from utils.config import dynamicConfig
from utils.dingding import Message

# index = CalcIndex()
class HengedGrid(object):

    def __init__(self):
        self.http_client = BinanceSpotHttp(api_key=config.api_key, secret=config.api_secret, proxy_host=config.proxy_host, proxy_port=config.proxy_port)
        pass


    def run(self):

        print("HengedGrid, run()")
        # while(True):
            #test
        kline_path = '/home/code/binance/data/BTCUSDT-5m-2021-06-26.csv' # '/home/code/binance/data/BTCUSDT-5m-2021-06-26.csv' #mac： '/Users/zipinghuang/Downloads/binance/BTCUSDT-5m-2021-06-26.csv'
        with open(kline_path, 'r', encoding='utf-8') as df:
            read = csv.reader(df)
            self.rows = [row for row in read]
            #test
            index = CalcIndex(self.rows)

            for i in range(6, len(self.rows)):
                print("kline:" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(self.rows[i][0])/1000)) + ", price:" + self.rows[i][2])
                self.cur_market_price = self.rows[i][2]
                time.sleep(0.01)
                #official
                #self.cur_market_price = self.http_client.get_latest_price(config.symbol).get('price')
                self.demical_length = len(str(self.cur_market_price).split(".")[1])
                self.quantity = self._format(config.quantity) #我看代码里quantity没有改变 #todo 这里可能要改成满足binance最低的10U的要求，如果配置文件里的数量买到的币不足10U，就要自动增加到10U

                self.spot_buy_price = dynamicConfig.spot_buy_price
                self.spot_sell_price = dynamicConfig.spot_sell_price
                self.spot_step = dynamicConfig.spot_step

                self.future_buy_price = dynamicConfig.future_buy_price
                self.future_sell_price = dynamicConfig.future_sell_price
                self.future_step = dynamicConfig.future_step
                ascending = True
                descending = False

                print("多单买入价：" + str(self.spot_buy_price) + "，多单卖出价：" + str(self.spot_sell_price) + "，市场价：" + str(self.cur_market_price))
                print("空单卖出价：" + str(self.future_sell_price) + "，空单买入价：" + str(self.future_buy_price) + "，市场价：" + str(self.cur_market_price))
                # print("上涨趋势？" + str(index.calcTrend(config.symbol, "5m", True, self.demical_length, i)))

                if float(self.cur_market_price) < config.min_border_price or float(self.cur_market_price) > config.max_border_price:
                    time.sleep(0.01)
                    continue

                #开多单（买入持仓） 趋势上升时不买
                #多单市场价要低于你的买入价，才能成交
                elif float(self.cur_market_price) <= float(self.spot_buy_price) and not index.calcTrend(config.symbol, "5m", ascending, self.demical_length, i):
                    #test
                    spot_res = {'orderId': 'Order' + str(random.randint(1000, 10000))}
                    dynamicConfig.order_list.append(spot_res)
                    #res = self.http_client.place_order(config.symbol, OrderSide.BUY, OrderType.Market, self.quantity, "")
                    if spot_res['orderId']:
                        print("开多单成功")
                        dynamicConfig.total_invest += float(self.cur_market_price) * float(config.quantity)
                        self.set_spot_share(self.spot_step + 1)
                        self.set_ratio()
                        self.add_record_spot_price(self.cur_market_price)#以市场价买入才划算
                        self.set_spot_price(float(self.cur_market_price)) #打折设置下次的买入卖出价格
                        time.sleep(0.01)
                    else:
                        break
                #平掉多单（卖出获利）趋势上升时不卖
                #多单市场价要高于你的卖出价，才能成交
                elif float(self.cur_market_price) >= float(self.spot_sell_price) and float(self.cur_market_price) > float(self.get_last_spot_price()) and not index.calcTrend(config.symbol, "5m", ascending, self.demical_length, i):

                    if self.spot_step > 0:
                        # test
                        spot_res = {'orderId': 'Order' + str(random.randint(1000, 10000))}
                        dynamicConfig.order_list.append(spot_res)
                        # spot_res = self.http_client.place_order(config.symbol, OrderSide.SELL, OrderType.MARKET, self.quantity, "")

                        if spot_res['orderId']:
                            print('多单卖出获利了！获得：' + str((float(self.cur_market_price) - float(self.get_last_spot_price())) * float(self.quantity)) + " usdt， 卖出价格："+ str(self.cur_market_price) + ", 买入的价格:" + str(self.get_last_spot_price()) + ", 买入的数量：" + str(self.quantity))
                            dynamicConfig.total_earn += (float(self.cur_market_price) - float(self.get_last_spot_price())) * float(self.quantity)
                            print(str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())) + ', 目前获利：' + str(dynamicConfig.total_earn) + ", 投资总额：" + str(dynamicConfig.total_invest) + ", 多单目前仓位：" + str(self.spot_step))
                            self.set_ratio()
                            last_price = self.get_last_spot_price() #获取上次的价格
                            self.set_spot_price(float(last_price)) #卖掉之后改为上次的价格
                            self.set_spot_share(self.spot_step - 1)  # 卖掉之后仓位 -1 改为从线上拿
                            self.remove_last_spot_price() #移除上次的价格
                            time.sleep(0.01)
                        else:
                            break
                    else:
                        print("多单没仓位了，平不了多单")
                    #     self.set_spot_price(float(self.cur_market_price))#没有份额啦，修改价格等待下次被买入

                #开空单（卖出借仓），趋势下跌时不买
                #空单市场价要高于你的卖出价，才能成交
                elif float(self.cur_market_price) >= float(self.future_sell_price) and not index.calcTrend(config.symbol, "5m", descending, self.demical_length, i):

                    #future_res
                    future_res= {'orderId': 'Order' + str(random.randint(1000, 10000))}
                    dynamicConfig.order_list.append(future_res)
                    # future_res = self.http_client.place_order(config.symbol, OrderSide.SELL, OrderType.Market, self.quantity, "")

                    if future_res['orderId']:
                        print("开空单成功")
                        dynamicConfig.total_invest += float(self.cur_market_price) * float(config.quantity)
                        self.set_future_step(self.future_step + 1)
                        self.set_ratio()
                        self.add_record_future_price(self.cur_market_price)#以市场价买入才划算
                        self.set_future_price(float(self.cur_market_price))
                        time.sleep(0.01)
                    else:
                        break

                #平掉空单（买入获利）下跌趋势时不买
                #空单市场价要低于你的买回价，才能成交
                elif float(self.cur_market_price) <= float(self.future_buy_price) and float(self.cur_market_price) < float(self.get_last_future_price()) and not index.calcTrend(config.symbol, "5m", descending, self.demical_length, i):

                    if self.future_step > 0:
                        # future_res
                        future_res = {'orderId': 'Order' + str(random.randint(1000, 10000))}
                        # future_res = self.http_client.place_order(config.symbol, OrderSide.BUY, OrderType.Market, self.quantity, "")
                        dynamicConfig.order_list.append(future_res)
                        if future_res['orderId']:
                            print('空单买回获利了！获得：' + str((float(self.get_last_future_price()) - float(self.cur_market_price)) * float(self.quantity)) + " usdt， 买回的价格：" + str(self.cur_market_price) + ", 卖出的价格:" + str(self.get_last_future_price()) + ", 买回的数量：" + str(self.quantity))
                            dynamicConfig.total_earn += (float(self.get_last_future_price()) - float(self.cur_market_price)) * float(self.quantity)
                            print(str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())) + ', 目前获利：' + str(dynamicConfig.total_earn) + ", 投资总额：" + str(dynamicConfig.total_invest) + ", 空单目前仓位：" + str(self.future_step))
                            self.set_ratio()
                            #获取上一个价格
                            last_price = self.get_last_future_price()
                            self.set_future_price(float(last_price))
                            self.set_future_step(self.future_step - 1)
                            self.remove_last_future_price()
                            # 移除文件中的历史合约价格
                            time.sleep(0.01)
                        else:
                            break
                    else:
                        print("空单没仓位了，平不了空单")
                    #     self.set_future_price(float(self.cur_market_price))#没有仓位了就要设置补仓??
                else:
                    print("这个价格这轮没有买卖成功，开启下一轮")
                print("----------------------------------------------------------")
        # time.sleep(2)

    def set_ratio(self):
        print("set_ratio")
        ratio_24hr = round(float(self.http_client.get_ticker_24hour(config.symbol)['priceChangePercent']), 1)

        if abs(ratio_24hr) > 3.65:
            if ratio_24hr > 0:  #上涨时，多单利润目标调大一点
                print("上涨趋势")
                dynamicConfig.rising_ratio = 1 + self.get_spot_share() / 2
                dynamicConfig.falling_ratio = 1 + self.get_spot_share() / 4
            else: #下跌时，空单利润目标调大一点
                print("下跌趋势")
                dynamicConfig.falling_ratio = 1 + self.get_future_share() / 2
                dynamicConfig.rising_ratio = 1 + self.get_future_share() / 4
        else: #震荡时
            print("震荡趋势")
            dynamicConfig.falling_ratio = 0.5 + self.get_future_share() / 4
            dynamicConfig.rising_ratio = 0.5 + self.get_future_share() / 4
        print("ratio_24hr, " + str(ratio_24hr) + ", dynamicConfig.rising_ratio:" + str(dynamicConfig.rising_ratio) + ", dynamicConfig.falling_ratio:" + str(dynamicConfig.falling_ratio) + ", self.get_spot_share():" + str(self.get_spot_share()) + ", self.get_future_share():" + str(self.get_future_share()))

    def add_record_spot_price(self, value):
        dynamicConfig.record_spot_price.append(value)

    def get_last_spot_price(self):
        if len(dynamicConfig.record_spot_price) == 0:
            return dynamicConfig.spot_buy_price
        return dynamicConfig.record_spot_price[self.spot_step - 1]

    def get_last_spot_prices(self):
        return dynamicConfig.record_spot_price

    def get_last_future_prices(self):
        return dynamicConfig.record_future_price

    def remove_last_spot_price(self):
        del dynamicConfig.record_spot_price[-1]

    def add_record_future_price(self, value):
        dynamicConfig.record_future_price.append(value)

    def get_last_future_price(self):
        if len(dynamicConfig.record_future_price) == 0:
            return dynamicConfig.future_sell_price
        else:
            print('sdfdfg:' + str(self.future_step) + str(dynamicConfig.record_future_price))
            return dynamicConfig.record_future_price[self.future_step - 1]

    def remove_last_future_price(self):
        del dynamicConfig.record_future_price[-1]

    def get_spot_share(self):
        # tmp = self.http_client.get_positionInfo(config.symbol)
        # for item in tmp:  # 多头持仓均价
        #     if item['positionSide'] == "LONG":
        #         dynamicConfig.spot_step = float(item['positionAmt'])
        #         break
        #测试时默认是0开始
        return dynamicConfig.spot_step

    def set_future_step(self, future_step):
        dynamicConfig.future_step = future_step
        print("设置空单仓位： " + str(dynamicConfig.future_step))

    def get_future_share(self):
        # tmp = self.http_client.get_positionInfo(config.symbol)
        # for item in tmp:  # 空头持仓均价
        #     if item['positionSide'] == "SHORT":
        #         dynamicConfig.future_step = float(item['positionAmt'])
        #         break
        #测试时默认是0开始
        return dynamicConfig.future_step

    def set_spot_price(self, deal_price):
        demical_point = len(str(deal_price).split(".")[1]) + 2
        dynamicConfig.spot_buy_price = round(deal_price * (1 - dynamicConfig.falling_ratio / 100), demical_point) #多单跌的时候补仓 # 保留2位小数
        dynamicConfig.spot_sell_price = round(deal_price * (1 + dynamicConfig.rising_ratio / 100), demical_point)
        print("设置接下来多单买入的价格, " + str(dynamicConfig.spot_buy_price) + ", dynamicConfig.rising_ratio:" + str(
            dynamicConfig.rising_ratio) + ", dynamicConfig.falling_ratio" + str(
            dynamicConfig.falling_ratio) + ", 设置接下来多单卖出的价格:" + str(dynamicConfig.spot_sell_price))

    def set_future_price(self, deal_price):
        demical_length = len(str(deal_price).split(".")[1]) + 2
        dynamicConfig.future_buy_price = round(deal_price * (1 - dynamicConfig.rising_ratio / 100), demical_length)  #空单涨的时候补仓 # 保留2位小数
        dynamicConfig.future_sell_price = round(deal_price * (1 + dynamicConfig.falling_ratio / 100), demical_length)
        print("设置接下来新开空单卖出的价格, " + str(dynamicConfig.future_sell_price) + ", dynamicConfig.rising_ratio:" + str(
            dynamicConfig.rising_ratio) + ", dynamicConfig.falling_ratio" + str(
            dynamicConfig.falling_ratio) + ", 设置接下来空单的买回价格:" + str(dynamicConfig.future_buy_price))


    def set_spot_share(self, spot_step):
        dynamicConfig.spot_step = spot_step
        print("设置多单仓位： " + str(dynamicConfig.spot_step))

    def _format(self, price):
        return "{:.6f}".format(price)

if __name__ == "__main__":
    try:
        config.loads('../config.json')
        # dynamicConfig.loads('./config.json')
        hengedGrid = HengedGrid()
        hengedGrid.run()
    except Exception as e:
        error_info = "报警：币种{coin},服务停止.错误原因{info}".format(coin=config.symbol, info=str(e))
        Message.dingding_warn(error_info)
    pass
