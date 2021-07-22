# -*- coding: utf-8 -*-
'''
自己学习理解的策略
带趋势判断的多空对冲网格

对于做多网格，连续上涨时不平多（获利），连续下跌时不补仓
对于做空网格，连续下跌时不平空（获利），连续上涨时不补仓

每次获取6条五分钟(或者是其它分钟的)趋势线，0-5分钟趋势线均价大于等于1-6分钟的话，说明在下跌
每次获取6条五分钟趋势线，0-5分钟趋势线均价小于等于1-6分钟的话，说明在上涨
判断趋势后面用了mk算法

'''
import csv
import json
import os
import random
import threading
import time
import sys
sys.path.append("/home/code/mac/binance")
sys.path.append("/home/code/binance")
from cmd_receive import fc, app
from gateway import BinanceSpotHttp, OrderSide, OrderType, BinanceFutureHttp, OrderStatus

from trader.calcIndex import CalcIndex
from utils import config
from utils.config import dynamicConfig
from utils.dingding import Message


class HengedGrid(object):

    def __init__(self):
        self.http_client_spot = BinanceSpotHttp(api_key=config.api_key, secret=config.api_secret, proxy_host=config.proxy_host, proxy_port=config.proxy_port)
        self.http_client_future = BinanceFutureHttp(api_key=config.api_key_future, secret=config.api_secret_future, proxy_host=config.proxy_host, proxy_port=config.proxy_port)

        pass

    def getMoney(self):
        #test
        # with open('/home/code/binance/data/test_account.txt', 'r+', encoding='utf-8') as df:
        #     res = str(df.read())
        #     print("account money:" + res)
        #     return res
        res = self.http_client_spot.get_account_info()#现货或者合约，都是一样的接口
        if res:
            assets = res.get('balances')
            for asset in assets:
                if config.symbol.endswith(asset.get('asset')):
                    return asset.get('free')
        return 0

    def getAsset(self):
        ret = str(self.http_client_future.get_future_asset(config.symbol))
        return ret

    def set_leverage(self, leverage):
        ret = self.http_client_future.set_future_leverage(config.symbol, leverage)
        return ret['leverage']

    def addMoney(self, money):
        res = float(self.getMoney()) + float(money)
        with open('/home/code/binance/data/test_account.txt', 'w', encoding='utf-8') as df:
            df.write(str(res))
        pass

    def decreaseMoney(self, money):
        res = float(self.getMoney()) - float(money)
        with open('/home/code/binance/data/test_account.txt', 'w', encoding='utf-8') as df:
            df.write(str(res))
        pass

    def run(self):

        print("HengedGrid, run()")
        print("--------------初始准备阶段开始！---------------")
        self.getMoney()
        # while(True):

        #test
        # kline_path = '/home/code/binance/data/BTCUSDT-5m-2021-06.csv' # '/home/code/binance/data/BTCUSDT-5m-2021-06-26.csv' #mac： '/Users/zipinghuang/Downloads/binance/BTCUSDT-5m-2021-06-26.csv'
        # with open(kline_path, 'r', encoding='utf-8') as df:
            #test
            # read = csv.reader(df)
            # self.rows = [row for row in read]
            # index = CalcIndex(self.rows)
            # self.cur_market_price = self.rows[0][2]

        # official
        index = CalcIndex()

        # 取出之前存好的多单和空单的买价或者卖价，它们存储在文件里
        self.init_record_price_list()
        #获得市场价 todo，将来做多的可以改为合约做多，便于使用杠杆
        self.cur_market_spot_price = self.http_client_spot.get_latest_price(config.symbol).get('price')
        self.cur_market_future_price = self.http_client_spot.get_latest_price(config.symbol).get('price')#self.http_client_future.get_latest_price(config.symbol).get('price')
        # 设定精度，无所谓现货或者合约
        self.demical_length = len(str(self.cur_market_spot_price).split(".")[1])
        # 设定买卖数量
        quantity_basic = (fc.every_time_trade_share if fc.every_time_trade_share else 10.1) / float(self.cur_market_spot_price) if self.cur_market_spot_price else config.quantity
        self.quantity = self._format(quantity_basic)  # 买的不一定是0.0004,应该是现在的市场价买10u的份额

        # 设定仓位
        # dynamicConfig.spot_step = self.get_spot_share() #现货仓位 #self.get_step_by_position(True) #  合约
        # dynamicConfig.future_step = self.get_future_share() #self.get_step_by_position(False) 一样的
        self.set_spot_share(int(len(dynamicConfig.record_spot_price)))
        self.set_future_step(len(dynamicConfig.record_future_price))

        if self.spot_step != int(float(self.http_client_spot.get_spot_position_info(config.coin)) / float(self.quantity)):
            print(f"现货：接口中获取的仓位数不是0，但列表为空，那么说明是之前买的，或者另外手动买的，不知道均价多少了，那就告诉你仓位:{self.spot_step}，你自己处理掉吧")
        if self.future_step != self.get_step_by_position(False):
            print(f"合约空：仓位数不是0，但列表为空，那么说明是之前买的，或者另外手动买的，不知道均价多少了，那就告诉你仓位:{self.future_step}，你自己处理掉吧")

        # test check value
        # print('check account exchangeinfo: ' + str(self.http_client_spot.get_exchange_info()))  # 保留账户模拟数据
        print('check account assets spot: ' + str(self.http_client_spot.get_spot_position_info('BTC')))  # 保留账户模拟数据
        print('check account assets future: ' + str(self.http_client_future.get_future_position_info(config.symbol)))
        print('check account: ' + str(self.http_client_spot.get_account_info()))# 查询现货指定货币的仓位
        print('check market price: ' + str(round(float(self.cur_market_spot_price), 2)))
        print('check quantity: ' + str(self.quantity))

        #设置为双向持仓
        if self.http_client_future.check_position_side().get('dualSidePosition') is False:
            self.http_client_future.set_henged_position_mode()
        print('check positionSide:' + str(self.http_client_future.check_position_side()))

        # future_res = self.http_client_future.place_order('BTCUSDT', OrderSide.SELL, OrderType.MARKET, self.quantity, round(float(self.cur_market_future_price), 2), "")
        # spot_res = self.http_client_spot.place_order('BTCUSDT', OrderSide.BUY, OrderType.MARKET, quantity=self.quantity, price=round(float(self.cur_market_spot_price), 2), time_inforce="")
        # if future_res['orderId']:
        #     print("开空单成功")
        #     print(f"future_res:{future_res}")
        # print("orders:" + str(self.http_client_future.get_positionInfo('BTCUSDT')))#现货查不了
        # print("orders:" + str(self.http_client_spot.get))

        # 初始买入卖出值要自定义不灵活，不如根据当前市场价开来
        print("设置初始的盈利点数")
        self.set_ratio()
        print("设置初始的多单 空单买入卖出价格，仓位")
        self.spot_step = dynamicConfig.spot_step
        self.set_spot_price(float(self.cur_market_spot_price) if len(dynamicConfig.record_spot_price) == 0 else dynamicConfig.record_spot_price[-1])
        self.future_step = dynamicConfig.future_step
        self.set_future_price(float(self.cur_market_future_price) if len(dynamicConfig.record_future_price) == 0 else dynamicConfig.record_future_price[-1])

        ascending = True
        descending = False

        print("--------------初始准备阶段完成！---------------")

        begin_time = time.time()
        loop_count = 1
        # for kkkkk in range(0, 1):
        while(True):
            print('loop, count:' + str(loop_count))
            loop_count = loop_count + 1

            #test
        # for i in range(6, len(self.rows)):
            # print('check account: ' + str(self.getMoney()))
            # print("kline:" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(self.rows[i][0])/1000)) + ", price:" + self.rows[i][2])
            # self.cur_market_price = self.rows[i][2]

            spot_res = None
            future_res = None

            try:
                self.cur_market_spot_price = self.http_client_spot.get_latest_price(config.symbol).get('price')
                self.cur_market_future_price = self.http_client_spot.get_latest_price(config.symbol).get('price')#self.http_client_future.get_latest_price(config.symbol).get('price')

                time.sleep(0.01)
                diff_time = time.time() - begin_time
                struct_time = time.gmtime(diff_time)

                time_format = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print('now time:' + str(time_format))

                print('网格运行时间:' + str("{0}年{1}月{2}日{3}小时{4}分钟{5}秒".format(
                     struct_time.tm_year-1970,
                     struct_time.tm_mon-1,
                     struct_time.tm_mday-1,
                     struct_time.tm_hour,
                     struct_time.tm_min,
                     struct_time.tm_sec)))
                # str(self.http_client_future.get_future_asset(config.symbol))
                # print('目前杠杆:' + str(self.set_leverage(fc.leverage)))
                # tmp = self.http_client_future.get_positionInfo(config.symbol)
                # print(f"查看杠杆效果:{tmp}")
                print('check account, spot: ' + str(self.getMoney()) +', future:' + self.getAsset() + ', 目前盈利：' + str(dynamicConfig.total_earn)) #保留账户模拟数据
                print('仓位数, 多仓:' + str(self.spot_step) + ', 空仓:' + str(self.future_step))
                print('仓位具体信息, 多仓:' + str(dynamicConfig.record_spot_price) + ', 空仓:' + str(dynamicConfig.record_future_price))
                print("需要的多单买入价：" + str(self.spot_buy_price) + "，需要的多单卖出价：" + str(self.spot_sell_price) + "，目前市场价：" + str(self.cur_market_spot_price))
                print("需要的空单卖出价：" + str(self.future_sell_price) + "，需要的空单买入价：" + str(self.future_buy_price) + "，目前市场价：" + str(self.cur_market_future_price))
                # print("上涨趋势？" + str(index.calcTrend(config.symbol, "5m", True, self.demical_length, i)))

                #设定仓位
                quantity_basic = (fc.every_time_trade_share if fc.every_time_trade_share else 10.1) / float(self.cur_market_spot_price) if self.cur_market_spot_price else config.quantity
                self.quantity = self._format(quantity_basic)  # 买的不一定是0.0004,应该是现在的市场价买10u的份额

                if max(float(self.cur_market_spot_price), float(self.cur_market_future_price)) < config.min_border_price or min(float(self.cur_market_spot_price), float(self.cur_market_future_price)) > config.max_border_price:
                    print("市场价超过网格区间上下限啦")
                    time.sleep(50)
                    continue

                #开多单（买入持仓） 趋势上升时不买
                #多单市场价要低于你的买入价，才能成交
                elif float(self.cur_market_spot_price) <= float(self.spot_buy_price) and not index.calcTrend_MK(config.symbol, "5m", ascending, self.demical_length):
                    print("进入开多单流程")
                    #test
                    # spot_res = {'orderId': 'Order' + str(random.randint(1000, 10000))}
                    # dynamicConfig.order_list.append(spot_res)
                    spot_res = self.http_client_spot.place_order(config.symbol, OrderSide.BUY, OrderType.MARKET, self.quantity, price=round(float(self.cur_market_spot_price), 2), time_inforce="")
                    if spot_res['orderId']:
                        print("开多单成功")
                        Message.dingding_warn(str(self.cur_market_spot_price) + "买入一份多单了！")
                        self.decreaseMoney(float(self.cur_market_spot_price) * float(self.quantity))
                        dynamicConfig.total_invest += float(self.cur_market_spot_price) * float(self.quantity)
                        self.add_record_spot_price(self.cur_market_spot_price)
                        self.set_spot_share(self.spot_step + 1)
                        self.set_ratio()
                        self.set_spot_price(float(self.cur_market_spot_price)) #打折设置下次的买入卖出价格
                        self.save_trade_to_file(time_format, [' ' + time_format, self.cur_market_future_price, self.cur_market_future_price, "", "", ""])
                        time.sleep(0.01)
                    else:
                        print("貌似没有开多单成功，为啥：")
                        print("spot_res：" + str(spot_res))

                #平掉多单（卖出获利）趋势上升时不卖
                #多单市场价要高于你的卖出价，才能成交
                #要卖出时，市场价也要大于最近上次那个的价格，因为计算盈利的时候，要拿上次的价格来算盈利的，如果max(sell_price,market_price) < get_last_spot_price,会亏钱
                elif float(self.cur_market_spot_price) >= float(self.spot_sell_price) and float(self.cur_market_spot_price) >= float(self.get_last_spot_price()) and not index.calcTrend_MK(config.symbol, "5m", ascending, self.demical_length):
                    print("进入平多单流程")
                    if self.spot_step > 0:
                        # test
                        # spot_res = {'orderId': 'Order' + str(random.randint(1000, 10000))}
                        # dynamicConfig.order_list.append(spot_res)
                        spot_res = self.http_client_spot.place_order(config.symbol, OrderSide.SELL, OrderType.MARKET, self.quantity, price=round(float(self.cur_market_spot_price), 2),time_inforce="")
                        if spot_res['orderId']:
                            Message.dingding_warn(str(self.cur_market_spot_price) + "平掉一份多单了！")
                            print('多单卖出获利了！获得：' + str((float(self.cur_market_spot_price) - float(self.get_last_spot_price())) * float(self.quantity)) + " usdt， 卖出价格：" + str(self.cur_market_spot_price) + ", 买入的价格:" + str(self.get_last_spot_price()) + ", 买入的数量：" + str(self.quantity))
                            dynamicConfig.total_earn += (float(self.cur_market_spot_price) - float(self.get_last_spot_price())) * float(self.quantity)
                            self.remove_last_spot_price() #移除上次的价格 这个价格就是刚刚卖出的价格
                            self.addMoney(float(self.cur_market_spot_price) * float(self.quantity))
                            self.set_spot_share(self.spot_step - 1)
                            self.set_ratio()
                            self.set_spot_price(float(self.cur_market_spot_price))#卖掉之后改为上次的价格
                            #last_price = self.get_last_spot_price() #获取上次的价格
                            #self.set_spot_price(float(last_price))

                            print(str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())) + ', 目前获利：' + str(dynamicConfig.total_earn) + ", 投资总额：" + str(dynamicConfig.total_invest) + ", 多单目前仓位：" + str(self.spot_step))
                            self.save_trade_to_file(time_format, [' ' + time_format, self.cur_market_future_price, "", self.cur_market_future_price, "", ""])
                            time.sleep(0.01)
                        else:
                            print("貌似没有平多单成功，为啥：")
                            print("spot_res：" + str(spot_res))
                    else:
                        print("多单没仓位了，售罄了，平不了多单，等多单有货再说吧")
                        # self.set_spot_price(float(self.cur_market_spot_price))#没有份额啦，修改价格等待下次被买入

                #开空单（卖出借仓），趋势下跌时不买
                #空单市场价要高于你的卖出价，才能成交
                if float(self.cur_market_future_price) >= float(self.future_sell_price) and not index.calcTrend_MK(config.symbol, "5m", descending, self.demical_length):
                    print("进入开空单流程")
                    #future_res
                    # future_res= {'orderId': 'Order' + str(random.randint(1000, 10000))}
                    # dynamicConfig.order_list.append(future_res)
                    future_res = self.http_client_future.place_order(config.symbol, OrderSide.SELL, OrderType.MARKET, self.quantity, round(float(self.cur_market_future_price), 2), "")
                    if future_res['orderId']:
                        print("开空单成功")
                        Message.dingding_warn(str(self.cur_market_future_price) + "买入一份空单了！")
                        self.addMoney(float(self.cur_market_future_price) * float(self.quantity))
                        dynamicConfig.total_invest += float(self.cur_market_future_price) * float(self.quantity)
                        self.add_record_future_price(self.cur_market_future_price)#以市场价买入才划算
                        self.set_future_step(self.future_step + 1)
                        self.set_ratio()
                        self.set_future_price(float(self.cur_market_future_price))
                        self.save_trade_to_file(time_format, [' ' + time_format, self.cur_market_future_price, "", "", self.cur_market_future_price, ""])
                        time.sleep(0.01)
                    else:
                        print("貌似没有开空单成功，为啥：")
                        print("future_res：" + str(future_res))
                        # break

                #平掉空单（买入获利）下跌趋势时不买
                #空单市场价要低于你的买回价，才能成交
                #要买回时，市场价也要小于最近上次那个的价格，因为计算盈利的时候，要拿上次的价格来算盈利的，如果min(buy_price,market_price) > get_last_future_price, 会亏钱
                elif float(self.cur_market_future_price) <= float(self.future_buy_price) and float(self.cur_market_future_price) <= float(self.get_last_future_price()) and not index.calcTrend_MK(config.symbol, "5m", descending, self.demical_length):
                    print("进入平空单流程")
                    if self.future_step > 0:
                        # future_res
                        # future_res = {'orderId': 'Order' + str(random.randint(1000, 10000))}
                        # dynamicConfig.order_list.append(future_res)
                        future_res = self.http_client_future.place_order(config.symbol, OrderSide.SELL, OrderType.MARKET, self.quantity, round(float(self.cur_market_future_price), 2), "")
                        if future_res['orderId']:
                            Message.dingding_warn(str(self.cur_market_future_price) + "平掉一份空单了！")
                            self.decreaseMoney(float(self.cur_market_future_price) * float(self.quantity))
                            print('空单买回获利了！获得：' + str((float(self.get_last_future_price()) - float(self.cur_market_future_price)) * float(self.quantity)) + " usdt， 买回的价格：" + str(self.cur_market_future_price) + ", 卖出的价格:" + str(self.get_last_future_price()) + ", 买回的数量：" + str(self.quantity))
                            dynamicConfig.total_earn += (float(self.get_last_future_price()) - float(self.cur_market_future_price)) * float(self.quantity)
                            self.remove_last_future_price()
                            self.set_future_step(self.future_step - 1)
                            self.set_ratio()
                            #获取上一个价格
                            #last_price = self.get_last_future_price()
                            self.set_future_price(float(self.cur_market_future_price))
                            print(str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())) + ', 目前获利：' + str(dynamicConfig.total_earn) + ", 投资总额：" + str(dynamicConfig.total_invest) + ", 空单目前仓位：" + str(self.future_step))
                            self.save_trade_to_file(time_format, [' ' + time_format, self.cur_market_future_price, "", "", "", self.cur_market_future_price])
                            # 移除文件中的历史合约价格
                            time.sleep(0.01)
                        else:
                            print("貌似没有平掉空单成功，为啥：")
                            print("future_res：" + str(future_res))
                    else:
                        print("空单没仓位了，售罄了，平不了空单，等空单有货再说吧")
                        # self.set_future_price(float(self.cur_market_future_price))#没有仓位了就要设置补仓??

                if (spot_res is None or not spot_res['orderId']) and (future_res is None or not future_res['orderId']):
                    print("这个价格这轮没有买卖成功，开启下一轮")

                print('休息5s')
                time.sleep(5)

                # 这几个其实有点多余（未验证）
                self.spot_buy_price = dynamicConfig.spot_buy_price
                self.spot_sell_price = dynamicConfig.spot_sell_price
                self.spot_step = dynamicConfig.spot_step

                self.future_buy_price = dynamicConfig.future_buy_price
                self.future_sell_price = dynamicConfig.future_sell_price
                self.future_step = dynamicConfig.future_step

                print("----------------------------------------------------------")

            except Exception as eloop:
                print('loop时出错了！，error：' + str(eloop))
                Message.dingding_warn(str(eloop))

        print('loop结束了')
        all_invests = sum([float(tmp_spot) for tmp_spot in dynamicConfig.record_spot_price] if len(dynamicConfig.record_spot_price) > 0 else [0]) + sum([float(tmp_future) for tmp_future in dynamicConfig.record_future_price] if len(dynamicConfig.record_future_price) > 0 else [0])
        msg1 = '总结，最终收益：' + str(dynamicConfig.total_earn) + ', 所有仓位数：' + str(dynamicConfig.spot_step + dynamicConfig.future_step) + '， 目前投资额:' + str(float(all_invests) * float(self.quantity)) + '， 曾经最多投资额数：' + str(dynamicConfig.total_invest)
        msg2 = ''
        msg3 = ''
        print(msg1)
        tmp_list2 = [float(tmp) for tmp in dynamicConfig.record_spot_price] if len(dynamicConfig.record_spot_price) > 0 else [0]
        tmp_list_result2 = 0
        for ttt in tmp_list2:
            tmp_list_result2 += ttt
        if len(dynamicConfig.record_spot_price) > 0:
            msg2 = '，多单浮动盈亏：' +  str((float(self.cur_market_spot_price) - tmp_list_result2 / len(dynamicConfig.record_spot_price)) * float(self.quantity))
            print(msg2)
        tmp_list = [float(tmp) for tmp in dynamicConfig.record_future_price] if len(dynamicConfig.record_future_price) > 0 else [0]
        tmp_list_result = 0
        for ttt in tmp_list:
            tmp_list_result += ttt
        if len(dynamicConfig.record_future_price) > 0:
            msg3 = ', 空单浮动盈亏：' + str((tmp_list_result / len(dynamicConfig.record_future_price) - float(self.cur_market_future_price)) * float(self.quantity))
        Message.dingding_warn(str(msg1 + '\n' + msg2 + '\n' + msg3))
        stop_singal_from_client = False
        time.sleep(10)

    def save_trade_to_file(self, time_format, trade_info):
        try:
            record_market_price_dir = '../data/record'
            if not os.path.exists(record_market_price_dir):
                os.mkdir(record_market_price_dir)
            with open(os.path.join(record_market_price_dir, 'record_market_price_%s.csv' % time_format.split()[0]),
                      'a+', encoding='utf-8-sig') as ddf:
                writer_p = csv.writer(ddf, delimiter=',')
                if os.path.getsize(os.path.join(record_market_price_dir,
                                                'record_market_price_%s.csv' % time_format.split()[0])) == 0:
                    writer_p.writerow(['datetime', 'price', 'long_buy', 'long_sell', 'short_sell', 'short_buy'])
                writer_p.writerow(trade_info)
        except RuntimeError as ee:
            print('ee:' + str(ee))

    def set_ratio(self):
        print("set_ratio")
        ratio_24hr = round(float(self.http_client_spot.get_ticker_24hour(config.symbol)['priceChangePercent']), 1)
        if abs(ratio_24hr) > 8:
            if ratio_24hr > 0:  #上涨时，多单利润目标调大一点
                print("上涨趋势")
                dynamicConfig.rising_ratio = fc.ratio_up_or_down + self.spot_step / 2
                dynamicConfig.falling_ratio = fc.ratio_up_or_down + self.spot_step / 4
            else: #下跌时，空单利润目标调大一点
                print("下跌趋势")
                dynamicConfig.falling_ratio = fc.ratio_up_or_down + self.future_step / 2
                dynamicConfig.rising_ratio = fc.ratio_up_or_down + self.future_step / 4
        else: #震荡时
            print("震荡趋势")
            dynamicConfig.falling_ratio = fc.ratio_no_trendency + self.future_step / 4
            dynamicConfig.rising_ratio = fc.ratio_no_trendency + self.future_step / 4
        print("24小时涨跌率：ratio_24hr： " + str(ratio_24hr)
              + ", 设置上涨的比率：dynamicConfig.rising_ratio:" + str(dynamicConfig.rising_ratio)
              + ", 设置上涨的比率：dynamicConfig.falling_ratio:" + str(dynamicConfig.falling_ratio))
              # + ", 现货的仓位：self.get_spot_share():" + str(self.get_spot_share())
              # + ", 合约的仓位：self.get_future_share():" + str(self.get_future_share()))

    def add_record_spot_price(self, value):
        dynamicConfig.record_spot_price.append(value)
        dynamicConfig.record_spot_price.sort(reverse=False)
        print('record_spot_price:' + str(dynamicConfig.record_spot_price))

    def get_last_spot_price(self):
        if len(dynamicConfig.record_spot_price) == 0:
            return dynamicConfig.spot_buy_price
        return dynamicConfig.record_spot_price[-1]

    def get_last_spot_prices(self):
        return dynamicConfig.record_spot_price

    def get_last_future_prices(self):
        return dynamicConfig.record_future_price

    def remove_last_spot_price(self):
        del dynamicConfig.record_spot_price[-1]

    def add_record_future_price(self, value):
        dynamicConfig.record_future_price.append(value)
        dynamicConfig.record_spot_price.sort()
        print('record_future_price:' + str(dynamicConfig.record_future_price))

    def get_last_future_price(self):
        if len(dynamicConfig.record_future_price) == 0:
            return dynamicConfig.future_sell_price
        # else:
        #     print('sdfdfg:' + str(self.future_step) + str(dynamicConfig.record_future_price))
        return dynamicConfig.record_future_price[-1]

    def remove_last_future_price(self):
        del dynamicConfig.record_future_price[-1]

    def get_spot_share(self):
        # tmp = self.http_client.get_positionInfo(config.symbol)
        # for item in tmp:  # 多头持仓均价
        #     if item['positionSide'] == "LONG":
        #         dynamicConfig.spot_step = float(item['positionAmt'])
        #         break
        print("get_spot_share")
        #觉得应该去掉文件中没有记录价格的那部分仓位
        dynamicConfig.spot_step = int(len(dynamicConfig.record_spot_price)) #int(float(self.http_client_spot.get_spot_position_info(config.coin)) / float(self.quantity)) # 取该货币的仓位，处以每份的数量，结果为份数
        #测试时默认是0开始
        self.spot_step = dynamicConfig.spot_step
        print("get_spot_share, dynamicConfig.spot_step:" + str(dynamicConfig.spot_step), ", position:" + self.http_client_spot.get_spot_position_info(config.coin) + ", every piece quantity:" + self.quantity)
        return self.spot_step

    def set_future_step(self, future_step):
        dynamicConfig.future_step = future_step
        self.future_step = dynamicConfig.future_step
        print("设置空单仓位： " + str(self.future_step))

    def set_spot_price(self, deal_price):
        demical_point = len(str(deal_price).split(".")[1]) + 2
        dynamicConfig.spot_buy_price = round(deal_price * (1 - dynamicConfig.falling_ratio / 100), demical_point) #多单跌的时候补仓 # 保留2位小数
        dynamicConfig.spot_sell_price = round(deal_price * (1 + dynamicConfig.rising_ratio / 100), demical_point)
        self.spot_buy_price = dynamicConfig.spot_buy_price
        self.spot_sell_price = dynamicConfig.spot_sell_price
        print("设置接下来多单买入的价格, " + str(dynamicConfig.spot_buy_price) + ", dynamicConfig.rising_ratio:" + str(
            dynamicConfig.rising_ratio) + ", dynamicConfig.falling_ratio" + str(
            dynamicConfig.falling_ratio) + ", 设置接下来多单卖出的价格:" + str(dynamicConfig.spot_sell_price))

    def set_future_price(self, deal_price):
        demical_length = len(str(deal_price).split(".")[1]) + 2
        dynamicConfig.future_buy_price = round(deal_price * (1 - dynamicConfig.rising_ratio / 100), demical_length)  #空单涨的时候补仓 # 保留2位小数
        dynamicConfig.future_sell_price = round(deal_price * (1 + dynamicConfig.falling_ratio / 100), demical_length)
        self.future_sell_price = dynamicConfig.future_sell_price
        self.future_buy_price = dynamicConfig.future_buy_price
        print("设置接下来新开空单卖出的价格, " + str(dynamicConfig.future_sell_price) + ", dynamicConfig.rising_ratio:" + str(
            dynamicConfig.rising_ratio) + ", dynamicConfig.falling_ratio" + str(
            dynamicConfig.falling_ratio) + ", 设置接下来空单的买回价格:" + str(dynamicConfig.future_buy_price))

    def set_spot_share(self, spot_step):
        print("set_spot_share")
        dynamicConfig.spot_step = spot_step
        self.spot_step = dynamicConfig.spot_step
        print("设置多单仓位： " + str(self.spot_step))

    def _format(self, quantity):
        return "{:.2}".format(round(quantity, 3))

    def normal_exit(self):
        while not fc.stop_singal_from_client:
            # print(str(fc.stop_singal_from_client))
            time.sleep(1)
        msg = 'stop by myself!'
        print(msg)
        Message.dingding_warn(str(msg))
        os._exit(0)

    def open_receiver(self):
        #todo 最好还是放在另外一个进程里，方便命令调起网格策略
        app.run(host='104.225.143.245', port=5000, threaded=True)

    def get_future_share(self):
        # dynamicConfig.future_step = len(dynamicConfig.record_future_price)
        # self.future_step = dynamicConfig.future_step
        print("get_future_share, self.future_step:" + str(self.future_step))
        return self.future_step
        # tmp = self.http_client_future.get_positionInfo(config.symbol)
        # print(f"positionInfo:{tmp}")
        # for item in tmp:  # 空头持仓均价
        #     if item['positionSide'] == "SHORT":
        #         dynamicConfig.future_step = len(dynamicConfig.record_future_price) #abs(int(float(item['positionAmt']) / float(self.quantity)))
        #         self.future_step = dynamicConfig.future_step
        #         print(f"positionSide:{item['positionSide']}")
        #         print("get_future_share, dynamicConfig.future_step:" + str(dynamicConfig.future_step),
        #               ", position:" + item['positionAmt'] + ",every piece quantity:" + self.quantity)
        #         return self.future_step
        #         #测试时默认是0开始
        # return 0

    def get_step_by_position(self,direction=True):
        print(f"get_step_by_position, direction：{direction}")
        tmp = self.http_client_future.get_positionInfo(config.symbol)
        print(f"positionInfo:{tmp}")
        for item in tmp:  # 遍历所有仓位
            if direction:  # 多头持仓均价
                if item['positionSide'] == "LONG":#这是合约才有的
                    res = abs(int(float(item['positionAmt'])/float(self.quantity)))#  本来结果是负数
                    print(f"positionSide:{item['positionSide']}, positionAmt:{res}")
                    return res
            else:        # 空头持仓均价
                if item['positionSide'] == "SHORT":
                    res = abs(int(float(item['positionAmt'])/float(self.quantity)))#  为何买了空单后，positionamt为空
                    print(f"positionSide:{item['positionSide']}, positionAmt:{res}")
                    return res

    def init_record_price_list(self):
        print("init_record_price_list")
        # orders = self.http_client_spot.get_all_orders(config.symbol)
        # for order in orders:
        #     if order.get('side') == OrderSide.BUY.value and order.get('status') == OrderStatus.FILLED.value:
        #         dynamicConfig.record_spot_price.append(order.get('price'))

        with open('../data/trade_info.json', 'r') as df:
            record_price_dict_to_file = json.load(df)
            print(f"record_price_dict_to_file['record_spot_price']:{record_price_dict_to_file['record_spot_price']}")
            print(f"record_price_dict_to_file['record_future_price']:{record_price_dict_to_file['record_future_price']}")
            dynamicConfig.record_spot_price = record_price_dict_to_file['record_spot_price']
            dynamicConfig.record_future_price = record_price_dict_to_file['record_future_price']

    # def init_record_future_price_list(self):
    #     orders = self.http_client_future.get_all_orders(config.symbol)
    #     for order in orders:
    #         if order.get('positionSide') == 'SHORT' and order.get('side') == OrderSide.SELL.value and order.get('status') == OrderStatus.FILLED.value:
    #             dynamicConfig.record_future_price.append(order.get('price'))

    def save_trade_info(self):
        print("存储记录的价格到文件里")
        print(f"save_trade_info, record_spot_price:{dynamicConfig.record_spot_price}, record_future_price:{dynamicConfig.record_future_price}")
        record_price_dict_to_file = {'record_spot_price':dynamicConfig.record_spot_price, 'record_future_price':dynamicConfig.record_future_price}
        with open('../data/trade_info.json', "w") as df:
            json.dump(record_price_dict_to_file, df)




if __name__ == "__main__":
    error_raw = ''
    try:
        config.loads('../config.json')
        # dynamicConfig.loads('./config.json')

        hengedGrid = HengedGrid()
        receiver_thread = threading.Thread(target=hengedGrid.open_receiver)
        receiver_thread.start()
        exit_thread = threading.Thread(target=hengedGrid.normal_exit)
        exit_thread.start()
        hengedGrid.run()
        receiver_thread.join()
        exit_thread.join()

    except Exception as e:
        print('出现异常了:' + str(e))
        error_raw = '出现异常了:' + str(e)
    except BaseException as be:
        if isinstance(be, KeyboardInterrupt):
            print('ctrl + c 程序中断了')
            error_raw = 'ctrl + c 程序中断了' + str(be)
    finally:
        hengedGrid.save_trade_info()
        if error_raw:
            error_info = "报警：币种{coin},服务停止.错误原因{info}".format(coin=config.symbol, info=str(error_raw) + "目前盈利：")
            Message.dingding_warn(str(error_info))

