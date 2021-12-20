# -*- coding: utf-8 -*-
"""
自己学习理解的策略
带趋势判断的多空对冲网格

对于做多网格，连续上涨时不平多（获利），连续下跌时不补仓
对于做空网格，连续下跌时不平空（获利），连续上涨时不补仓

每次获取6条五分钟(或者是其它分钟的)趋势线，0-5分钟趋势线均价大于等于1-6分钟的话，说明在下跌
每次获取6条五分钟趋势线，0-5分钟趋势线均价小于等于1-6分钟的话，说明在上涨
判断趋势后面用了mk算法

"""
import csv
import json
import os
import random
import threading
import time
import sys

import numpy as np

import requests
import zipfile

sys.path.append("/home/code/mac/binance")
sys.path.append("/home/code/binance")
from cmd_receive_uni import fc, app
from gateway import BinanceSpotHttp, OrderSide, OrderType, BinanceFutureHttp, OrderStatus

from trader.calcIndex import CalcIndex
from utils.config_uni import config, dynamicConfig
from utils.dingding import Message


class HengedGrid(object):

    def __init__(self):
        api_key = ''
        api_secret = ''
        if config.platform == 'binance_future_testnet':
            api_key = config.api_key_future_testnet
            api_secret = config.api_secret_future_testnet
        else:
            api_key = config.api_key_future
            api_secret = config.api_secret_future

        self.http_client_spot = BinanceSpotHttp(api_key=api_key, secret=api_secret, proxy_host=config.proxy_host, proxy_port=config.proxy_port)
        self.http_client_future = BinanceFutureHttp(api_key=api_key, secret=api_secret, proxy_host=config.proxy_host, proxy_port=config.proxy_port)

        self.leverage = 1
        self.grid_side = fc.position_side
        self.long_bottom_position_share = fc.long_bottom_position_share
        self.cut_position_threshold = fc.cut_position_threshold
        self.open_spot_price = 99999
        self.open_future_price = 1
        self.long_buy_ratio_scale = fc.long_buy_ratio_scale
        self.crazy_buy = fc.crazy_buy
        self.open_trend_trade = fc.open_trend_trade
        self.handling_ratio = 0.0008 # u本位买卖都是0.04%的手续费
        self.gross_profit = 9.01
        self.grid_run_time = ""
        self.end_martin_grid = fc.end_martin_grid
        self.current_all_spot_quantity = 0.0
        self.current_all_future_quantity = 0.0
        self.is_mac = True
        self.computer_path_base = '/Users/zipinghuang/Downloads/binance/CyptoGridStrategy/' if self.is_mac else 'G:\\PersonalFiles\\binance_grid_trader-master\\'
        pass

    def getMoney(self):
        if config.platform == 'test':
            with open(self.computer_path_base + 'data/test_account.txt', 'r+', encoding='utf-8') as df:
                res = str(df.read())
                print("backtest account money:" + res)
                return res
        else:
            res = self.http_client_spot.get_account_info(config.symbol)#现货或者合约，都是一样的接口
            if res:
                assets = res.get('balances')# future : assets
                for asset in assets:
                    if config.symbol.endswith(asset.get('asset')):
                        return asset.get('free')
            return 0

    def getAsset(self):
        ret = self.http_client_spot.get_spot_position_info(config.coin)
        print('ret:' + str(ret))
        return ret

    def set_leverage(self, leverage):
        ret = self.http_client_future.set_future_leverage(config.symbol, leverage)
        # print('set_leverage:' + str(ret))
        return ret['leverage']

    def addMoney(self, money):
            res = float(self.getMoney()) + float(money)
            if config.platform == 'test':
                with open(self.computer_path_base + 'data/test_account_%s_test.txt' % config.symbol, 'w', encoding='utf-8') as df:
                    df.write(str(res))

    def decreaseMoney(self, money):
        res = float(self.getMoney()) - float(money)
        if config.platform == 'test':
            with open(self.computer_path_base + 'data/test_account_%s_test.txt' % config.symbol, 'w', encoding='utf-8') as df:
                df.write(str(res))

    def loop_one_ratio(self):
        index = CalcIndex()
        # 取出之前存好的多单和空单的买价或者卖价，它们存储在文件里
        if config.platform == 'test':
            pass
        else:
            self.init_record_price_list()
        # 获得市场价 todo，将来做多的可以改为合约做多，便于使用杠杆
        # self.cur_market_spot_price = self.http_client_spot.get_latest_price(config.symbol).get('price')
        self.cur_market_future_price = self.rows[config.symbol][0][
            4] if config.platform == "test" else self.http_client_spot.get_latest_price(config.symbol).get(
            'price')  # self.http_client_future.get_latest_price(config.symbol).get('price')
        # 设定精度，无所谓现货或者合约
        self.demical_length = len(str(self.cur_market_future_price).split(".")[1])
        # 设定买卖数量
        quantity_basic = round((fc.every_time_trade_share / float(self.cur_market_future_price)), 3)
        self.quantity = self._format(quantity_basic)
        self.current_all_spot_quantity = self.quantity
        self.current_all_future_quantity = self.quantity
        # 设定仓位
        # dynamicConfig.spot_step = self.get_spot_share() #现货仓位 #self.get_step_by_position(True) #  合约
        # dynamicConfig.future_step = self.get_future_share() #self.get_step_by_position(False) 一样的
        self.set_spot_share(int(len(dynamicConfig.record_spot_price)))
        self.set_future_step(len(dynamicConfig.record_future_price))

        # if self.spot_step != int(float(self.http_client_spot.get_future_position_info(config.symbol)) / float(self.quantity)):
        #     print(f"现货：接口中获取的仓位数不是0，但列表为空，那么说明是之前买的，或者另外手动买的，不知道均价多少了，那就告诉你仓位:{self.spot_step}，你自己处理掉吧")
        # if self.future_step != self.get_step_by_position(False):
        #     print(f"合约空：仓位数不是0，但列表为空，那么说明是之前买的，或者另外手动买的，不知道均价多少了，那就告诉你仓位:{self.future_step}，你自己处理掉吧")

        # test check value
        # print('check account exchangeinfo: ' + str(self.http_client_spot.exchangeInfo(config.symbol)))  # 保留账户模拟数据
        # print('check account assets spot: ' + str(self.http_client_spot.get_future_position_info(config.symbol)))  # 保留账户模拟数据
        # print('check account assets future: ' + str(self.http_client_future.get_future_asset(config.symbol)))
        # print('check account: ' + str(self.http_client_spot.get_account_info(config.symbol)))# 查询现货指定货币的仓位
        print('check market price: ' + str(round(float(self.cur_market_future_price), 2)))
        print('check quantity: ' + str(self.quantity))

        # 设置为双向持仓
        # if self.http_client_future.check_position_side().get('dualSidePosition') is False:
        #     self.http_client_future.set_henged_position_mode()
        # print('check positionSide:' + str(self.http_client_future.check_position_side()))

        # future_res = self.http_client_future.place_order('BTCUSDT', OrderSide.SELL, OrderType.MARKET, self.quantity, round(float(self.cur_market_future_price), 2), "")
        # spot_res = self.http_client_spot.place_order('BTCUSDT', OrderSide.BUY, OrderType.MARKET, quantity=self.quantity, price=round(float(self.cur_market_spot_price), 2), time_inforce="")
        # if future_res['orderId']:
        #     print("开空单成功")
        #     print(f"future_res:{future_res}")
        # print("orders:" + str(self.http_client_future.get_positionInfo('BTCUSDT')))#现货查不了
        # print("orders:" + str(self.http_client_spot.get))
        # self.leverage = str(self.set_leverage(fc.leverage))
        # print('目前杠杆:' + self.leverage)
        print("设置初始的盈利点数")
        if self.grid_side == 'LONG':
            self.set_spot_ratio()
        elif self.grid_side == 'SHORT':
            self.set_future_ratio()
        else:
            self.set_spot_ratio()
            self.set_future_ratio()
        print("设置初始的多单 空单买入卖出价格，仓位")
        self.spot_step = dynamicConfig.spot_step
        self.set_spot_next_buy_price(float(
            self.cur_market_future_price))  # if len(dynamicConfig.record_spot_price) == 0 else float(dynamicConfig.record_spot_price[-1]))
        self.set_spot_next_sell_price(float(self.cur_market_future_price))
        self.future_step = dynamicConfig.future_step
        self.set_future_next_sell_price(float(
            self.cur_market_future_price))  # if len(dynamicConfig.record_future_price) == 0 else float(dynamicConfig.record_future_price[-1]))
        self.set_future_next_buy_price(float(self.cur_market_future_price))
        self.spot_money = float(self.getMoney()) if config.platform == 'test' else float(self.getAsset())
        self.ease_position_share = fc.ease_position_share

        ascending = True
        descending = False

        print("--------------初始准备阶段完成！---------------")

        begin_time = time.time()
        self.last_get_profit_time = begin_time
        loop_count = 1
        # for kkkkk in range(0, 1):

        time_format = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print('now time:' + str(time_format))
        diff_time = time.time() - begin_time
        struct_time = time.gmtime(diff_time)

        self.grid_run_time = '网格运行时间:' + str("{0}年{1}月{2}日{3}小时{4}分钟{5}秒".format(
            struct_time.tm_year - 1970,
            struct_time.tm_mon - 1,
            struct_time.tm_mday - 1,
            struct_time.tm_hour,
            struct_time.tm_min,
            struct_time.tm_sec))
        print(self.grid_run_time)

        # print("把上次存下来的卖掉一部分")
        # self.close_previous_position(time_format)

        # print("等待是寂寞的，所以开仓时先分别开一个空单和多单")
        # if self.grid_side == 'BOTH':
        #     self.open_long(time_format)
        #     self.open_short(time_format)
        # elif self.grid_side == 'LONG':
        #     self.open_long(time_format)
        # elif self.grid_side == 'SHORT':
        #     self.open_short(time_format)

        # time.sleep(5)

        has_report = False

        #
        # for i in range(0, len(rows)):
        #     print("cur_market_price:" + str(rows[i][4]))

        while not fc.stop_singal_from_client or (True if (config.platform == 'test' and loop_count < len(self.rows[config.symbol])) else False):
            print('loop, count:' + str(loop_count))
            # test
            # for i in range(6, len(self.rows)):
            # print('check account: ' + str(self.getMoney()))
            # print("kline:" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(self.rows[i][0])/1000)) + ", price:" + self.rows[i][2])
            # self.cur_market_price = self.rows[i][2]

            spot_res = None
            spot_open_long_res = None
            future_res = None

            try:
                # self.cur_market_spot_price = self.http_client_spot.get_latest_price(config.symbol).get('price')

                time.sleep(0.01)
                diff_time = time.time() - begin_time
                struct_time = time.gmtime(diff_time)

                time_format = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print('now time:' + str(time_format))

                self.grid_run_time = '网格运行时间:' + str("{0}年{1}月{2}日{3}小时{4}分钟{5}秒".format(
                    struct_time.tm_year - 1970,
                    struct_time.tm_mon - 1,
                    struct_time.tm_mday - 1,
                    struct_time.tm_hour,
                    struct_time.tm_min,
                    struct_time.tm_sec))
                print(self.grid_run_time)
                # str(self.http_client_future.get_future_asset(config.symbol))
                # tmp = self.http_client_future.get_positionInfo(config.symbol)
                # print(f"查看杠杆效果:{tmp}")
                # print("看交易记录：" + str(self.http_client_future.get_my_trades(config.symbol)))
                try:
                    self.spot_money = float(self.getMoney()) if config.platform == 'test' else float(self.getAsset())
                except Exception as e:
                    print('exception:' + str(e))
                    time.sleep(5)
                    continue
                # print('check account: ' + str(self.getAsset()))
                self.gross_profit = str(round(float(dynamicConfig.total_earn) / float(self.spot_money) * 100, 2)) + '%'
                msg1 = '目前盈利：' + str(dynamicConfig.total_earn) + (
                            '(每小时：' + str(round(dynamicConfig.total_earn / float(diff_time / 3600), 2)) + ')') if float(
                    diff_time / 3600) != 0 else ''
                msg2 = '目前网格套利数：' + str(dynamicConfig.total_earn_grids) + ', 网格利润率：' + self.gross_profit + (
                            '(每小时：' + str(
                        round(float(dynamicConfig.total_earn) / float(self.spot_money) / float(diff_time / 3600) * 100,
                              2)) + '%)') if float(diff_time / 3600) != 0 else ''
                msg3 = '网格浮动盈亏, 多单：' + str(
                    sum([(float(self.cur_market_future_price) - float(tmp)) * float(self.quantity) for tmp in
                         dynamicConfig.record_spot_price])) + ', 空单：' + str(
                    sum([(float(tmp) - float(self.cur_market_future_price)) * float(self.quantity) for tmp in
                         dynamicConfig.record_future_price]))
                msg4 = '总仓位数:' + str(dynamicConfig.total_steps) + ', 多仓:' + str(self.spot_step) + ', 空仓:' + str(
                    self.future_step) + ', 底仓：' + str(len(dynamicConfig.long_bottom_position_price))
                msg5 = '仓位具体信息, 多仓:' + str(dynamicConfig.record_spot_price) + ', 空仓:' + str(
                    dynamicConfig.record_future_price) + ', 底仓：' + str(
                    dynamicConfig.long_bottom_position_price) + '(' + str(
                    self.get_long_bottom_position_scale()) + '), 阈值：' + str(fc.long_bottom_position_share)

                # if struct_time.tm_min == 0 or struct_time.tm_min == 30:
                print(msg1)  # 保留账户模拟数据
                print(msg2)
                print(msg3)
                print(msg4)
                print(msg5)

                # 判断一下趋势(做多拉升时or做空暴跌时，认为趋势来了)
                symbol_to_check_trend = config.symbol
                if symbol_to_check_trend.endswith('BUSD'):
                    symbol_to_check_trend = symbol_to_check_trend.replace('BUSD',
                                                                          'USDT')  # 因为遇到过BTCBUSD调用kline返回的结果不变的bug 应该是接口问题导致的
                if fc.position_side == 'LONG':
                    isTrendComing = False  # index.calcTrend_MK(symbol_to_check_trend, "5m", ascending, self.demical_length)
                elif fc.position_side == 'SHORT':
                    isTrendComing = index.calcTrend_MK(symbol_to_check_trend, "5m", descending, self.demical_length)
                else:
                    isTrendComing = False
                self.cur_market_future_price = self.rows[config.symbol][loop_count][
                    4] if config.platform == 'test' else self.http_client_spot.get_latest_price(config.symbol).get(
                    'price')  # self.http_client_future.get_latest_price(config.symbol).get('price')
                loop_count = loop_count + 1

                msg6 = "目前【市场价】：" + str(self.cur_market_future_price)
                # self.quantity = self._format(round(fc.every_time_trade_share / float(dynamicConfig.record_spot_price[-1]), 3)) if len(dynamicConfig.record_spot_price) > 0 else self._format(round(fc.every_time_trade_share / self.cur_market_future_price, 3))
                # msg7 = "开仓数量：" + str(self.quantity * pow(1.01, len(dynamicConfig.record_spot_price) + 1))
                # msg8 = "平仓数量：" + str(self.quantity * pow(1.01, len(dynamicConfig.record_spot_price)))
                print(msg6)
                # print(msg7)
                # print(msg8)

                # 清仓操作
                if len(dynamicConfig.record_spot_price) > 0:
                    spot_lost_ratio = (float(dynamicConfig.record_spot_price[0]) - float(
                        self.cur_market_future_price)) / float(dynamicConfig.record_spot_price[0])
                    if spot_lost_ratio > self.cut_position_threshold:
                        msg = '要清掉一份仓位，不然要容易爆仓'
                        print(msg)
                        self.open_spot_price = dynamicConfig.record_spot_price[0]
                        self.close_long(time_format, True, self.cur_market_future_price)
                        Message.dingding_warn(msg + ', 这份止损了:' + str(self.open_spot_price))
                        del dynamicConfig.record_spot_price[0]
                    else:
                        print('最亏的那份多单损益:' + str(spot_lost_ratio))

                position_delta = min(len(dynamicConfig.record_spot_price) - self.ease_position_share,
                                     len(dynamicConfig.record_future_price) - self.ease_position_share)
                if len(dynamicConfig.record_spot_price) == len(dynamicConfig.record_future_price) and len(
                        dynamicConfig.record_spot_price) > self.ease_position_share and len(
                        dynamicConfig.record_future_price) > self.ease_position_share:
                    msg = '减少多空持仓数量，卖掉' + str(self.ease_position_share) + '份'
                    print(msg)
                    for i in range(0, position_delta):
                        self.close_long(time_format, True, self.cur_market_future_price)
                        Message.dingding_warn('这份多单平掉了:' + str(dynamicConfig.record_spot_price[i]))
                        self.close_short(time_format, True, self.cur_market_future_price)
                        Message.dingding_warn('这份空单平掉了:' + str(dynamicConfig.record_future_price[i]))
                        del dynamicConfig.record_spot_price[i]
                        del dynamicConfig.record_future_price[i]

                if len(dynamicConfig.record_future_price) > 0:
                    future_lost_ratio = (float(self.cur_market_future_price) - float(
                        dynamicConfig.record_future_price[0])) / float(dynamicConfig.record_future_price[0])
                    if future_lost_ratio > self.cut_position_threshold:
                        msg = '要清掉一份仓位，不然要容易爆仓'
                        print(msg)
                        self.open_future_price = dynamicConfig.record_future_price[0]
                        self.close_short(time_format, True, self.cur_market_future_price)
                        Message.dingding_warn(msg + ', 这份止损了:' + str(self.open_future_price))
                        del dynamicConfig.record_future_price[0]
                    else:
                        print('最亏的那份空单损益:' + str(future_lost_ratio))

                # 开仓资金占总资金1/3以上走马丁
                # occupied_share = sum([float(dynamicConfig.record_spot_price[i]) * 1.01 * (i + 1) * self.quantity for i in range(0, len(dynamicConfig.record_spot_price))])
                # total_share =occupied_share + self.spot_money
                # isMartin = False if (occupied_share / total_share) > 1/3 else False

                isMartin = True if len(dynamicConfig.record_spot_price) <= self.end_martin_grid else False
                tag = '【马丁】' if isMartin else '【网格】'
                msg7 = ''
                msg8 = ''
                if self.grid_side == 'LONG':
                    msg7 = "下一份多单买入价：" + str(self.spot_buy_price) + "，这份【多单卖出价】" + str(tag) + "：" + str(
                        self.spot_sell_price)
                    print(msg7)
                elif self.grid_side == "SHORT":
                    msg8 = "下一份空单卖出价：" + str(self.future_sell_price) + "，这份【空单买入价】：" + str(self.future_buy_price)
                    print(msg8)
                else:
                    msg7 = "下一份多单买入价：" + str(self.spot_buy_price) + "，这份【多单卖出价】" + str(tag) + "：" + str(
                        self.spot_sell_price)
                    msg8 = "下一份空单卖出价：" + str(self.future_sell_price) + "，这份【空单买入价】：" + str(self.future_buy_price)
                    print(msg7)
                    print(msg8)

                if loop_count % 1800 == 5:  # 半小时汇报一次
                    msg = '【' + str(
                        config.symbol) + '】' + '汇报脚本运行情况：' + msg1 + ', ' + msg2 + ', ' + msg3 + ', ' + msg4 + ', ' + msg5 + ', ' + msg6 + ', ' + msg7 + ', ' + msg8 + ', ' + self.grid_run_time
                    Message.dingding_warn(msg)

                # 设定仓位
                # quantity_basic = (fc.every_time_trade_share if fc.every_time_trade_share else 10.1) / float(self.cur_market_future_price) if self.cur_market_future_price else config.quantity
                # self.quantity = self._format(quantity_basic)  # 买的不一定是0.0004,应该是现在的市场价买10u的份额
                # spot_res = None
                # future_res = None

                # if max(float(self.cur_market_future_price), float(self.cur_market_future_price)) < config.min_border_price or min(float(self.cur_market_future_price), float(self.cur_market_future_price)) > config.max_border_price:
                #     print("市场价超过网格区间上下限啦")
                #     time.sleep(50)
                # el
                # if isTrendComing:
                #     print('趋势来了，多仓空仓拿好，不买不卖')
                #     time.sleep(10)
                # else:

                # 开多单（买入持仓）
                # 多单市场价要低于你的买入价，才能成交
                if not isTrendComing and float(self.cur_market_future_price) <= float(
                        self.spot_buy_price) and not self.nearly_full_position():
                    if not self.long_bottom_position_full() or self.need_join_in_long_bottom_position_price(
                            self.cur_market_future_price):
                        spot_open_long_res = self.build_long_bottom_position(self.cur_market_future_price, time_format)
                    # if not spot_open_long_res:#不需要建仓
                    spot_res = self.open_long(time_format)  # 不管是否建仓，都要买一份

                # 平掉多单（卖出获利）
                # 多单市场价要高于你的卖出价，才能成交
                # 要卖出时，市场价也要大于最近上次那个的价格，因为计算盈利的时候，要拿上次的价格来算盈利的，如果max(sell_price,market_price) < get_last_spot_price,会亏钱 # 可能高位的单需要留着，因为还没到它的目标止盈点
                elif not isTrendComing and float(self.cur_market_future_price) >= float(self.spot_sell_price) * (
                        1 + self.handling_ratio):
                    spot_res = self.close_long(time_format, False, self.cur_market_future_price)

                # 开空单（卖出借仓）
                # 空单市场价要高于你的卖出价，才能成交
                if not isTrendComing and float(self.cur_market_future_price) >= float(
                        self.future_sell_price) and not self.nearly_full_position():
                    future_res = self.open_short(time_format)

                # 平掉空单（买入获利）
                # 空单市场价要低于你的买回价，才能成交
                # 要买回时，市场价也要小于最近上次那个的价格，因为计算盈利的时候，要拿上次的价格来算盈利的，如果min(buy_price,market_price) > get_last_future_price, 会亏钱 # 可能高位的单需要留着，因为还没到它的目标止盈点
                elif not isTrendComing and float(self.cur_market_future_price) <= float(self.future_buy_price) * (
                        1 + self.handling_ratio):
                    future_res = self.close_short(time_format, False, self.cur_market_future_price)

                if (spot_res is None or not 'orderId' in spot_res.keys()) and (
                        future_res is None or not 'orderId' in future_res.keys()):
                    print("这个价格这轮没有买卖成功，开启下一轮")
                    self.save_trade_to_file(time_format,
                                            [' ' + time_format, self.cur_market_future_price, "", "", "", ""])
                elif self.crazy_buy and spot_open_long_res and not (future_res and 'orderId' in future_res.keys()):
                    # 走这里的话，会在同一价位一直买一直买，建议低位时把self.crazy_buy设置为True
                    # 因为狂买模式不要一直触发不然会爆仓，所以还是在建底仓的时候做
                    msg = "进入狂买模式了"
                    Message.dingding_warn(msg)
                    # print("这个价格建仓了，目前仓位列表：" + str(dynamicConfig.long_bottom_position_price) + ", 底仓仓位比例：" + str(self.get_long_bottom_position_scale()))
                else:
                    # 多单或者空单开单成功后，均需要修改整体双向的买卖价格
                    # 修改价格应在所有流程结束之后做，否则在多单开完之后立马修改所有的价格的话，这时候空单就平不了了
                    # 差异化的多空区间网格，所以多空单格子利润要为不一致
                    if spot_res:
                        self.set_ratio_and_price('spot_res')
                    if future_res:
                        self.set_ratio_and_price('future_res')
                    # self.set_spot_price(float(self.cur_market_future_price))
                    # self.set_future_price(float(self.cur_market_future_price))

                print('休息5s')
                if config.platform == 'test':
                    pass
                else:
                    time.sleep(5)

                # 这几个其实有点多余（未验证）
                # self.spot_buy_price = dynamicConfig.spot_buy_price
                # self.spot_sell_price = dynamicConfig.spot_sell_price
                self.spot_step = dynamicConfig.spot_step

                # self.future_buy_price = dynamicConfig.future_buy_price
                # self.future_sell_price = dynamicConfig.future_sell_price
                self.future_step = dynamicConfig.future_step

                print("----------------------------------------------------------")

            except Exception as eloop:
                print('loop时出错了！，error：' + str(eloop))
                Message.dingding_warn(str(eloop))
                break

        print('loop结束了')
        all_invests = sum([float(tmp_spot) for tmp_spot in dynamicConfig.record_spot_price] if len(
            dynamicConfig.record_spot_price) > 0 else [0]) + sum(
            [float(tmp_future) for tmp_future in dynamicConfig.record_future_price] if len(
                dynamicConfig.record_future_price) > 0 else [0])
        msg1 = '总结，最终收益：' + str(dynamicConfig.total_earn) + ', 所有仓位数：' + str(
            dynamicConfig.spot_step + dynamicConfig.future_step) + '， 目前投资额:' + str(
            float(all_invests) * float(self.quantity)) + '， 曾经最多投资额数：' + str(
            dynamicConfig.total_invest) + self.grid_run_time
        msg2 = ''
        msg3 = ''
        print(msg1)
        tmp_list2 = [float(tmp) for tmp in dynamicConfig.record_spot_price] if len(
            dynamicConfig.record_spot_price) > 0 else [0]
        tmp_list_result2 = 0
        for ttt in tmp_list2:
            tmp_list_result2 += ttt
        if len(dynamicConfig.record_spot_price) > 0:
            msg2 = '，多单浮动盈亏：' + str(
                (float(self.cur_market_future_price) - tmp_list_result2 / len(dynamicConfig.record_spot_price)) * float(
                    self.quantity))
            print(msg2)
        tmp_list = [float(tmp) for tmp in dynamicConfig.record_future_price] if len(
            dynamicConfig.record_future_price) > 0 else [0]
        tmp_list_result = 0
        for ttt in tmp_list:
            tmp_list_result += ttt
        if len(dynamicConfig.record_future_price) > 0:
            msg3 = ', 空单浮动盈亏：' + str((tmp_list_result / len(dynamicConfig.record_future_price) - float(
                self.cur_market_future_price)) * float(self.quantity))
        Message.dingding_warn(str(msg1 + '\n' + msg2 + '\n' + msg3))
        stop_singal_from_client = False
        if config.platform == 'test':
            backtest_result = str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(
                int(self.rows[config.symbol][0][0][:-3])))) + ', 交易对:' + config.symbol + '回测结果：' + "格子利率：" + str(
                round(dynamicConfig.spot_rising_ratio, 2)) + '最终收益：' + str(round(dynamicConfig.total_earn, 2)) + '格子数量：' + str(len(dynamicConfig.record_spot_price)) + ', 最多投资额：' + str(all_invests)
            print(backtest_result)
            dynamicConfig.total_earn = 0
            dynamicConfig.record_spot_price = []
            all_invests = 0
            with open(self.computer_path_base + 'backtest/backtest_result.txt', 'a+') as df:
                df.write(backtest_result + '\n')

    def run(self):

        print("HengedGrid, run()")
        print("--------------初始准备阶段开始！---------------")
        self.getMoney()
        # while(True):

        self.rows = {}
        symbol_list = ['UNIBUSD', 'BTCBUSD', 'ETHBUSD']
        if config.platform == 'test':
              # 交易对范围
            for m in range(0, len(symbol_list)):
                self.rows[symbol_list[m]] = []
                for k in range(-1, -5, -1):
                    timestamp = time.time() + 86400 * k
                    date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)).split(' ')[0]
                    base_url = 'https://data.binance.vision/data/spot/daily/klines/' + symbol_list[m] + '/1m/'
                    kline_path = base_url + symbol_list[m] + '-1m-' + date + '.zip'
                    file_name = kline_path.split('/')[-1]
                    r = requests.get(kline_path, stream=True)
                    save_path = self.computer_path_base + 'backtest/' + file_name
                    with open(save_path, 'wb') as wb:
                        for trunk in r.iter_content(128):
                            wb.write(trunk)
                    is_zipfile = zipfile.is_zipfile(save_path)
                    if is_zipfile:
                        fz = zipfile.ZipFile(save_path, 'r')
                        for file in fz.namelist():
                            fz.extract(file, self.computer_path_base + 'backtest/')
                        # os.remove(save_path)
                        with open(save_path.replace('.zip', '.csv'), 'r', encoding='utf-8') as df:
                            read = csv.reader(df)
                            tmp = [row for row in read]
                            print("self.rowasdas")
                            self.rows[symbol_list[m]].extend(tmp)
                            print("self.row len:" + str(len(self.rows[symbol_list[m]])))

            # with requests.Session() as s:
            #     download = s.get(kline_path)
            #     with open('/Users/zipinghuang/Downloads/' + file_name.replace('zip', 'csv'), 'r',
            #               encoding='utf-8') as df:
            #         reader = csv.reader(download.content.decode('gbk').splitlines(), delimiter=',')
            #         tmp = list(reader)

                # decoded_content = download.content.decode('utf-8')
                # cr = csv.reader(decoded_content.splitlines(), delimiter=',')
                # tmp = list(cr)
                # self.rows.extend(tmp)

            # with open('/Users/zipinghuang/Downloads/' + file_name.replace('zip', 'csv'), 'wb') as w:
            #     w.write(r.content.decode('utf-8'))
            # with open('/Users/zipinghuang/Downloads/' + file_name.replace('zip', 'csv'), 'r', encoding='utf-8') as df:
            #     test
                # read = csv.reader(df)
                # tmp = [row for row in read]
                # self.rows.append(tmp)
                # print("self.row len:" + str(len(self.rows)))
                # time.sleep(5)
            # index = CalcIndex(self.rows)

        # official
        if config.platform != 'test':
            self.loop_one_ratio()
        else:
        #test
            ratio_list = np.arange(0.3, 1.6, 0.1)# 利率范围
            martin_list = np.arange(6, 26, 5) # 马丁格子数范围
            # for i in range(0, 10, 1/10):
            #     ratio_list.append(i)
            print(str(ratio_list))
            time.sleep(10)
            for l in range(0, len(symbol_list)):
                with open(self.computer_path_base + 'backtest/backtest_result.txt',
                          'a+') as dfout:
                    dfout.write(str(symbol_list[l]) + '交易对' + '\n')
                    if config.platform == 'test':
                        config.symbol = symbol_list[l]
                for j in range(0, len(martin_list)):# 前多少为马丁
                    with open(self.computer_path_base + 'backtest/backtest_result.txt', 'a+') as dfout:
                        dfout.write('前' + str(martin_list[j]) + '格为马丁' + '\n')
                    if config.platform == 'test':
                        self.end_martin_grid = martin_list[j]
                    for i in range(0, len(ratio_list)):
                        if config.platform == 'test':
                            fc.ratio_up_or_down = ratio_list[i]
                            fc.ratio_no_trendency = ratio_list[i]
                        self.loop_one_ratio()

                        # time.sleep(5)

    def set_ratio_and_price(self, set_side = ''):
        self.set_spot_ratio()
        self.set_future_ratio()
        if set_side == '':
            self.set_spot_next_buy_price(float(self.cur_market_future_price))#, float(self.get_last_spot_price())))#考虑列表价格的话，拉升后，要跌很多才能开仓；不考虑的话，有可能同个价位附近有很多仓位
            self.set_spot_next_sell_price(float(self.cur_market_future_price))#, float(self.get_last_spot_price())))
            self.set_future_next_buy_price(float(self.cur_market_future_price))#, float(self.get_last_future_price())))
            self.set_future_next_sell_price(float(self.cur_market_future_price))#, float(self.get_last_future_price())))
        elif set_side == 'spot_res':
            self.set_spot_next_buy_price(float(self.cur_market_future_price))#, float(self.get_last_spot_price())))#考虑列表价格的话，拉升后，要跌很多才能开仓；不考虑的话，有可能同个价位附近有很多仓位
            self.set_spot_next_sell_price(float(self.cur_market_future_price))#, float(self.get_last_spot_price())))
        elif set_side == 'future_res':
            self.set_future_next_buy_price(float(self.cur_market_future_price))#, float(self.get_last_future_price())))
            self.set_future_next_sell_price(float(self.cur_market_future_price))#, float(self.get_last_future_price())))
        self.adjust_prices()


    def nearly_full_position(self):
        return False
        # if float(((sum(dynamicConfig.record_spot_price) if len(dynamicConfig.record_spot_price) > 0 else 0) + float(sum(dynamicConfig.record_future_price) if len(dynamicConfig.record_future_price) > 0 else 0)) * self.quantity) / (float(self.spot_money) * int(self.leverage)) >= 0.95:
        #     print('9成5仓位了，只平仓不开仓了')
        #     time.sleep(10)
        #     return True
        # return False

    def open_long(self, time_format, build_position_share = False):
        spot_res = {}
        if self.grid_side == 'SHORT':
            spot_res['orderId'] = 'virtual'
            return spot_res

        print("进入开多单流程")
        # test
        # spot_res = {'orderId': 'Order' + str(random.randint(1000, 10000))}
        # dynamicConfig.order_list.append(spot_res)
        isMartin = True if len(dynamicConfig.record_spot_price) <= self.end_martin_grid else False
        quantity = float(self.quantity) * pow(1.5, len(dynamicConfig.record_spot_price)+1) if isMartin else float(self.quantity)
        print('quantity::' + str(quantity))
        spot_res = {'orderId':'backtestid'} if config.platform == 'test' else self.http_client_spot.place_order(config.symbol, OrderSide.BUY, OrderType.LIMIT, quantity, price=str(round(float(self.cur_market_future_price), 2)))
        # print('开多单完整结果：'+str(spot_res))
        if spot_res and 'orderId' in spot_res.keys():
            print("开多单成功")
            self.decreaseMoney(float(self.cur_market_future_price) * quantity)
            dynamicConfig.total_invest += float(self.cur_market_future_price) * quantity
            if not build_position_share:
                Message.dingding_warn('【' + str(config.symbol) + '】' + str(self.cur_market_future_price) + "买入一份多单了！")
                self.add_record_spot_price(self.cur_market_future_price)
                self.set_spot_share(self.spot_step + 1)
                dynamicConfig.total_steps += 1
            else:
                Message.dingding_warn('【' + str(config.symbol) + '】' + str(self.cur_market_future_price) + "【建仓】买入一份多单了！")
            # self.set_spot_ratio()
            # self.set_spot_next_sell_price(float(self.cur_market_future_price))
            # self.set_spot_next_buy_price(float(self.cur_market_future_price))
            # self.set_spot_price(float(self.cur_market_future_price))  # 打折设置下次的买入卖出价格
            # self.set_future_price(float(self.cur_market_future_price)) # 开多单成功后，空单的买入卖出价格要下调，不然价格上涨时，空单难成交
            self.save_trade_to_file(time_format, [' ' + time_format, self.cur_market_future_price, self.cur_market_future_price, "", "", ""])
            return spot_res
        else:
            print("貌似没有开多单成功，为啥：")
            print("spot_res：" + str(spot_res))

    def close_long(self, time_format, cut_position = False, price='none', tickOutBottom = False):
        if self.grid_side == 'SHORT':
            if float(self.cur_market_future_price) <= self.get_last_spot_price():
                print("亏本的买卖不做，不平了")
                return {}
        print("进入平多单流程")
        spot_res = {}
        isMartin = True if len(dynamicConfig.record_spot_price) <= self.end_martin_grid else False
        if self.spot_step > (0 if tickOutBottom else (1 if isMartin else 0)):
            # test
            # spot_res = {'orderId': 'Order' + str(random.randint(1000, 10000))}
            # dynamicConfig.order_list.append(spot_res)
            order_type = OrderType.LIMIT
            time_inforce = ''
            if price != 'none':
                order_type = OrderType.LIMIT
                time_inforce = "GTC"
            tag = '【马丁】' if isMartin else '【网格】'
            current_average_spot_price = sum([float(item) for item in dynamicConfig.record_spot_price]) / len(dynamicConfig.record_spot_price)
            self.current_all_spot_quantity = self.quantity * (1.5 * (1 - pow(1.5, len(dynamicConfig.record_spot_price)-1))/ (1 - 1.5) if ((len(dynamicConfig.record_spot_price) > 1) and isMartin) else 1)
            open_spot_price = current_average_spot_price if isMartin else self.get_last_spot_price()
            spot_quantity = self.current_all_spot_quantity if isMartin else self.quantity
            print("self.end_martin_grid:" +str(self.end_martin_grid) + ", len(dynamicConfig.record_spot_price):" + str(len(dynamicConfig.record_spot_price)) + ", " + tag + "current_average_spot_price:" + str(current_average_spot_price) + ", self.current_all_spot_quantity:" + str(self.current_all_spot_quantity) + ", spot_quantity:" + str(spot_quantity) + ", open_spot_price:" + str(open_spot_price) + "， price：" + str(price))
            spot_res = {'orderId':'backtestid'} if config.platform == 'test' else self.http_client_spot.place_order(config.symbol, OrderSide.SELL, order_type, self.quantity if tickOutBottom is True else float(spot_quantity), price=str(price))
            if order_type == OrderType.LIMIT and tickOutBottom is True:
                print('price:' + price + ' 挂平仓多单了')
                return {}
            if spot_res and 'orderId' in spot_res.keys():
                dynamicConfig.total_earn += (float(self.cur_market_future_price) - float(
                    open_spot_price)) * float(spot_quantity)
                dynamicConfig.total_earn_grids += (self.spot_step - 1) if isMartin else 1
                self.addMoney(float(self.cur_market_future_price) * float(spot_quantity))
                self.set_spot_share(1 if isMartin else (self.spot_step - 1))
                dynamicConfig.total_steps -= (self.spot_step - 1) if isMartin else 1
                self.gross_profit = str(round(float(dynamicConfig.total_earn) / float(self.spot_money) * 100, 2)) + '%'
                if not cut_position:
                    if isMartin:
                        self.remove_except_first_spot_price()
                        self.change_first_spot_record_price(str(open_spot_price))
                    else:
                        self.remove_last_spot_price()  # 移除上次的价格 这个价格就是刚刚卖出的价格


                # self.set_spot_ratio()
                # self.set_spot_next_buy_price(float(self.cur_market_future_price))
                # self.set_spot_next_sell_price(float(self.cur_market_future_price))


                # self.set_spot_price(float(self.cur_market_future_price))  # 卖掉之后改为上次的价格
                # last_price = self.get_last_spot_price() #获取上次的价格
                # self.set_spot_price(float(last_price))

                print(str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())) + ', 目前获利：' + str(
                    dynamicConfig.total_earn) + ", 投资总额：" + str(dynamicConfig.total_invest) + ", 多单目前仓位：" + str(
                    self.spot_step))
                self.save_trade_to_file(time_format, [' ' + time_format, self.cur_market_future_price, "",
                                                      self.cur_market_future_price, "", ""])

                last_get_profit_time_struct = time.gmtime(time.time() - self.last_get_profit_time)
                self.last_get_profit_time_delta = '距离上一次套利有多久了:' + str("{0}日{1}小时{2}分钟{3}秒".format(
                    last_get_profit_time_struct.tm_mday - 1,
                    last_get_profit_time_struct.tm_hour,
                    last_get_profit_time_struct.tm_min,
                    last_get_profit_time_struct.tm_sec))

                # Message.dingding_warn('【' + str(config.symbol) + '】' + str(self.cur_market_future_price) + "平掉一份多单了！")
                msg = tag + '【' + str(config.symbol) + '】多单卖出获利了！获得：' + str(round((float(self.cur_market_future_price) - open_spot_price) * float(spot_quantity), 2)) + "， 卖出价格：" + str(self.cur_market_future_price) + ", 买入的价格:" + str(open_spot_price
                    ) + ", 买入的数量：" + str(spot_quantity) + ', 目前总获利：' + str(round(dynamicConfig.total_earn, 2)) + ', 总格子数：' + str(int(dynamicConfig.total_earn_grids)) + ', 利润率：' + self.gross_profit + ', 多仓:' + str(self.spot_step) + ', 空仓:' + str(self.future_step) + ', 仓位具体信息, 多仓:' + str(dynamicConfig.record_spot_price) + ', 空仓:' + str(dynamicConfig.record_future_price) + ', 底仓：' + str(dynamicConfig.long_bottom_position_price) + ', (' + str(self.get_long_bottom_position_scale()) + '), 阈值：' + str(fc.long_bottom_position_share) + ', ' + self.grid_run_time + ', ' + self.last_get_profit_time_delta
                print(msg)
                Message.dingding_warn(msg)
                self.last_get_profit_time = time.time()
                return spot_res
            else:
                print("貌似没有平多单成功，为啥：")
                print("spot_res：" + str(spot_res))
        elif self.grid_side == 'SHORT':
            spot_res['orderId'] = 'virtual'
            return spot_res
        else:
            print("多单没仓位了，售罄了，平不了多单，等多单有货再说吧")
            if isMartin and len(dynamicConfig.record_spot_price) == 1:
                print("多单，马丁剩下一份了，keep着")
            self.save_trade_to_file(time_format, [' ' + time_format, self.cur_market_future_price, "", "", "", ""])
            # self.set_spot_price(float(self.cur_market_future_price))#没有份额啦，修改价格等待下次被买入
            #但价格要改的
            spot_res['orderId'] = 'virtual'
            return spot_res

    def open_short(self, time_format):
        future_res = {}
        if self.grid_side == 'LONG':
            future_res['orderId'] = 'virtual'
            return future_res
        print("进入开空单流程")
        # future_res
        # future_res= {'orderId': 'Order' + str(random.randint(1000, 10000))}
        # dynamicConfig.order_list.append(future_res)
        isMartin = True if len(dynamicConfig.record_future_price) <= self.end_martin_grid else False
        quantity = float(self.quantity) * pow(1.5, len(dynamicConfig.record_future_price) + 1) if isMartin else float(self.quantity)
        future_res = self.http_client_future.place_order(config.symbol, OrderSide.SELL, "SHORT", OrderType.MARKET, quantity, round(float(self.cur_market_future_price), 2),"")

        if future_res and 'orderId' in future_res.keys():
            print("开空单成功")
            Message.dingding_warn('【' + str(config.symbol) + '】' + str(self.cur_market_future_price) + "买入一份空单了！")
            self.addMoney(float(self.cur_market_future_price) * quantity)
            dynamicConfig.total_invest += float(self.cur_market_future_price) * quantity
            self.add_record_future_price(self.cur_market_future_price)  # 以市场价买入才划算
            self.set_future_step(self.future_step + 1)
            dynamicConfig.total_steps += 1
            # self.set_future_ratio()
            # self.set_future_next_buy_price(float(self.cur_market_future_price))
            # self.set_future_next_sell_price(float(self.cur_market_future_price))
            # self.set_spot_price(float(self.cur_market_future_price))#开空单成功后，多单的买入卖出价格要上调，不然价格回落时，多单难成交
            # self.set_future_price(float(self.cur_market_future_price))
            self.save_trade_to_file(time_format, [' ' + time_format, self.cur_market_future_price, "", "",
                                                  self.cur_market_future_price, ""])
            return future_res
        else:
            print("貌似没有开空单成功，为啥：")
            print("future_res：" + str(future_res))
            # break



    def close_short(self, time_format, cut_position=False, price='none'):
        if self.grid_side == 'LONG':
            if float(self.cur_market_future_price) >= self.get_last_future_price():
                print("亏本的买卖不做，不平了")
                return {}
        print("进入平空单流程")
        future_res = {}
        isMartin = True if len(dynamicConfig.record_future_price) <= self.end_martin_grid else False
        if self.future_step > (1 if isMartin else 0):
            # future_res
            # future_res = {'orderId': 'Order' + str(random.randint(1000, 10000))}
            # dynamicConfig.order_list.append(future_res)
            order_type = OrderType.MARKET
            time_inforce = ''
            if price != 'none':
                order_type = OrderType.LIMIT
                time_inforce = "GTC"
            tag = '【马丁】' if isMartin else '【网格】'
            current_average_future_price = sum([float(item) for item in dynamicConfig.record_future_price]) / len(dynamicConfig.record_future_price)
            open_future_price = current_average_future_price if isMartin else self.get_last_future_price()
            self.current_all_spot_quantity = self.quantity * (1.5 * (1 - pow(1.5, len(dynamicConfig.record_future_price) - 1)) / (1 - 1.5) if ((len(dynamicConfig.record_future_price) > 1) and isMartin) else 1)
            future_quantity = self.current_all_future_quantity if isMartin else self.quantity
            print("current_average_future_price:" + str(current_average_future_price) + ", self.current_all_future_quantity:" + str(self.current_all_future_quantity) + ", future_quantity:" + str(future_quantity) + ", open_future_price:" + str(open_future_price))
            future_res = self.http_client_future.place_order(config.symbol, OrderSide.BUY, "SHORT", order_type, future_quantity, price, time_inforce)
            if order_type == OrderType.LIMIT:
                print('price:' + price + '挂平仓空单了')
                # return {}
            if future_res and 'orderId' in future_res.keys():
                # Message.dingding_warn('【' + str(config.symbol) + '】' + str(self.cur_market_future_price) + "平掉一份空单了！")
                self.decreaseMoney(float(self.cur_market_future_price) * float(future_quantity))
                dynamicConfig.total_earn += (float(open_future_price) - float(self.cur_market_future_price)) * float(future_quantity)
                dynamicConfig.total_earn_grids += (self.future_step - 1) if isMartin else 1
                self.gross_profit = str(round(float(dynamicConfig.total_earn) / float(self.spot_money) * 100, 2)) + '%'
                if not cut_position:
                    if isMartin:
                        self.remove_except_first_future_price()
                        self.change_first_spot_record_price(str(open_future_price))
                    else:
                        self.remove_last_future_price()

                self.set_future_step(1 if isMartin else (self.future_step - 1))
                dynamicConfig.total_steps -= (self.future_step - 1) if isMartin else 1
                # self.set_future_ratio()
                # self.set_future_next_buy_price(float(self.cur_market_future_price))
                # self.set_future_next_sell_price(float(self.cur_market_future_price))
                # 获取上一个价格
                # last_price = self.get_last_future_price()
                # self.set_future_price(float(self.cur_market_future_price))
                print(str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())) + ', 目前获利：' + str(
                    dynamicConfig.total_earn) + ", 投资总额：" + str(dynamicConfig.total_invest) + ", 空单目前仓位：" + str(
                    self.future_step))
                self.save_trade_to_file(time_format, [' ' + time_format, self.cur_market_future_price, "", "", "",
                                                      self.cur_market_future_price])
                print('check time.time() - self.last_get_profit_time：' + str(time.time() - self.last_get_profit_time))
                last_get_profit_time_struct = time.gmtime(time.time() - self.last_get_profit_time)
                self.last_get_profit_time_delta = '距离上一次套利有多久了:' + str("{0}日{1}小时{2}分钟{3}秒".format(
                    last_get_profit_time_struct.tm_mday - 1,
                    last_get_profit_time_struct.tm_hour,
                    last_get_profit_time_struct.tm_min,
                    last_get_profit_time_struct.tm_sec))

                msg = tag + '【' + str(config.symbol) + '】空单买回获利了！获得：' + str(round((float(open_future_price) - float(self.cur_market_future_price)) * float(
                        self.quantity),2)) + " usdt， 买回的价格：" + str(self.cur_market_future_price) + ", 卖出的价格:" + str(
                    open_future_price) + ", 买回的数量：" + str(future_quantity) + ', 目前总获利：' + str(dynamicConfig.total_earn) + ', 总格子数：' + str(int(dynamicConfig.total_earn_grids)) + ', 利润率：' + self.gross_profit + ', 多仓:' + str(self.spot_step) + ', 空仓:' + str(self.future_step) + ', 仓位具体信息, 多仓:' + str(dynamicConfig.record_spot_price) + ', 空仓:' + str(dynamicConfig.record_future_price) + ', 底仓：' + str(dynamicConfig.long_bottom_position_price) + ', (' + str(self.get_long_bottom_position_scale()) + '), 阈值：' + str(fc.long_bottom_position_share) + ', ' + self.grid_run_time + ', ' + self.last_get_profit_time_delta
                print(msg)
                Message.dingding_warn(msg)
                self.last_get_profit_time = time.time()
                return future_res
            else:
                print("貌似没有平掉空单成功，为啥：")
                print("future_res：" + str(future_res))
        elif self.grid_side == 'LONG':
            future_res['orderId'] = 'virtual'
            return future_res
        else:
            print("空单没仓位了，售罄了，平不了空单，等空单有货再说吧")
            if isMartin and len(dynamicConfig.record_future_price) == 1:
                print("空单，马丁剩下一份了，keep着")
            self.save_trade_to_file(time_format, [' ' + time_format, self.cur_market_future_price, "", "", "", ""])
            # self.set_future_price(float(self.cur_market_future_price))#没有仓位了就要设置补仓??
            future_res['orderId'] = 'virtual'
            return future_res

    def save_trade_to_file(self, time_format, trade_info):
        pass
        #太费空间了
        # try:
        #     record_market_price_dir = '../data/record'
        #     if not os.path.exists(record_market_price_dir):
        #         os.mkdir(record_market_price_dir)
        #     with open(os.path.join(record_market_price_dir, 'record_market_price_%s_%s.csv' % (time_format.replace(' ', '-'),  config.symbol)),
        #               'a+', encoding='utf-8-sig') as ddf:
        #         writer_p = csv.writer(ddf, delimiter=',')
        #         if os.path.getsize(os.path.join(record_market_price_dir,
        #                                         'record_market_price_%s_%s.csv' % (time_format.replace(' ', '-'), config.symbol))) == 0:
        #             writer_p.writerow(['datetime', 'price', 'long_buy', 'long_sell', 'short_sell', 'short_buy'])
        #         writer_p.writerow(trade_info)
        # except Exception as ee:
        #     print('ee:' + str(ee))



    def set_spot_ratio(self):
        '''
        设置买入卖出的比率
        todo 仓位越多，格子要越大，防止不断地开仓或平仓, 实现起来有点复杂
        '''
        print("set_spot_ratio")
        if config.platform == 'test':
            ratio_24hr = 5
        else:
            ratio_24hr = round(float(self.http_client_spot.get_ticker_24hour(config.symbol)['priceChangePercent']), 1)
        if abs(ratio_24hr) > 6:
                print("24小时上涨或下跌趋势")
                dynamicConfig.spot_rising_ratio = fc.ratio_up_or_down# + dynamicConfig.total_steps / 4
                dynamicConfig.spot_falling_ratio = fc.ratio_up_or_down# + dynamicConfig.total_steps / 4
        else: #震荡时
            print("24小时震荡趋势")
            dynamicConfig.spot_falling_ratio = fc.ratio_no_trendency# + dynamicConfig.total_steps / 8
            dynamicConfig.spot_rising_ratio = fc.ratio_no_trendency# + dynamicConfig.total_steps / 8
        print("24小时涨跌率：ratio_24hr： " + str(ratio_24hr)
              + ", 设置多单上涨的比率：dynamicConfig.spot_rising_ratio:" + str(dynamicConfig.spot_rising_ratio)
              + ", 设置多单下跌的比率：dynamicConfig.spot_falling_ratio:" + str(dynamicConfig.spot_falling_ratio))
              # + ", 现货的仓位：self.get_spot_share():" + str(self.get_spot_share())
              # + ", 合约的仓位：self.get_future_share():" + str(self.get_future_share()))

    def set_future_ratio(self):
        '''
        设置买入卖出的比率
        todo 仓位越多，格子要越大，防止不断地开仓或平仓, 实现起来有点复杂
        '''
        print("set_future_ratio")
        ratio_24hr = 5 if config.platform == 'test' else round(float(self.http_client_spot.get_ticker_24hour(config.symbol)['priceChangePercent']), 1)
        if abs(ratio_24hr) > 6:
                print("24小时上涨或下跌趋势")
                dynamicConfig.future_rising_ratio = fc.ratio_up_or_down / fc.long_buy_ratio_scale# + dynamicConfig.total_steps / 4
                dynamicConfig.future_falling_ratio = fc.ratio_up_or_down / fc.long_buy_ratio_scale# + dynamicConfig.total_steps / 4
        else: #震荡时
            print("24小时震荡趋势")
            dynamicConfig.future_falling_ratio = fc.ratio_no_trendency / fc.long_buy_ratio_scale# + dynamicConfig.total_steps / 8
            dynamicConfig.future_rising_ratio = fc.ratio_no_trendency / fc.long_buy_ratio_scale# + dynamicConfig.total_steps / 8
        print("24小时涨跌率：ratio_24hr： " + str(ratio_24hr)
              + ", 设置空单上涨的比率：dynamicConfig.future_rising_ratio:" + str(dynamicConfig.future_rising_ratio)
              + ", 设置空单下跌的比率：dynamicConfig.future_falling_ratio:" + str(dynamicConfig.future_falling_ratio))
              # + ", 现货的仓位：self.get_spot_share():" + str(self.get_spot_share())
              # + ", 合约的仓位：self.get_future_share():" + str(self.get_future_share()))

    def add_record_spot_price(self, value):
        dynamicConfig.record_spot_price.append(value)
        print('record_spot_price:' + str(dynamicConfig.record_spot_price))
        dynamicConfig.record_spot_price.sort(reverse=True)#降序
        self.save_trade_info()

    def get_last_spot_price(self):
        if len(dynamicConfig.record_spot_price) == 0:
            return float(dynamicConfig.spot_buy_price)
        return float(dynamicConfig.record_spot_price[-1])

    def get_last_spot_prices(self):
        return dynamicConfig.record_spot_price

    def get_last_future_prices(self):
        return dynamicConfig.record_future_price

    def remove_last_spot_price(self):
        del dynamicConfig.record_spot_price[-1]
        self.save_trade_info()

    def remove_except_first_spot_price(self):
        del dynamicConfig.record_spot_price[1:]
        self.save_trade_info()

    def change_first_spot_record_price(self, first_record_price):
        dynamicConfig.record_spot_price[0] = first_record_price

    def change_first_future_record_price(self, first_record_price):
        dynamicConfig.record_future_price[0] = first_record_price

    def add_record_future_price(self, value):
        dynamicConfig.record_future_price.append(value)
        dynamicConfig.record_future_price.sort()
        print('record_future_price:' + str(dynamicConfig.record_future_price))
        self.save_trade_info()

    def get_last_future_price(self):
        if len(dynamicConfig.record_future_price) == 0:
            return float(dynamicConfig.future_sell_price)
        # else:
        #     print('sdfdfg:' + str(self.future_step) + str(dynamicConfig.record_future_price))
        return float(dynamicConfig.record_future_price[-1])

    def remove_last_future_price(self):
        del dynamicConfig.record_future_price[-1]
        self.save_trade_info()

    def remove_except_first_future_price(self):
        del dynamicConfig.record_future_price[1:]
        self.save_trade_info()

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
        # print("get_spot_share, dynamicConfig.spot_step:" + str(dynamicConfig.spot_step), ", position:" + self.http_client_spot.get_future_position_info(config.symbol) + ", every piece quantity:" + self.quantity)
        return self.spot_step

    def set_future_step(self, future_step):
        dynamicConfig.future_step = future_step
        self.future_step = dynamicConfig.future_step
        print("设置空单仓位： " + str(self.future_step))

    def set_spot_next_buy_price(self, deal_price):
        price_str_list = str(deal_price).split(".")
        demical_point = len(price_str_list[1]) if len(price_str_list) > 1 else 0 + 2
        # dynamicConfig.spot_buy_price = round(min(float(dynamicConfig.record_future_price[-1]) if len(dynamicConfig.record_future_price) > 0 and self.grid_side == 'BOTH' else 999999, deal_price * (1 - dynamicConfig.spot_falling_ratio / 100)), demical_point)  # 多单跌的时候补仓 # 保留2位小数
        dynamicConfig.spot_buy_price = round(deal_price * (1 - dynamicConfig.spot_falling_ratio / 100), demical_point)  # 多单跌的时候补仓 # 保留2位小数
        self.spot_buy_price = dynamicConfig.spot_buy_price
        # print("设置接下来多单买入的价格, " + str(self.spot_buy_price))

    def set_spot_next_sell_price(self, deal_price):
        price_str_list = str(deal_price).split(".")
        demical_point = len(price_str_list[1]) if len(price_str_list) > 1 else 0 + 2
        if self.end_martin_grid > 0 and len(dynamicConfig.record_spot_price) > 0 and len(dynamicConfig.record_spot_price) <= self.end_martin_grid:
            print("execute martin stragety")
            self.spot_sell_price = max(round(deal_price * (1 + dynamicConfig.spot_rising_ratio / 100), demical_point), (round(sum([float(item) for item in dynamicConfig.record_spot_price]) / len(dynamicConfig.record_spot_price) * (1 + dynamicConfig.spot_rising_ratio / 100), demical_point)) if len(dynamicConfig.record_spot_price) > 0 else self.spot_sell_price)
            dynamicConfig.spot_sell_price = self.spot_sell_price
            print("self.spot_sell_price：" + str(self.spot_sell_price))
            # self.quantity = self.quantity * (len(dynamicConfig.record_spot_price) - 1) # 留一份
        else:
            dynamicConfig.spot_sell_price = round(deal_price * (1 + dynamicConfig.spot_rising_ratio / 100), demical_point)
            self.spot_sell_price = max(dynamicConfig.spot_sell_price, (float(dynamicConfig.record_spot_price[-1]) if len(dynamicConfig.record_spot_price) > 0 else 0)) # 如果多单平仓价比列表里最小的还小，那交易时就亏本了啊
            print("[ss]设置接下来多单卖出的价格:" + str(self.spot_sell_price))

    def set_future_next_sell_price(self, deal_price):
        price_str_list = str(deal_price).split(".")
        demical_point = len(price_str_list[1]) if len(price_str_list) > 1 else 0 + 2
        dynamicConfig.future_sell_price = round(deal_price * (1 + dynamicConfig.future_falling_ratio / 100), demical_point)
        self.future_sell_price = dynamicConfig.future_sell_price
        # print("设置接下来新开空单卖出的价格, " + str(self.future_sell_price))

    def set_future_next_buy_price(self, deal_price):
        price_str_list = str(deal_price).split(".")
        demical_point = len(price_str_list[1]) if len(price_str_list) > 1 else 0 + 2
        if self.end_martin_grid > 0 and len(dynamicConfig.record_future_price) > 0 and len(dynamicConfig.record_future_price) <= self.end_martin_grid:
            print("execute martin stragety")
            self.future_buy_price = min(round(deal_price * (1 - dynamicConfig.future_rising_ratio / 100), demical_point), (round(sum([float(item) for item in dynamicConfig.record_future_price]) / len(dynamicConfig.record_future_price) * (1 - dynamicConfig.future_rising_ratio / 100), demical_point)) if len(dynamicConfig.record_future_price) > 0 else self.future_buy_price)
            dynamicConfig.future_buy_price = self.future_buy_price
            # self.current_all_future_quantity = self.quantity * (len(dynamicConfig.record_future_price) - 1)  # 留一份
        else:
            dynamicConfig.future_buy_price = round(deal_price * (1 - dynamicConfig.future_rising_ratio / 100), demical_point)  #空单涨的时候补仓 # 保留2位小数
            self.future_buy_price = min(dynamicConfig.future_buy_price, float(dynamicConfig.record_future_price[-1]) if len(dynamicConfig.record_future_price) > 0 else 999999) # 如果空单平仓价比列表里最大的还大，那交易时就亏本了啊
        # print("设置接下来空单的买回价格:" + str(self.future_buy_price))

    def adjust_prices(self):
        # if self.grid_side == 'BOTH':
        #     min_buy_price = min(dynamicConfig.spot_buy_price, dynamicConfig.future_buy_price)
        #     max_sell_price = max(dynamicConfig.spot_sell_price, dynamicConfig.future_sell_price)
        #     dynamicConfig.spot_buy_price = min_buy_price
        #     dynamicConfig.spot_sell_price = max_sell_price
        #     dynamicConfig.future_sell_price = max_sell_price
        #     dynamicConfig.future_buy_price = min_buy_price
        #     self.spot_buy_price = dynamicConfig.spot_buy_price
        #     self.spot_sell_price = dynamicConfig.spot_sell_price
        #     self.future_sell_price = dynamicConfig.future_sell_price
        #     self.future_buy_price = dynamicConfig.future_buy_price
        print("【重设】接下来多单买入的价格, " + str(self.spot_buy_price))
        print("【重设】接下来多单卖出的价格:" + str(self.spot_sell_price))
        print("【重设】接下来新开空单卖出的价格, " + str(self.future_sell_price))
        print("【重设】接下来空单的买回价格:" + str(self.future_buy_price))
        pass

    def set_spot_share(self, spot_step):
        print("set_spot_share")
        dynamicConfig.spot_step = spot_step
        self.spot_step = dynamicConfig.spot_step
        print("设置多单仓位： " + str(self.spot_step))

    def _format(self, quantity):
        return int(quantity)

    def normal_exit(self):
        while not fc.stop_singal_from_client:
            if fc.change_ratio_singal_from_client:
                # print(str(fc.stop_singal_from_client))
                # if fc.change_ratio_singal_from_client:
                self.set_ratio_and_price()
                fc.change_ratio_singal_from_client=False
            if fc.change_every_time_trade_share_signal_from_client:
                self.cur_market_future_price = self.http_client_spot.get_latest_price(config.symbol).get('price')  # self.http_client_future.get_latest_price(config.symbol).get('price')
                quantity_basic = round((fc.every_time_trade_share / float(self.cur_market_future_price)), 3)
                self.quantity = self._format(quantity_basic)
                fc.change_every_time_trade_share_signal_from_client=False
            if fc.change_quantity_singal_from_client:
                self.quantity = str(fc.quantity)
                fc.change_quantity_singal_from_client=False
            if fc.change_position_side_singal_from_client:
                self.grid_side = fc.position_side
                fc.change_position_side_singal_from_client=False
            if fc.change_long_bottom_position_share_singal_from_client:
                self.long_bottom_position_share = fc.long_bottom_position_share
                fc.change_long_bottom_position_share_singal_from_client = False
            if fc.cut_position_threshold_singal_from_client:
                self.cut_position_threshold = fc.cut_position_threshold
                fc.cut_position_threshold_singal_from_client=False
            if fc.ease_position_share_singal_from_client:
                self.ease_position_share = fc.ease_position_share
                fc.ease_position_share_singal_from_client=False
            if fc.update_position_list_signal_from_client:
                self.init_record_price_list()
                fc.update_position_list_signal_from_client=False
            if fc.long_buy_ratio_scale_signal_from_client:
                self.long_buy_ratio_scale=fc.long_buy_ratio_scale
                fc.long_buy_ratio_scale_signal_from_client=False
            if fc.end_martin_grid_singal_from_client:
                self.end_martin_grid = fc.end_martin_grid
                self.set_ratio_and_price()
                fc.end_martin_grid_singal_from_client=False
            self.crazy_buy = fc.crazy_buy
            self.open_trend_trade = fc.open_trend_trade
            # current_falling_ratio = dynamicConfig.spot_falling_ratio
            #     current_rising_ratio = dynamicConfig.rising_ratio
            #     self.set_ratio()
            #     current_share_previous_market_price = float(self.future_sell_price) / (1 + float(current_rising_ratio))
            #     self.set_future_price(current_share_previous_market_price) #恢复回当时的市场价，然后根据传入的比率重新设置
            #     fc.change_ratio_singal_from_client = False
            time.sleep(3)
        self.save_trade_info()
        # self.place_left_orders()
        msg = 'stop by myself!'
        print(msg)
        Message.dingding_warn(str(msg))
        # os._exit(0)

    def place_left_orders(self):
        '''停止时，自动挂单吧'''
        print('停止时，自动挂单吧')
        time_format = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        for spot_price in dynamicConfig.record_spot_price:
            self.close_long(time_format, False, str(int(float(spot_price) * (1 + dynamicConfig.spot_rising_ratio / 100))))
        for future_price in dynamicConfig.record_future_price:
            self.close_short(time_format, False, str(int(float(future_price) * (1 - dynamicConfig.future_falling_ratio / 100))))

    def open_receiver(self):
        #todo 最好还是放在另外一个进程里，方便命令调起网格策略
        app.run(host='104.225.143.245', port=5000 if config.platform == 'binance_future' else 5005, threaded=True)

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
        if tmp and len(tmp) > 0:
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

        if config.platform == 'test':
            trade_info_file_path = '../data/trade_info_%s_test.json' % config.symbol
        else:
            trade_info_file_path = '../data/trade_info_%s.json' % config.symbol

        with open(trade_info_file_path, 'r') as df:
            if os.path.getsize(df.name) == 0:
                return
            record_price_dict_to_file = json.load(df)
            if 'record_spot_price' in record_price_dict_to_file.keys():
                print(f"record_price_dict_to_file['record_spot_price']:{record_price_dict_to_file['record_spot_price']}")
                dynamicConfig.record_spot_price = record_price_dict_to_file['record_spot_price']
            if 'record_future_price' in record_price_dict_to_file.keys():
                print(f"record_price_dict_to_file['record_future_price']:{record_price_dict_to_file['record_future_price']}")
                dynamicConfig.record_future_price = record_price_dict_to_file['record_future_price']
            if 'long_bottom_position_price' in record_price_dict_to_file.keys():
                print(f"record_price_dict_to_file['long_bottom_position_price']:{record_price_dict_to_file['long_bottom_position_price']}")
                dynamicConfig.long_bottom_position_price = record_price_dict_to_file['long_bottom_position_price']
            dynamicConfig.total_steps = len(dynamicConfig.record_spot_price) + len(dynamicConfig.record_future_price) + len(dynamicConfig.long_bottom_position_price)

    # def init_record_future_price_list(self):
    #     orders = self.http_client_future.get_all_orders(config.symbol)
    #     for order in orders:
    #         if order.get('positionSide') == 'SHORT' and order.get('side') == OrderSide.SELL.value and order.get('status') == OrderStatus.FILLED.value:
    #             dynamicConfig.record_future_price.append(order.get('price'))

    def save_trade_info(self):
        print("存储记录的价格到文件里")
        print(f"save_trade_info, record_spot_price:{dynamicConfig.record_spot_price}, record_future_price:{dynamicConfig.record_future_price}, dynamicConfig.long_bottom_position_price:{dynamicConfig.long_bottom_position_price}")

        record_price_dict_to_file = {'record_spot_price':dynamicConfig.record_spot_price, 'record_future_price':dynamicConfig.record_future_price, 'long_bottom_position_price':dynamicConfig.long_bottom_position_price}

        if config.platform == 'test':
            trade_info_file_path = '../data/trade_info_%s_test.json' % config.symbol
        else:
            trade_info_file_path = '../data/trade_info_%s.json' % config.symbol

        with open(trade_info_file_path, "w") as df:
            json.dump(record_price_dict_to_file, df)

        self.save_trade_benefit()

    def save_trade_benefit(self):
        '''
            "货币对": ["运行时间", "总获利", "总利润率", "总格子数", "总仓位数", "多仓", "空仓", "底仓"]
        :return:
        '''
        record_benefit_list_to_file = [self.grid_run_time, str(dynamicConfig.total_earn), self.gross_profit, str(dynamicConfig.total_earn_grids), str(dynamicConfig.total_steps), str(self.future_step), str(len(dynamicConfig.long_bottom_position_price))]
        trade_benefit_path = '../data/trade_benefit.json'
        with open(trade_benefit_path, "r") as df_read:
            load_dict = json.load(df_read)
            print(load_dict)
            if load_dict and config.symbol in load_dict.keys():
                load_dict[config.symbol] = record_benefit_list_to_file
                with open(trade_benefit_path, "w") as df_write:
                    json.dump(load_dict, df_write)

    def close_previous_position(self, time_format):
        print("清掉盈利的多单和空单仓位，未盈利的留着")
        ret_list_spot = []
        ret_list_future = []
        for tmp in dynamicConfig.record_spot_price:
            self.cur_market_future_price = self.http_client_spot.get_latest_price(config.symbol).get('price')
            if float(tmp) <= float(self.cur_market_future_price):
                self.close_long(time_format, True, self.cur_market_future_price)
            else:
                ret_list_spot.append(tmp)
        dynamicConfig.record_spot_price = ret_list_spot
        # print("ssdfsdf:" + str(dynamicConfig.record_spot_price))

        for tmp in dynamicConfig.record_future_price:
            self.cur_market_future_price = self.http_client_spot.get_latest_price(config.symbol).get('price')
            if float(tmp) >= float(self.cur_market_future_price):
                self.close_short(time_format, True, self.cur_market_future_price)
            else:
                ret_list_future.append(tmp)
        dynamicConfig.record_future_price = ret_list_future
        # del ret_list_spot[:]
        # del ret_list_future[:]

        self.save_trade_info()

    def long_bottom_position_full(self):
        '''
        判断是否满仓
        :param price:
        :return:
        '''
        tmp_list = [float(tmp) for tmp in dynamicConfig.long_bottom_position_price]
        current_position_share = (sum(tmp_list) * float(self.quantity)) / self.spot_money
        ret = (current_position_share >= fc.long_bottom_position_share)
        return ret

    def need_join_in_long_bottom_position_price(self, price):
        '''
        判断价格是否加入底仓列表
        :param price:
        :return:
        '''
        need_join = False
        tmp_list = [float(tmp) for tmp in dynamicConfig.long_bottom_position_price]
        if len(tmp_list) == 0:
            need_join = True
        if price:
            if float(price) < max(tmp_list):
                need_join = True
        return need_join

    def get_long_bottom_position_scale(self):
        current_position_share = (sum([float(tmp) for tmp in dynamicConfig.long_bottom_position_price]) * float(
            self.quantity)) / self.spot_money
        ret = current_position_share
        print("current_position_share:" + str(current_position_share))
        return ret

    def build_long_bottom_position(self, price, time_format):
        print('当前的价格' + str(self.cur_market_future_price) + '，目前的底仓列表：' + str(dynamicConfig.long_bottom_position_price))
        #todo need improve
        len_position_share = len(dynamicConfig.long_bottom_position_price)
        need_open_long_bottom_position = False
        tick_out_price = ''  # 需要剔除的价格
        if not self.long_bottom_position_full():
            need_open_long_bottom_position = True #列表为空直接加
        elif self.need_join_in_long_bottom_position_price(price):#列表不空则优胜略汰
            # retain_list = []
            tmp = max(dynamicConfig.long_bottom_position_price)
            if float(tmp) > float(price):
                print('这个价格超过目前的底仓列表，剔除【' + str(tmp) + '】，将它挂单')
                self.close_long(time_format, False, str(int(float(tmp) * (1 + dynamicConfig.spot_rising_ratio / 100))), True)#挂掉出了
                tick_out_price = tmp
                need_open_long_bottom_position = True
        if need_open_long_bottom_position and tick_out_price:
            dynamicConfig.long_bottom_position_price.remove(tick_out_price)#把价格大的剔除
            self.save_trade_info()

        if need_open_long_bottom_position:
            print('这个价格需要加入底仓')
            dynamicConfig.long_bottom_position_price.append(price)
            self.save_trade_info()
            need_open_long_bottom_position = False
            return self.open_long(time_format, True)#加入底仓后，需要开单，才算真正加入了底仓





if __name__ == "__main__":

    # test
    # kline_path = '/home/code/binance/backtest/UNIBUSD-1m-2021-12-01.csv'
    # with open(kline_path, 'r', encoding='utf-8') as df:
    #     # test
    #     read = csv.reader(df)
    #     rows = [row for row in read]
    #     # index = CalcIndex(self.rows)
    #     cur_market_price = rows[0][4]
    #
    # for i in range(0, len(rows)):
    #     print("cur_market_price:" + str(rows[i][4]))

    ###########################################################
    #official
    print('=======cypto script begin======')
    error_raw = ''
    hengedGrid = None
    try:
        config.loads('../config_uni.json')
        # dynamicConfig.loads('./config.json')

        hengedGrid = HengedGrid()
        if config.platform != 'test':
            receiver_thread = threading.Thread(target=hengedGrid.open_receiver)
            receiver_thread.start()
        else:
            fc.start_grid = True
        exit_thread = threading.Thread(target=hengedGrid.normal_exit)
        exit_thread.start()
        run_thread = threading.Thread(target=hengedGrid.run)
        while not fc.terminate:
            time.sleep(1)
            if run_thread:
                if fc.start_grid:
                    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
                        if not run_thread.is_alive():
                            run_thread.start()
                    else:
                        if not run_thread.is_alive():
                            run_thread.start()
                    fc.start_grid = False
                if fc.stop_singal_from_client:
                    run_thread.join()
        if config.platform != 'test':
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
            Message.dingding_warn("[test]"+str(error_info))