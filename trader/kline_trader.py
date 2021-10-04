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
import math
import os
import random
import threading
import time
import sys

sys.path.append("/home/code/mac/binance")
sys.path.append("/home/code/binance")
from utils.config_ma import config
from cmd_receive import fc, app
from gateway import OrderSide, OrderType, BinanceFutureHttp, OrderStatus

from trader.calcIndex import CalcIndex

from utils.dingding import Message


class MA_trader(object):

    def __init__(self):
        api_key = ''
        api_secret = ''
        # if config.platform == 'binance_future_testnet':
        #     api_key = config.api_key_future_testnet
        #     api_secret = config.api_secret_future_testnet
        # else:
        api_key = config.api_key_future
        api_secret = config.api_secret_future

        # self.http_client_spot = BinanceFutureHttp(api_key=api_key, secret=api_secret, proxy_host=config.proxy_host, proxy_port=config.proxy_port)
        self.http_client_future = BinanceFutureHttp(api_key=api_key, secret=api_secret, proxy_host=config.proxy_host,
                                                    proxy_port=config.proxy_port)

        # self.grid_side = fc.position_side
        # self.long_bottom_position_share = fc.long_bottom_position_share
        # self.cut_position_threshold = fc.cut_position_threshold
        self.open_spot_price = 99999
        self.open_future_price = 1
        # self.long_buy_ratio_scale = fc.long_buy_ratio_scale

        self.need_get_back_long = False
        self.need_get_back_short = False
        self.profit_total = 0
        self.angle_ma_18 = 99
        self.angle_ma_42 = 99
        self.kline_dimemsion = "1m"
        self.slope_offset = 5
        self.smooth_line_angle = 12
        self.my_profit_target = 0.25 # 150%的盈利目标
        self.touch_times = 2

        self.last_time_profit = 0

        self.current_price = 0
        self.quantity = ''


        pass

    def getMoney(self):
        # test
        # with open('/home/code/binance/data/test_account.txt', 'r+', encoding='utf-8') as df:
        #     res = str(df.read())
        #     print("account money:" + res)
        #     return res
        res = self.http_client_spot.get_account_info(config.symbol)  # 现货或者合约，都是一样的接口
        if res:
            assets = res.get('assets')
            for asset in assets:
                if config.symbol.endswith(asset.get('asset')):
                    return asset.get('crossWalletBalance')
        return 0

    def getAsset(self):
        ret = self.http_client_future.get_future_asset(config.symbol)
        print('ret:' + str(ret))
        return ret

    def set_leverage(self, leverage):
        ret = self.http_client_future.set_future_leverage(config.symbol, leverage)
        # print('set_leverage:' + str(ret))
        return ret['leverage']

    def addMoney(self, money):
        res = float(self.getMoney()) + float(money)
        with open('/home/code/binance/data/test_account_%s.txt' % config.symbol, 'w', encoding='utf-8') as df:
            df.write(str(res))
        pass

    def decreaseMoney(self, money):
        res = float(self.getMoney()) - float(money)
        with open('/home/code/binance/data/test_account_%s.txt' % config.symbol, 'w', encoding='utf-8') as df:
            df.write(str(res))
        pass

    def run(self):

        try:
            print("MA_trader, run()")
            print("--------------初始准备阶段开始！---------------")
            time.sleep(3)
            print("--------------初始准备阶段完成！---------------")

            begin_time = time.time()
            loop_count = 1
            # for kkkkk in range(0, 1):

            position_info_short = self.http_client_future.get_future_position_info_ma(config.symbol, 'SHORT')
            position_info_long = self.http_client_future.get_future_position_info_ma(config.symbol, 'LONG')

            self.quantity = max(abs(float(position_info_short[0])), abs(float(position_info_long[0])))
            print('quantity origin:' + str(self.quantity))
            # if float(quantity) == 0.0:  # 都没有单
            #     quantity = config.quantity
            # 市场价开多空相等的两单
            # if abs(float(position_info_short[0])) == 0.0:
            #     self.open_short(quantity)
            # if abs(float(position_info_long[0])) == 0.0:
            #     self.open_long(quantity)

            pre_price_open_long = ''
            pre_price_close_long = ''
            pre_price_open_short = ''
            pre_price_for_ma_42 = ''
            pre_price_for_ma_18 = ''

            price_touch_ma42_count_fall_break = 0
            price_touch_ma42_count_rise_break = 0
            price_touch_ma18_count_fall_break = 0
            price_touch_ma18_count_rise_break = 0

            index = CalcIndex()
            ma_number_18 = 20
            ma_number_42 = 30

            ma_number_35 = 35

            ma_number_3 = 2

            ma_pre_price_3 = 0

            self.quantity = config.quantity


            # ma_pre_price_3 = index.calcSlopeMA(config.symbol, self.kline_dimemsion, self.demical_length, ma_number_3, self.slope_offset)
            #
            # time.sleep(5)
            press_price = 0
            sustain_price = 0
            while not fc.stop_singal_from_client:

                print('ma henged loop, count:' + str(loop_count))

                time_format = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print('now time:' + str(time_format))
                diff_time = time.time() - begin_time
                struct_time = time.gmtime(diff_time)

                self.henged_run_time = '均线信号对冲运行时间:' + str("{0}年{1}月{2}日{3}小时{4}分钟{5}秒".format(
                    struct_time.tm_year - 1970,
                    struct_time.tm_mon - 1,
                    struct_time.tm_mday - 1,
                    struct_time.tm_hour,
                    struct_time.tm_min,
                    struct_time.tm_sec))
                print(self.henged_run_time)

                print('【目前盈利】:' + str(self.profit_total))

                loop_count = loop_count + 1

                if loop_count % 60 == 15:
                    msg = str(self.henged_run_time) + ',【目前盈利】:' + str(self.profit_total) + ('， 最新的压力线：' + str(press_price) + ', 最新的支撑线：' + str(sustain_price)) if (float(press_price) != 0 or float(sustain_price) != 0) else ""
                    Message.dingding_warn(msg)

                position_info_short = self.http_client_future.get_future_position_info_ma(config.symbol, 'SHORT')
                position_info_long = self.http_client_future.get_future_position_info_ma(config.symbol, 'LONG')

                if position_info_long == -1 or position_info_long == -1:
                    print('interface request maybe error')
                    time.sleep(5)
                    continue

                print('position_info_short:' + str(position_info_short))
                print('position_info_long:' + str(position_info_long))
                self.current_price = float(self.http_client_future.get_latest_price(config.symbol).get('price'))
                self.demical_length = len(str(self.current_price).split(".")[1])

                #等信号，到了再开单

                ########42和20日均线法，震荡时亏损有点受不鸟，暂时放弃##############################

                if not pre_price_for_ma_42:
                    pre_price_for_ma_42 = self.current_price
                if not pre_price_for_ma_18:
                    pre_price_for_ma_18 = self.current_price

                # print("aasdasd:"+str(self.kline_dimemsion) + str(self.demical_length) + str(ma_number_42))

                #压力线
                press_price = index.calc_press(config.symbol, self.kline_dimemsion, self.demical_length, ma_number_42)

                #支撑线
                sustain_price = index.calc_sustain(config.symbol, self.kline_dimemsion, self.demical_length, ma_number_42)

                print('press_price:' + str(press_price) + ', sustain_price:' + str(sustain_price))
                if press_price < sustain_price:# 因为按规则上穿压力线就要开多平空，下破支撑线就要开空平多，所以价格如果压力线一定要高于支撑线，否则就换一下
                   press_price, sustain_price = sustain_price, press_price
                   print('【交换后】press_price:' + str(press_price) + ', sustain_price:' + str(sustain_price))

                #均线
                ma_price_3 = index.calcSlopeMA(config.symbol, self.kline_dimemsion, self.demical_length, ma_number_3, self.slope_offset)

                ma_price_35 = index.calcSlopeMA(config.symbol, self.kline_dimemsion, self.demical_length, ma_number_35, self.slope_offset)

                if not ma_pre_price_3:
                    ma_pre_price_3 = ma_price_3[1]

                # print('ma_price_3:' + str(ma_price_3))

                if not position_info_long:
                    print("position_info_long is null")
                if not position_info_short:
                    print("position_info_short is null")
                if not position_info_long[0]:
                    print("position_info_long[0] is null")
                if not position_info_long[1]:
                    print("position_info_long[1] is null")
                if not position_info_short[0]:
                    print("position_info_short[0] is null")
                if not position_info_short[1]:
                    print("position_info_short[1] is null")

                if press_price and sustain_price and press_price > sustain_price:# 压力线要大于支撑线，不然按规则，上穿压力线开多然后向下时，会有风险
                # if position_info_long and position_info_short and position_info_long[0] and position_info_long[0] and position_info_long[2] and position_info_long[2]:
                    self.deal_with_line("", sustain_price, ma_pre_price_3, ma_price_3[1], position_info_long, position_info_short, ma_price_35, self.quantity)
                    self.deal_with_line("", press_price, ma_pre_price_3, ma_price_3[1], position_info_long, position_info_short, ma_price_35, self.quantity)

                # else:
                #     print("sth is null")



                # 压力线之上还有空单，就要清掉；支撑线之下还有多单，也要清掉，那如果是用来抄底的呢？？,而且可能ma还没穿过压力线
                # 暂时不加
                time.sleep(1)
                if ma_price_3[1] > press_price and float(position_info_short[0]) != 0.0:
                    msg = 'ma3价格涨破压力线了，空单还在，要清掉，不然很危险'
                    if float(position_info_short[2]) < 0.0:
                        self.last_time_profit += float(position_info_short[2]) - float(position_info_short[3]) * 0.0006 # 记录亏的

                    self.close_short(self.quantity)
                    print(msg)
                    Message.dingding_warn(msg)
                elif ma_price_3[1] < sustain_price and float(position_info_long[0]) != 0.0:
                    msg = 'ma3价格跌破压力线了，多单还在，要清掉，不然很危险'
                    if float(position_info_long[2]) < 0.0:
                        self.last_time_profit += float(position_info_long[2]) - float(position_info_long[3]) * 0.0006 # 记录亏的
                    self.close_long(self.quantity)
                    print(msg)
                    Message.dingding_warn(msg)

                # ma_price_42 = index.calcSlopeMA(config.symbol, self.kline_dimemsion, self.demical_length, ma_number_42, self.slope_offset)
                # ma_price_18 = index.calcSlopeMA(config.symbol, self.kline_dimemsion, self.demical_length, ma_number_18, self.slope_offset)

                # 算斜率
                # https: // blog.csdn.net / weixin_39585675 / article / details / 111078182
                # self.angle_ma_18 = abs(math.degrees(math.atan2(ma_price_18[1] - ma_price_18[0], self.slope_offset)) * 100)
                # if self.angle_ma_18 > 90:
                #     self.angle_ma_18 = 180 - self.angle_ma_18
                # self.angle_ma_42 = abs(math.degrees(math.atan2(ma_price_42[1] - ma_price_42[0], self.slope_offset)) * 100)
                # if self.angle_ma_42 > 90:
                #     self.angle_ma_42 = 180 - self.angle_ma_42

                # print('angle_ma_18:' + str(self.angle_ma_18) + ', ma_price_18:' + str(ma_price_18[1]) + ', last_ma_price_18:'+ str(ma_price_18[0]))
                # print('angle_ma_42:' + str(self.angle_ma_42) + ', ma_price_42:' + str(ma_price_42[1]) + ', last_ma_price_42:'+ str(ma_price_42[0]))

                # ma_42_cross_kline = index.ma_cross_current_Kline_Half(ma_price_42)

                # print('ma_price_42:' + str(ma_price_42[1]))
                # print('ma_price_18:' + str(ma_price_18[1]))

                # tmp_list_42 = self.deal_with_ma("tag_ma_42", current_price, ma_price_42[1], ma_price_18[1], pre_price_for_ma_42,
                #                                 position_info_long[0], position_info_short[0],
                #                                 price_touch_ma42_count_rise_break, price_touch_ma42_count_fall_break,
                #                                 position_info_long[2], position_info_short[2], position_info_long[3], position_info_short[3])
                # tmp_list_18 = self.deal_with_ma("tag_ma_18", current_price, ma_price_18[1], ma_price_42[1], pre_price_for_ma_18,
                #                                 position_info_long[0], position_info_short[0],
                #                                 price_touch_ma18_count_rise_break, price_touch_ma18_count_fall_break,
                #                                 position_info_long[2], position_info_short[2], position_info_long[3], position_info_short[3])
                #
                # pre_price_for_ma_42 = tmp_list_42[0]
                # price_touch_ma42_count_rise_break = tmp_list_42[1]
                # price_touch_ma42_count_fall_break = tmp_list_42[2]
                #
                # pre_price_for_ma_18 = tmp_list_18[0]
                # price_touch_ma18_count_rise_break = tmp_list_18[1]
                # price_touch_ma18_count_fall_break = tmp_list_18[2]

                ma_pre_price_3 = ma_price_3[1]

                print('ok,  ' + 'sleep 10 secs')
                time.sleep(10)


                # if current_price > ma_price_42: #当前的价格在ma上方
                #     if not pre_price:#没有前一个价格，说明是第一次，不处理
                #         pre_price = current_price
                #         time.sleep(10)
                #         continue
                #     elif pre_price > ma_price_42:#前一个的价格存在，但大于ma，说明pre与cur连成的线在ma上方，不处理
                #         pre_price = current_price
                #         time.sleep(10)
                #         continue
                #     elif pre_price < ma_price_42:#pre与cur连成的线，下往上地穿过了ma，说明是涨破
                #         price_touch_count_rise_break += 1# 累计在ma上方停留的次数，像插针这种也许只停留一次的肯定不能马上开单，要碰多几次
                #         if price_touch_count_rise_break > 3:#暂定碰三次吧
                #             self.close_short(position_info_short[0])#平空
                #             price_touch_count_rise_break = 0
                #             pre_price = current_price
                #             time.sleep(10)
                #         else:
                #             pre_price = current_price
                #             time.sleep(10)
                #             continue
                # elif current_price < ma_price_42:#当前价格在ma下方
                #     if not pre_price:#没有前一个价格，说明是第一次，不处理
                #         pre_price = current_price
                #         time.sleep(10)
                #         continue
                #     elif pre_price > ma_price_42:#前一个的价格存在，但小于ma，说明pre与cur连成的线在ma下方，不处理
                #         pre_price = current_price
                #         time.sleep(10)
                #         continue
                #     elif pre_price > ma_price_42:#pre与cur连成的线，上往下地穿过了ma，说明是跌破
                #         price_touch_count_fall_break += 1# 累计在ma下方停留的次数，像插针这种也许只停留一次的肯定不能马上开单，要碰多几次
                #         if price_touch_count_fall_break > 3:#暂定碰三次吧
                #             self.close_long(position_info_long[0])#平多
                #             price_touch_count_fall_break = 0
                #             pre_price = current_price
                #             time.sleep(10)
                #         else:
                #             pre_price = current_price
                #             time.sleep(10)
                #             continue

                # if float(position_info_short[2]) / float(position_info_short[3]) >= 0.5:

                # time.sleep(5)
        except Exception as e:
            error_msg = '异常发生了，赶紧上一个对冲单：' + str(e)
            print(error_msg)
            Message.dingding_warn(error_msg)
            try:
                if float(position_info_long[0]) == 0.0:# 没空开空，没多开多，这里异常说明多空都没有
                    self.open_long(self.quantity)
                if float(position_info_short[0]) == 0.0:
                    self.open_short(self.quantity)
            except Exception as e:
                error_msg = 'error again:' + str(e) + '开仓也失败了，那就清仓， 上次的盈亏为： ' + str(self.last_time_profit)
                print(error_msg)
                Message.dingding_warn(error_msg)
                # position_info_long or position_info_long 出错了
                self.close_long(self.quantity)
                self.close_short(self.quantity)


    def set_quantity(self):
        # print('quantity last time:' + str(self.quantity))
        print('self.last_time_profit：' + str(self.last_time_profit))
        # 挽救震荡磨损的办法，上次如果亏损了，这次就双份，一份是为了覆盖上次亏损之后止盈出场的，但出场后，剩下的（比如某次双份是8倍，止盈后应该降为1倍）应该缩减为1倍；控制风险
        if self.last_time_profit < 0.0:
            self.quantity = float(config.quantity) * (int(self.quantity / float(config.quantity)) + 1)  # 翻倍成本太高了，每次递增一倍吧
            msg = '上次亏了，这次要加倍：' + str(self.quantity)
            Message.dingding_warn(msg)
            print(msg)
        else:  # 恢复
            self.quantity = config.quantity
        # print('this time quantity：' + str(self.quantity))

    def deal_with_line(self, tag_line, line_price, ma_pre_price, ma_price, position_info_long, position_info_short, cooperate_ma_price, quantity):

        if not line_price:
            return

        ma_price = float(ma_price)
        ma_pre_price = float(ma_pre_price)
        long_position_amt = position_info_long[0]
        short_position_amt = position_info_short[0]
        position_info_long_profit = position_info_long[2]
        position_info_short_profit = position_info_short[2]
        position_info_long_initial_margin = position_info_long[3]
        position_info_short_initial_margin = position_info_short[3]

        if not position_info_long and not position_info_long[0] and not position_info_long[2] and not position_info_long[3]:
            long_position_amt = position_info_long[0]
            position_info_long_profit = position_info_long[2]
            position_info_long_initial_margin = position_info_long[3]
        if not position_info_short and not position_info_short[0] and not position_info_short[2] and not position_info_short[3]:
            short_position_amt = position_info_short[0]
            position_info_short_profit = position_info_short[2]
            position_info_short_initial_margin = position_info_short[3]
        # if not long_position_amt and not short_position_amt:
        #     quantity = max(abs(float(long_position_amt)), abs(float(short_position_amt)))
        # else:

        print('1111:' + str(ma_price))
        if ma_price > line_price:
            print('2222:')
        # if tag_line == 'press' and ma_price > line_price:
            if ma_pre_price > line_price:
                print('3333:')
                # print('这次和上次的ma 都在' + tag_line + '上方')
                self.saveLastTimeLoss(quantity, long_position_amt, short_position_amt, position_info_long_profit, position_info_short_profit, position_info_long_initial_margin, position_info_short_initial_margin)
                print('6666:')
            elif ma_pre_price <= line_price:
                print('4444:')
                print('ma涨穿' + tag_line + '了')
                if float(short_position_amt) != 0.0:
                    if float(position_info_short_profit) < 0.0:
                        self.last_time_profit = self.last_time_profit + float(position_info_short_profit) - float(position_info_short_initial_margin) * 0.0006 # 记录亏的
                    self.close_short(quantity)
                    self.profit_total = self.profit_total + float(position_info_short_profit) - float(position_info_short_initial_margin) * 0.0006
                    msg = tag_line + '平空, 总盈亏：' + str(self.profit_total) + (', 本次盈亏：' + str(self.last_time_profit)) if self.last_time_profit != 0 else ''
                    print(msg)
                    Message.dingding_warn(msg)
                if float(long_position_amt) == 0.0:
                    self.set_quantity()  # 亏了下次加倍
                    self.open_long(self.quantity)
        # elif tag_line == 'sustain' and ma_price < line_price:
        elif ma_price < line_price:
            if ma_pre_price < line_price:
                # print('这次和上次的ma都在' + tag_line + '下方')
                self.saveLastTimeLoss(quantity, long_position_amt, short_position_amt, position_info_long_profit, position_info_short_profit, position_info_long_initial_margin, position_info_short_initial_margin)
            elif ma_pre_price >= line_price:
                print('5555:')
                print('ma跌穿' + tag_line + '了' + str(long_position_amt) +', ' + str(position_info_long_profit))
                if float(long_position_amt) != 0.0:
                    if float(position_info_long_profit) < 0.0:
                        self.last_time_profit = self.last_time_profit + float(position_info_long_profit) - float(position_info_long_initial_margin[3]) * 0.0006 # 记录亏的
                    self.close_long(quantity)
                    self.profit_total = self.profit_total + float(position_info_long_profit) - float(position_info_long_initial_margin[3]) * 0.0006
                    msg = tag_line + '平多, 总盈亏：' + str(self.profit_total) + (', 本次盈亏：' + str(self.last_time_profit)) if self.last_time_profit != 0 else ''
                    print(msg)
                    Message.dingding_warn(msg)
                if float(short_position_amt) == 0.0:
                    self.set_quantity()  # 亏了下次加倍
                    self.open_short(self.quantity)
        elif ma_price == line_price:
            print('均线价格刚好跟支撑/压力线相等,均线：' + str(ma_price) + ', 压力线or均线：' + str(line_price))

    def deal_with_ma(self, tag_ma, current_price, ma_price, ma_price_another, pre_price, long_position_amt, short_position_amt,
                     price_touch_count_rise_break, price_touch_count_fall_break, position_info_long_profit,
                     position_info_short_profit, position_info_long_initial_margin, position_info_short_initial_margin):
        print(tag_ma + 'deal_with_ma, params:' + str(current_price) + ', ' + str(ma_price) + ', ' + str(
            pre_price) + ', ' + str(long_position_amt) + ', ' + str(short_position_amt) + ', ' + str(
            price_touch_count_rise_break) + ', ' + str(price_touch_count_fall_break))
        quantity = max(abs(float(long_position_amt)), abs(float(short_position_amt)))
        # print(tag_ma + 'quantity origin:' + str(quantity))
        if quantity == 0:
            quantity = config.quantity
        print(tag_ma + 'quantity final:' + str(quantity))
        if current_price > ma_price:  # 当前的价格在ma上方
            print(tag_ma + 'current_price > ma_price, 当前的价格在' + tag_ma + '上方')
            if not pre_price:  # 没有前一个价格，说明是第一次，不处理
                print(tag_ma + '没有前一个价格，说明是第一次，不处理')
                pre_price = current_price
                price_touch_count_rise_break = 0
            elif pre_price > ma_price:  # 前一个的价格存在，但大于ma，说明pre与cur连成的线在ma上方，不处理
                self.closeInAdvance(quantity, long_position_amt, short_position_amt, position_info_long_profit, position_info_short_profit, position_info_long_initial_margin, position_info_short_initial_margin)
                print(tag_ma + '前一个的价格存在，但大于' + tag_ma + '，说明pre与cur连成的线在' + tag_ma + '上方，不处理')
                pre_price = current_price
                price_touch_count_rise_break = 0
            elif pre_price < ma_price:  # pre与cur连成的线，下往上地穿过了ma，说明是涨破
                print(tag_ma + 'pre与cur连成的线，下往上地穿过了' + tag_ma + '，说明是涨破，次数：' + str(price_touch_count_rise_break + 1))
                price_touch_count_rise_break += 1  # 累计在ma上方停留的次数，像插针这种也许只停留一次的肯定不能马上开单，要碰多几次
                if price_touch_count_rise_break > self.touch_times:  # 暂定碰三次吧
                    print(tag_ma + '触碰涨破' + tag_ma + '到' + str(self.touch_times) + '次了')
                    if float(long_position_amt) == 0.0 and tag_ma == "tag_ma_18":# or tag_ma == "tag_ma_42") and ma_price <= ma_price_another):  # 穿过当时价格低的那跟线开多 #and self.need_get_back_long:  # 没多仓了
                        # if tag_ma == "tag_ma_18" and ma_price <= ma_price_another:
                        #     print('此刻18日线的值小于42日线, ma:' + str(ma_price) + ', ma_price_another:' + str(ma_price_another))
                        # if tag_ma == "tag_ma_42" and ma_price <= ma_price_another:
                        #     print('此刻42日线的值小于18日线, ma:' + str(ma_price) + ', ma_price_another:' + str(ma_price_another))
                        msg = tag_ma + '没多仓了,开多，接回来, 前一个价格：' + str(pre_price) + ' +， 现价：' + str(
                            current_price) + ', ma价格：' + str(ma_price)
                        print(msg)
                        Message.dingding_warn(msg)
                        self.open_long(quantity)  # 开多，接回来
                        self.need_get_back_long = False
                    elif float(short_position_amt) != 0.0 and ((tag_ma == "tag_ma_42" and self.angle_ma_42 >= self.smooth_line_angle) or (self.angle_ma_42 < self.smooth_line_angle and tag_ma == "tag_ma_18")):
                        # if float(position_info_short_profit) <= 0 < (float(position_info_long_profit) + float(
                        #         position_info_short_profit)) and not 0 >= float(position_info_long_profit): # 如果要平空的时候，空为负值，多空都关，为了可以保持将来多空都有浮盈平单的能力
                        #     self.profit_total += abs(float(position_info_long_profit) + float(position_info_short_profit))
                        #     msg = tag_ma + '多空都平掉, 前一个价格：' + str(pre_price) + ' +， 现价：' + str(current_price) + ', ma价格：' + str(
                        #         ma_price) + ', 盈亏：' + str(self.profit_total)
                        #     print(msg)
                        #     Message.dingding_warn(msg)
                        #     self.close_short(quantity)  # 平空
                        #     self.close_long(quantity)  # 平多
                        # el
                        # '''float(position_info_short_profit) > 0 and'''
                        if (tag_ma == "tag_ma_42" and self.angle_ma_42 >= self.smooth_line_angle) or (self.angle_ma_42 < self.smooth_line_angle and tag_ma == "tag_ma_18"):
                            self.profit_total += float(position_info_short_profit)
                            msg = tag_ma + '平空, 前一个价格：' + str(pre_price) + ' +， 现价：' + str(current_price) + ', ma价格：' + str(
                                ma_price) + ', 盈亏：' + str(self.profit_total)
                            print(msg)
                            Message.dingding_warn(msg)
                            self.close_short(quantity)  # 平空
                            self.need_get_back_short = True
                    price_touch_count_rise_break = 0
                    pre_price = current_price
                else:
                    print(tag_ma + '触碰涨破' + tag_ma + '少于' + str(self.touch_times) + '次')
            elif pre_price == ma_price:#todo 碰到线要不要算一次
                print(tag_ma + 'pre_price刚好等于ma_price')
        elif current_price < ma_price:  # 当前价格在ma下方
            print(tag_ma + 'current_price < ma_price, 当前的价格在' + tag_ma + '下方')
            if not pre_price:  # 没有前一个价格，说明是第一次，不处理
                print(tag_ma + '没有前一个价格，说明是第一次，不处理')
                pre_price = current_price
                price_touch_count_fall_break = 0
            elif pre_price < ma_price:  # 前一个的价格存在，但小于ma，说明pre与cur连成的线在ma下方，不处理
                self.closeInAdvance(quantity, long_position_amt, short_position_amt, position_info_long_profit, position_info_short_profit,
                                    position_info_long_initial_margin, position_info_short_initial_margin)
                print(tag_ma + '前一个的价格存在，但小于' + tag_ma + '，说明pre与cur连成的线在' + tag_ma + '下方，不处理')
                pre_price = current_price
                price_touch_count_fall_break = 0
            elif pre_price > ma_price:  # pre与cur连成的线，上往下地穿过了ma，说明是跌破
                print(tag_ma + 'pre与cur连成的线，上往下地穿过了' + tag_ma + '，说明是跌破，次数：' + str(price_touch_count_fall_break + 1))
                price_touch_count_fall_break += 1  # 累计在ma下方停留的次数，像插针这种也许只停留一次的肯定不能马上开单，要碰多几次
                if price_touch_count_fall_break > self.touch_times:  # 暂定碰三次吧
                    print(tag_ma + '触碰跌破' + tag_ma + '到' + str(self.touch_times) + '次了')
                    if float(short_position_amt) == 0.0 and tag_ma == "tag_ma_18": # or tag_ma == "tag_ma_42") and ma_price >= ma_price_another):  # 穿过当时价格高的那跟线开空 # and self.need_get_back_short:  # 没空仓了
                        # if tag_ma == "tag_ma_18" and ma_price >= ma_price_another:
                        #     print('此刻18日线的值大于42日线, ma:' + str(ma_price) + ', ma_price_another:' + str(ma_price_another))
                        # if tag_ma == "tag_ma_42" and ma_price >= ma_price_another:
                        #     print('此刻42日线的值大于18日线, ma:' + str(ma_price) + ', ma_price_another:' + str(ma_price_another))
                        msg = tag_ma + '没空仓了,开空，接回来, 前一个价格：' + str(pre_price) + ' +， 现价：' + str(
                            current_price) + ', ma价格：' + str(ma_price)
                        print(msg)
                        Message.dingding_warn(msg)
                        self.open_short(quantity)  # 开空，接回来
                        self.need_get_back_short = False
                    elif float(long_position_amt) > 0 and ((tag_ma == "tag_ma_42" and self.angle_ma_42 >= self.smooth_line_angle) or (self.angle_ma_42 < self.smooth_line_angle and tag_ma == "tag_ma_18")):
                        # if float(position_info_long_profit) <= 0 < (float(position_info_long_profit) + float(
                        #         position_info_short_profit)) and not 0 >= float(position_info_short_profit): # 多空都关，为了可以保持将来多空都有浮盈平单的能力
                        #     self.profit_total += abs(float(position_info_long_profit) + float(position_info_short_profit))
                        #     msg = tag_ma + '多空都平掉, 前一个价格：' + str(pre_price) + ' +， 现价：' + str(current_price) + ', ma价格：' + str(
                        #         ma_price) + ', 盈亏：' + str(self.profit_total)
                        #     print(msg)
                        #     Message.dingding_warn(msg)
                        #     self.close_short(quantity)  # 平空
                        #     self.close_long(quantity)  # 平多
                        # el
                        # float(position_info_long_profit) > 0 and
                        if (tag_ma == "tag_ma_42" and self.angle_ma_42 >= self.smooth_line_angle) or (self.angle_ma_42 < self.smooth_line_angle and tag_ma == "tag_ma_18"):
                            if tag_ma == "tag_ma_42" and self.angle_ma_42 >= self.smooth_line_angle:
                                print(tag_ma + ', 角度：' +str(self.angle_ma_42))
                            if tag_ma == "tag_ma_18" and self.angle_ma_18 >= self.smooth_line_angle:
                                print(tag_ma + ', 角度：' +str(self.angle_ma_18))
                            self.profit_total += float(position_info_long_profit)
                            msg = tag_ma + '平多, 前一个价格：' + str(pre_price) + ' +， 现价：' + str(current_price) + ', ma价格：' + str(
                                ma_price) + ', 盈亏：' + str(self.profit_total)
                            print(msg)
                            Message.dingding_warn(msg)
                            self.close_long(quantity)  # 平多
                            self.need_get_back_long = True
                    price_touch_count_fall_break = 0
                    pre_price = current_price
                else:
                    print(tag_ma + '触碰跌破' + tag_ma + '少于' + str(self.touch_times) + '次')
            elif pre_price == ma_price:#todo 碰到线要不要算一次
                print(tag_ma + 'pre_price刚好等于ma_price')
        elif current_price == ma_price:
            self.closeInAdvance(quantity, long_position_amt, short_position_amt, position_info_long_profit, position_info_short_profit,
                                position_info_long_initial_margin, position_info_short_initial_margin)
            print(tag_ma + 'current_price刚好等于ma_price')

        return [pre_price, price_touch_count_rise_break, price_touch_count_fall_break]

    def closeInAdvance(self, quantity, long_position_amt, short_position_amt, position_info_long_profit, position_info_short_profit, position_info_long_initial_margin, position_info_short_initial_margin):
        '''
        单边持仓且达到盈利目标时，出掉，防止回撤时利润回吐
        双边持仓不能解开，不然会有大风险
        '''
        msg = ''
        # if self.angle_ma_42 <= self.smooth_line_angle * 1.6:# 较为平缓时，再操作
        if float(short_position_amt) == 0.0 and float(position_info_long_initial_margin) > 0.0 and float(position_info_long_profit) / float(position_info_long_initial_margin) >= self.my_profit_target:
            self.profit_total += float(position_info_long_profit)
            msg = '达到盈利目标了，收工bye,利润:' + str(position_info_long_profit) + '， 总利润：' + str(self.profit_total)
            self.close_long(quantity)  # 平多
        elif float(long_position_amt) == 0.0 and float(position_info_short_initial_margin) > 0.0 and float(position_info_short_profit) / float(position_info_short_initial_margin) >= self.my_profit_target:
            self.profit_total += float(position_info_short_profit)
            msg = '达到盈利目标了，收工bye,利润:' + str(position_info_short_profit) + '， 总利润：' + str(self.profit_total)
            self.close_short(quantity)  # 平空
            print(msg)
            Message.dingding_warn(msg)
        '''

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

        index = CalcIndex()

        # 取出之前存好的多单和空单的买价或者卖价，它们存储在文件里
        #self.init_record_price_list()
        #获得市场价 todo，将来做多的可以改为合约做多，便于使用杠杆
        # self.cur_market_spot_price = self.http_client_spot.get_latest_price(config.symbol).get('price')
        self.cur_market_future_price = self.http_client_spot.get_latest_price(config.symbol).get('price')#self.http_client_future.get_latest_price(config.symbol).get('price')
        # 设定精度，无所谓现货或者合约
        self.demical_length = len(str(self.cur_market_future_price).split(".")[1])
        # 设定买卖数量
        quantity_basic = round((fc.every_time_trade_share / float(self.cur_market_future_price)), 3)
        self.quantity = self._format(quantity_basic)

        # 设定仓位
        # dynamicConfig.spot_step = self.get_spot_share() #现货仓位 #self.get_step_by_position(True) #  合约
        # dynamicConfig.future_step = self.get_future_share() #self.get_step_by_position(False) 一样的
        self.set_spot_share(int(len(dynamicConfig.record_spot_price)))
        self.set_future_step(len(dynamicConfig.record_future_price))

        if self.spot_step != int(float(self.http_client_spot.get_future_position_info(config.symbol)) / float(self.quantity)):
            print(f"现货：接口中获取的仓位数不是0，但列表为空，那么说明是之前买的，或者另外手动买的，不知道均价多少了，那就告诉你仓位:{self.spot_step}，你自己处理掉吧")
        if self.future_step != self.get_step_by_position(False):
            print(f"合约空：仓位数不是0，但列表为空，那么说明是之前买的，或者另外手动买的，不知道均价多少了，那就告诉你仓位:{self.future_step}，你自己处理掉吧")

        # test check value
        # print('check account exchangeinfo: ' + str(self.http_client_spot.exchangeInfo(config.symbol)))  # 保留账户模拟数据
        # print('check account assets spot: ' + str(self.http_client_spot.get_future_position_info(config.symbol)))  # 保留账户模拟数据
        print('check account assets future: ' + str(self.http_client_future.get_future_asset(config.symbol)))
        # print('check account: ' + str(self.http_client_spot.get_account_info(config.symbol)))# 查询现货指定货币的仓位
        print('check market price: ' + str(round(float(self.cur_market_future_price), 2)))
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
        self.leverage = str(self.set_leverage(fc.leverage))
        print('目前杠杆:' + self.leverage)
        print("设置初始的盈利点数")
        self.set_spot_ratio()
        self.set_future_ratio()
        print("设置初始的多单 空单买入卖出价格，仓位")
        self.spot_step = dynamicConfig.spot_step
        self.set_spot_next_buy_price(float(self.cur_market_future_price))# if len(dynamicConfig.record_spot_price) == 0 else float(dynamicConfig.record_spot_price[-1]))
        self.set_spot_next_sell_price(float(self.cur_market_future_price))
        self.future_step = dynamicConfig.future_step
        self.set_future_next_sell_price(float(self.cur_market_future_price))# if len(dynamicConfig.record_future_price) == 0 else float(dynamicConfig.record_future_price[-1]))
        self.set_future_next_buy_price(float(self.cur_market_future_price))
        self.spot_money = float(self.getAsset()[0])
        self.ease_position_share = fc.ease_position_share

        ascending = True
        descending = False

        print("--------------初始准备阶段完成！---------------")

        begin_time = time.time()
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


        print("把上次存下来的卖掉一部分")
        self.close_previous_position(time_format)

        print("等待是寂寞的，所以开仓时先分别开一个空单和多单")
        if self.grid_side == 'BOTH':
            self.open_long(time_format)
            self.open_short(time_format)
        elif self.grid_side == 'LONG':
            self.open_long(time_format)
        elif self.grid_side == 'SHORT':
            self.open_short(time_format)

        time.sleep(5)

        while not fc.stop_singal_from_client:
            print('loop, count:' + str(loop_count))
            loop_count = loop_count + 1

            #test
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
                     struct_time.tm_year-1970,
                     struct_time.tm_mon-1,
                     struct_time.tm_mday-1,
                     struct_time.tm_hour,
                     struct_time.tm_min,
                     struct_time.tm_sec))
                print(self.grid_run_time)
                # str(self.http_client_future.get_future_asset(config.symbol))
                # tmp = self.http_client_future.get_positionInfo(config.symbol)
                # print(f"查看杠杆效果:{tmp}")
                # print("看交易记录：" + str(self.http_client_future.get_my_trades(config.symbol)))
                try:
                    self.spot_money = float(self.getAsset()[0])
                except Exception as e:
                    print('exception:' + str(e))
                    time.sleep(5)
                    continue
                # print('check account: ' + str(self.getAsset()))
                self.gross_profit = str(round(float(dynamicConfig.total_earn) / float(self.spot_money) * 100, 2)) + '%'
                print('目前盈利：' + str(dynamicConfig.total_earn)) #保留账户模拟数据
                print('目前网格套利数：' + str(dynamicConfig.total_earn_grids) + ', 网格毛利润率：' + self.gross_profit)
                print('网格浮动盈亏, 多单：' + str(sum([(float(self.cur_market_future_price) - float(tmp)) * float(self.quantity) for tmp in dynamicConfig.record_spot_price])) + ', 空单：' + str(sum([(float(tmp) - float(self.cur_market_future_price)) * float(self.quantity) for tmp in dynamicConfig.record_future_price])))
                print('总仓位数:' + str(dynamicConfig.total_steps) + ', 多仓:' + str(self.spot_step) + ', 空仓:' + str(self.future_step))
                print('仓位具体信息, 多仓:' + str(dynamicConfig.record_spot_price) + ', 空仓:' + str(dynamicConfig.record_future_price) + ', 底仓：' + str(dynamicConfig.long_bottom_position_price) +  '(' + str(self.get_long_bottom_position_scale()) + '), 阈值：' + str(fc.long_bottom_position_share))

                # 判断一下趋势(做多拉升时or做空暴跌时，认为趋势来了)
                symbol_to_check_trend = config.symbol
                if symbol_to_check_trend.endswith('BUSD'):
                    symbol_to_check_trend = symbol_to_check_trend.replace('BUSD', 'USDT') # 因为遇到过BTCBUSD调用kline返回的结果不变的bug 应该是接口问题导致的
                if fc.position_side == 'LONG':
                    isTrendComing = index.calcTrend_MK(symbol_to_check_trend, "5m", ascending, self.demical_length)
                elif fc.position_side == 'SHORT':
                    isTrendComing = index.calcTrend_MK(symbol_to_check_trend, "5m", descending, self.demical_length)
                else:
                    isTrendComing = False

                self.cur_market_future_price = self.http_client_spot.get_latest_price(config.symbol).get(
                    'price')  # self.http_client_future.get_latest_price(config.symbol).get('price')
                print("目前【市场价】：" + str(self.cur_market_future_price))

                #清仓操作
                if len(dynamicConfig.record_spot_price) > 0:
                    spot_lost_ratio = (float(dynamicConfig.record_spot_price[0]) - float(self.cur_market_future_price)) / float(dynamicConfig.record_spot_price[0])
                    if spot_lost_ratio > self.cut_position_threshold:
                        msg = '要清掉一份仓位，不然要容易爆仓'
                        print(msg)
                        self.open_spot_price = dynamicConfig.record_spot_price[0]
                        self.close_long(time_format, True)
                        Message.dingding_warn(msg + ', 这份止损了:' + str(self.open_spot_price))
                        del dynamicConfig.record_spot_price[0]
                    else:
                        print('最亏的那份多单损益:' + str(spot_lost_ratio))

                position_delta = min(len(dynamicConfig.record_spot_price) - self.ease_position_share, len(dynamicConfig.record_future_price) - self.ease_position_share)
                if len(dynamicConfig.record_spot_price) == len(dynamicConfig.record_future_price) and len(dynamicConfig.record_spot_price) > self.ease_position_share and len(dynamicConfig.record_future_price) > self.ease_position_share:
                    msg = '减少多空持仓数量，卖掉' + str(self.ease_position_share) + '份'
                    print(msg)
                    for i in range(0, position_delta):
                        self.close_long(time_format, True)
                        Message.dingding_warn('这份多单平掉了:' + str(dynamicConfig.record_spot_price[i]))
                        self.close_short(time_format, True)
                        Message.dingding_warn('这份空单平掉了:' + str(dynamicConfig.record_future_price[i]))
                        del dynamicConfig.record_spot_price[i]
                        del dynamicConfig.record_future_price[i]


                if len(dynamicConfig.record_future_price) > 0:
                    future_lost_ratio = (float(self.cur_market_future_price) - float(dynamicConfig.record_future_price[0])) / float(dynamicConfig.record_future_price[0])
                    if future_lost_ratio > self.cut_position_threshold:
                        msg = '要清掉一份仓位，不然要容易爆仓'
                        print(msg)
                        self.open_future_price = dynamicConfig.record_future_price[0]
                        self.close_short(time_format, True)
                        Message.dingding_warn(msg + ', 这份止损了:' + str(self.open_future_price))
                        del dynamicConfig.record_future_price[0]
                    else:
                        print('最亏的那份空单损益:' + str(future_lost_ratio))

                print("下一份多单买入价：" + str(self.spot_buy_price) + "，这份【多单卖出价】：" + str(self.spot_sell_price))
                print("下一份空单卖出价：" + str(self.future_sell_price) + "，这份【空单买入价】：" + str(self.future_buy_price))

                #设定仓位
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

                #开多单（买入持仓）
                #多单市场价要低于你的买入价，才能成交
                if not isTrendComing and float(self.cur_market_future_price) <= float(self.spot_buy_price) and not self.nearly_full_position():
                    if not self.long_bottom_position_full() or self.need_join_in_long_bottom_position_price(self.cur_market_future_price):
                        spot_open_long_res = self.build_long_bottom_position(self.cur_market_future_price, time_format)
                    # if not spot_open_long_res:#不需要建仓
                    spot_res = self.open_long(time_format) #不管是否建仓，都要买一份


                #平掉多单（卖出获利）
                #多单市场价要高于你的卖出价，才能成交
                #要卖出时，市场价也要大于最近上次那个的价格，因为计算盈利的时候，要拿上次的价格来算盈利的，如果max(sell_price,market_price) < get_last_spot_price,会亏钱 # 可能高位的单需要留着，因为还没到它的目标止盈点
                elif not isTrendComing and float(self.cur_market_future_price) >= float(self.spot_sell_price):
                    spot_res = self.close_long(time_format)

                #开空单（卖出借仓）
                #空单市场价要高于你的卖出价，才能成交
                if not isTrendComing and float(self.cur_market_future_price) >= float(self.future_sell_price) and not self.nearly_full_position():
                    future_res = self.open_short(time_format)

                #平掉空单（买入获利）
                #空单市场价要低于你的买回价，才能成交
                #要买回时，市场价也要小于最近上次那个的价格，因为计算盈利的时候，要拿上次的价格来算盈利的，如果min(buy_price,market_price) > get_last_future_price, 会亏钱 # 可能高位的单需要留着，因为还没到它的目标止盈点
                elif not isTrendComing and float(self.cur_market_future_price) <= float(self.future_buy_price):
                    future_res = self.close_short(time_format)

                if (spot_res is None or not spot_res['orderId']) and (future_res is None or not future_res['orderId']):
                    print("这个价格这轮没有买卖成功，开启下一轮")
                    self.save_trade_to_file(time_format, [' ' + time_format, self.cur_market_future_price, "", "", "", ""])
                elif spot_open_long_res and not (future_res and future_res['orderId']):
                    print("这个价格建仓了，目前仓位列表：" + str(dynamicConfig.long_bottom_position_price) + ", 底仓仓位比例：" + str(self.get_long_bottom_position_scale()))
                else:
                    # 多单或者空单开单成功后，均需要修改整体双向的买卖价格
                    #修改价格应在所有流程结束之后做，否则在多单开完之后立马修改所有的价格的话，这时候空单就平不了了
                    self.set_ratio_and_price()
                    # self.set_spot_price(float(self.cur_market_future_price))
                    # self.set_future_price(float(self.cur_market_future_price))

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
            msg2 = '，多单浮动盈亏：' + str((float(self.cur_market_future_price) - tmp_list_result2 / len(dynamicConfig.record_spot_price)) * float(self.quantity))
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

        '''
        # time.sleep(10)

    def saveLastTimeLoss(self, quantity, long_position_amt, short_position_amt, position_info_long_profit, position_info_short_profit, position_info_long_initial_margin, position_info_short_initial_margin):
        '''
        单边持仓的盈利大于上次的亏损时，持仓降为1倍，算是解救亏损成功
        比如这次买了4倍，如果 盈利 * 3/4 > 上次的亏损，那就卸掉这3/4的仓位
        '''
        msg = ''
        # if self.angle_ma_42 <= self.smooth_line_angle * 1.6:# 较为平缓时，再操作
        save_profit_quantity = float(quantity) * ((int(float(quantity) / float(config.quantity)) - 1) / (int(float(quantity) / float(config.quantity))))
        after_quantity = int(float(quantity) - save_profit_quantity)
        handling_charge_long = float(position_info_long_initial_margin) * 0.002 # 大约4次交易的手续费
        handling_charge_short = float(position_info_short_initial_margin) * 0.002 # 大约4次交易的手续费

        # print('config.quantity:' + str(config.quantity))
        # print('self.quantity:' + str(self.quantity))
        # print('quantity:' + str(quantity))
        # print('save_profit_quantity:' + str(save_profit_quantity))
        # print('after_quantity:' + str(after_quantity))
        # print('short_position_amt:' + str(short_position_amt))
        # print('long_position_amt:' + str(long_position_amt))
        # print('position_info_long_profit:' + str(position_info_long_profit))
        # print('position_info_short_profit:' + str(position_info_short_profit))
        # print('int(save_profit_quantity / float(quantity)):' + str(int(save_profit_quantity / float(quantity))))
        # print('self.last_time_profit:' + str(self.last_time_profit))
        # self.last_time_profit = -0.33

        save_share_current_profit_long = float(position_info_long_profit) * float(save_profit_quantity / float(quantity))
        save_share_current_profit_short = float(position_info_short_profit) * float(save_profit_quantity / float(quantity))
        if  float(short_position_amt) == 0.0 and float(position_info_long_profit) > 0 and save_share_current_profit_long > max(abs(self.last_time_profit), abs(self.profit_total) if self.profit_total < 0 else 0) + handling_charge_long: # 0.005 为手续费
            msg = '本次多单盈利: ' + str(position_info_long_profit) + ' 覆盖上次的亏损( ' + str(self.last_time_profit) + ' )了，减仓! 原仓: ' + str(quantity) + ', 减的仓：' + str(save_profit_quantity) + ', 减了之后的： ' + str(after_quantity)
            self.close_long(save_profit_quantity)  # 平多
            self.quantity = after_quantity # 减了之后的
            self.last_time_profit = 0
            self.profit_total += save_share_current_profit_long
            msg += ', 总盈利：' + str(self.profit_total)
            print(msg)
            Message.dingding_warn(msg)
        elif float(long_position_amt) == 0.0 and float(position_info_short_profit) > 0 and save_share_current_profit_short > max(abs(self.last_time_profit), abs(self.profit_total) if self.profit_total < 0 else 0) + handling_charge_short: # 0.005 为手续费
            msg = '本次空单盈利: ' + str(position_info_short_profit) + ' 覆盖上次的亏损( ' + str(self.last_time_profit) + ' )了，减仓! 原仓: ' + str(quantity) + ', 减的仓：' + str(save_profit_quantity) + ', 减了之后的： ' + str(after_quantity)
            self.close_short(save_profit_quantity)  # 平空
            self.quantity = after_quantity # 减了之后的
            self.last_time_profit = 0
            self.profit_total += save_share_current_profit_short
            msg += ', 总盈利：' + str(self.profit_total)
            print(msg)
            Message.dingding_warn(msg)
        '''

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

        index = CalcIndex()

        # 取出之前存好的多单和空单的买价或者卖价，它们存储在文件里
        #self.init_record_price_list()
        #获得市场价 todo，将来做多的可以改为合约做多，便于使用杠杆
        # self.cur_market_spot_price = self.http_client_spot.get_latest_price(config.symbol).get('price')
        self.cur_market_future_price = self.http_client_spot.get_latest_price(config.symbol).get('price')#self.http_client_future.get_latest_price(config.symbol).get('price')
        # 设定精度，无所谓现货或者合约
        self.demical_length = len(str(self.cur_market_future_price).split(".")[1])
        # 设定买卖数量
        quantity_basic = round((fc.every_time_trade_share / float(self.cur_market_future_price)), 3)
        self.quantity = self._format(quantity_basic)

        # 设定仓位
        # dynamicConfig.spot_step = self.get_spot_share() #现货仓位 #self.get_step_by_position(True) #  合约
        # dynamicConfig.future_step = self.get_future_share() #self.get_step_by_position(False) 一样的
        self.set_spot_share(int(len(dynamicConfig.record_spot_price)))
        self.set_future_step(len(dynamicConfig.record_future_price))

        if self.spot_step != int(float(self.http_client_spot.get_future_position_info(config.symbol)) / float(self.quantity)):
            print(f"现货：接口中获取的仓位数不是0，但列表为空，那么说明是之前买的，或者另外手动买的，不知道均价多少了，那就告诉你仓位:{self.spot_step}，你自己处理掉吧")
        if self.future_step != self.get_step_by_position(False):
            print(f"合约空：仓位数不是0，但列表为空，那么说明是之前买的，或者另外手动买的，不知道均价多少了，那就告诉你仓位:{self.future_step}，你自己处理掉吧")

        # test check value
        # print('check account exchangeinfo: ' + str(self.http_client_spot.exchangeInfo(config.symbol)))  # 保留账户模拟数据
        # print('check account assets spot: ' + str(self.http_client_spot.get_future_position_info(config.symbol)))  # 保留账户模拟数据
        print('check account assets future: ' + str(self.http_client_future.get_future_asset(config.symbol)))
        # print('check account: ' + str(self.http_client_spot.get_account_info(config.symbol)))# 查询现货指定货币的仓位
        print('check market price: ' + str(round(float(self.cur_market_future_price), 2)))
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
        self.leverage = str(self.set_leverage(fc.leverage))
        print('目前杠杆:' + self.leverage)
        print("设置初始的盈利点数")
        self.set_spot_ratio()
        self.set_future_ratio()
        print("设置初始的多单 空单买入卖出价格，仓位")
        self.spot_step = dynamicConfig.spot_step
        self.set_spot_next_buy_price(float(self.cur_market_future_price))# if len(dynamicConfig.record_spot_price) == 0 else float(dynamicConfig.record_spot_price[-1]))
        self.set_spot_next_sell_price(float(self.cur_market_future_price))
        self.future_step = dynamicConfig.future_step
        self.set_future_next_sell_price(float(self.cur_market_future_price))# if len(dynamicConfig.record_future_price) == 0 else float(dynamicConfig.record_future_price[-1]))
        self.set_future_next_buy_price(float(self.cur_market_future_price))
        self.spot_money = float(self.getAsset()[0])
        self.ease_position_share = fc.ease_position_share

        ascending = True
        descending = False

        print("--------------初始准备阶段完成！---------------")

        begin_time = time.time()
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


        print("把上次存下来的卖掉一部分")
        self.close_previous_position(time_format)

        print("等待是寂寞的，所以开仓时先分别开一个空单和多单")
        if self.grid_side == 'BOTH':
            self.open_long(time_format)
            self.open_short(time_format)
        elif self.grid_side == 'LONG':
            self.open_long(time_format)
        elif self.grid_side == 'SHORT':
            self.open_short(time_format)

        time.sleep(5)

        while not fc.stop_singal_from_client:
            print('loop, count:' + str(loop_count))
            loop_count = loop_count + 1

            #test
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
                     struct_time.tm_year-1970,
                     struct_time.tm_mon-1,
                     struct_time.tm_mday-1,
                     struct_time.tm_hour,
                     struct_time.tm_min,
                     struct_time.tm_sec))
                print(self.grid_run_time)
                # str(self.http_client_future.get_future_asset(config.symbol))
                # tmp = self.http_client_future.get_positionInfo(config.symbol)
                # print(f"查看杠杆效果:{tmp}")
                # print("看交易记录：" + str(self.http_client_future.get_my_trades(config.symbol)))
                try:
                    self.spot_money = float(self.getAsset()[0])
                except Exception as e:
                    print('exception:' + str(e))
                    time.sleep(5)
                    continue
                # print('check account: ' + str(self.getAsset()))
                self.gross_profit = str(round(float(dynamicConfig.total_earn) / float(self.spot_money) * 100, 2)) + '%'
                print('目前盈利：' + str(dynamicConfig.total_earn)) #保留账户模拟数据
                print('目前网格套利数：' + str(dynamicConfig.total_earn_grids) + ', 网格毛利润率：' + self.gross_profit)
                print('网格浮动盈亏, 多单：' + str(sum([(float(self.cur_market_future_price) - float(tmp)) * float(self.quantity) for tmp in dynamicConfig.record_spot_price])) + ', 空单：' + str(sum([(float(tmp) - float(self.cur_market_future_price)) * float(self.quantity) for tmp in dynamicConfig.record_future_price])))
                print('总仓位数:' + str(dynamicConfig.total_steps) + ', 多仓:' + str(self.spot_step) + ', 空仓:' + str(self.future_step))
                print('仓位具体信息, 多仓:' + str(dynamicConfig.record_spot_price) + ', 空仓:' + str(dynamicConfig.record_future_price) + ', 底仓：' + str(dynamicConfig.long_bottom_position_price) +  '(' + str(self.get_long_bottom_position_scale()) + '), 阈值：' + str(fc.long_bottom_position_share))

                # 判断一下趋势(做多拉升时or做空暴跌时，认为趋势来了)
                symbol_to_check_trend = config.symbol
                if symbol_to_check_trend.endswith('BUSD'):
                    symbol_to_check_trend = symbol_to_check_trend.replace('BUSD', 'USDT') # 因为遇到过BTCBUSD调用kline返回的结果不变的bug 应该是接口问题导致的
                if fc.position_side == 'LONG':
                    isTrendComing = index.calcTrend_MK(symbol_to_check_trend, "5m", ascending, self.demical_length)
                elif fc.position_side == 'SHORT':
                    isTrendComing = index.calcTrend_MK(symbol_to_check_trend, "5m", descending, self.demical_length)
                else:
                    isTrendComing = False

                self.cur_market_future_price = self.http_client_spot.get_latest_price(config.symbol).get(
                    'price')  # self.http_client_future.get_latest_price(config.symbol).get('price')
                print("目前【市场价】：" + str(self.cur_market_future_price))

                #清仓操作
                if len(dynamicConfig.record_spot_price) > 0:
                    spot_lost_ratio = (float(dynamicConfig.record_spot_price[0]) - float(self.cur_market_future_price)) / float(dynamicConfig.record_spot_price[0])
                    if spot_lost_ratio > self.cut_position_threshold:
                        msg = '要清掉一份仓位，不然要容易爆仓'
                        print(msg)
                        self.open_spot_price = dynamicConfig.record_spot_price[0]
                        self.close_long(time_format, True)
                        Message.dingding_warn(msg + ', 这份止损了:' + str(self.open_spot_price))
                        del dynamicConfig.record_spot_price[0]
                    else:
                        print('最亏的那份多单损益:' + str(spot_lost_ratio))

                position_delta = min(len(dynamicConfig.record_spot_price) - self.ease_position_share, len(dynamicConfig.record_future_price) - self.ease_position_share)
                if len(dynamicConfig.record_spot_price) == len(dynamicConfig.record_future_price) and len(dynamicConfig.record_spot_price) > self.ease_position_share and len(dynamicConfig.record_future_price) > self.ease_position_share:
                    msg = '减少多空持仓数量，卖掉' + str(self.ease_position_share) + '份'
                    print(msg)
                    for i in range(0, position_delta):
                        self.close_long(time_format, True)
                        Message.dingding_warn('这份多单平掉了:' + str(dynamicConfig.record_spot_price[i]))
                        self.close_short(time_format, True)
                        Message.dingding_warn('这份空单平掉了:' + str(dynamicConfig.record_future_price[i]))
                        del dynamicConfig.record_spot_price[i]
                        del dynamicConfig.record_future_price[i]


                if len(dynamicConfig.record_future_price) > 0:
                    future_lost_ratio = (float(self.cur_market_future_price) - float(dynamicConfig.record_future_price[0])) / float(dynamicConfig.record_future_price[0])
                    if future_lost_ratio > self.cut_position_threshold:
                        msg = '要清掉一份仓位，不然要容易爆仓'
                        print(msg)
                        self.open_future_price = dynamicConfig.record_future_price[0]
                        self.close_short(time_format, True)
                        Message.dingding_warn(msg + ', 这份止损了:' + str(self.open_future_price))
                        del dynamicConfig.record_future_price[0]
                    else:
                        print('最亏的那份空单损益:' + str(future_lost_ratio))

                print("下一份多单买入价：" + str(self.spot_buy_price) + "，这份【多单卖出价】：" + str(self.spot_sell_price))
                print("下一份空单卖出价：" + str(self.future_sell_price) + "，这份【空单买入价】：" + str(self.future_buy_price))

                #设定仓位
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

                #开多单（买入持仓）
                #多单市场价要低于你的买入价，才能成交
                if not isTrendComing and float(self.cur_market_future_price) <= float(self.spot_buy_price) and not self.nearly_full_position():
                    if not self.long_bottom_position_full() or self.need_join_in_long_bottom_position_price(self.cur_market_future_price):
                        spot_open_long_res = self.build_long_bottom_position(self.cur_market_future_price, time_format)
                    # if not spot_open_long_res:#不需要建仓
                    spot_res = self.open_long(time_format) #不管是否建仓，都要买一份


                #平掉多单（卖出获利）
                #多单市场价要高于你的卖出价，才能成交
                #要卖出时，市场价也要大于最近上次那个的价格，因为计算盈利的时候，要拿上次的价格来算盈利的，如果max(sell_price,market_price) < get_last_spot_price,会亏钱 # 可能高位的单需要留着，因为还没到它的目标止盈点
                elif not isTrendComing and float(self.cur_market_future_price) >= float(self.spot_sell_price):
                    spot_res = self.close_long(time_format)

                #开空单（卖出借仓）
                #空单市场价要高于你的卖出价，才能成交
                if not isTrendComing and float(self.cur_market_future_price) >= float(self.future_sell_price) and not self.nearly_full_position():
                    future_res = self.open_short(time_format)

                #平掉空单（买入获利）
                #空单市场价要低于你的买回价，才能成交
                #要买回时，市场价也要小于最近上次那个的价格，因为计算盈利的时候，要拿上次的价格来算盈利的，如果min(buy_price,market_price) > get_last_future_price, 会亏钱 # 可能高位的单需要留着，因为还没到它的目标止盈点
                elif not isTrendComing and float(self.cur_market_future_price) <= float(self.future_buy_price):
                    future_res = self.close_short(time_format)

                if (spot_res is None or not spot_res['orderId']) and (future_res is None or not future_res['orderId']):
                    print("这个价格这轮没有买卖成功，开启下一轮")
                    self.save_trade_to_file(time_format, [' ' + time_format, self.cur_market_future_price, "", "", "", ""])
                elif spot_open_long_res and not (future_res and future_res['orderId']):
                    print("这个价格建仓了，目前仓位列表：" + str(dynamicConfig.long_bottom_position_price) + ", 底仓仓位比例：" + str(self.get_long_bottom_position_scale()))
                else:
                    # 多单或者空单开单成功后，均需要修改整体双向的买卖价格
                    #修改价格应在所有流程结束之后做，否则在多单开完之后立马修改所有的价格的话，这时候空单就平不了了
                    self.set_ratio_and_price()
                    # self.set_spot_price(float(self.cur_market_future_price))
                    # self.set_future_price(float(self.cur_market_future_price))

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
            msg2 = '，多单浮动盈亏：' + str((float(self.cur_market_future_price) - tmp_list_result2 / len(dynamicConfig.record_spot_price)) * float(self.quantity))
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

        '''
        # time.sleep(10)

    '''
    def set_ratio_and_price(self):
        self.set_spot_ratio()
        self.set_future_ratio()
        self.set_spot_next_buy_price(float(self.cur_market_future_price))#, float(self.get_last_spot_price())))#考虑列表价格的话，拉升后，要跌很多才能开仓；不考虑的话，有可能同个价位附近有很多仓位
        self.set_spot_next_sell_price(float(self.cur_market_future_price))#, float(self.get_last_spot_price())))
        self.set_future_next_buy_price(float(self.cur_market_future_price))#, float(self.get_last_future_price())))
        self.set_future_next_sell_price(float(self.cur_market_future_price))#, float(self.get_last_future_price())))
        self.adjust_prices()

    def nearly_full_position(self):
        if float(dynamicConfig.total_steps * 100) / (float(self.spot_money) * int(self.leverage)) >= 0.95:
            print('9成5仓位了，只平仓不开仓了')
            time.sleep(10)
            return True
        return False

    '''

    def open_long(self, quantity):
        print("进入开多单流程, 数量：" + str(quantity))
        # test
        # spot_res = {'orderId': 'Order' + str(random.randint(1000, 10000))}
        # dynamicConfig.order_list.append(spot_res)
        spot_res = self.http_client_future.place_order(config.symbol, OrderSide.BUY, "LONG", OrderType.MARKET, quantity,
                                                       "none", time_inforce="")
        # print('开多单完整结果：'+str(spot_res))
        if spot_res and spot_res['orderId']:
            print("开多单成功")
            Message.dingding_warn("买入一份多单了！")
            # self.set_spot_ratio()
            # self.set_spot_next_sell_price(float(self.cur_market_future_price))
            # self.set_spot_next_buy_price(float(self.cur_market_future_price))
            # self.set_spot_price(float(self.cur_market_future_price))  # 打折设置下次的买入卖出价格
            # self.set_future_price(float(self.cur_market_future_price)) # 开多单成功后，空单的买入卖出价格要下调，不然价格上涨时，空单难成交
            return spot_res
        else:
            print("貌似没有开多单成功，为啥：")
            print("spot_res：" + str(spot_res))

    def close_long(self, quantity):
        print("进入平多单流程")
        spot_res = {}

        # test
        # spot_res = {'orderId': 'Order' + str(random.randint(1000, 10000))}
        # dynamicConfig.order_list.append(spot_res)
        order_type = OrderType.MARKET
        time_inforce = ''
        spot_res = self.http_client_future.place_order(config.symbol, OrderSide.SELL, "LONG", order_type, quantity,
                                                       price='none', time_inforce=time_inforce)
        if spot_res and spot_res['orderId']:

            # self.set_spot_ratio()
            # self.set_spot_next_buy_price(float(self.cur_market_future_price))
            # self.set_spot_next_sell_price(float(self.cur_market_future_price))

            # self.set_spot_price(float(self.cur_market_future_price))  # 卖掉之后改为上次的价格
            # last_price = self.get_last_spot_price() #获取上次的价格
            # self.set_spot_price(float(last_price))

            # print(str(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())) + ', 目前获利：' + str(
            #     dynamicConfig.total_earn) + ", 投资总额：" + str(dynamicConfig.total_invest) + ", 多单目前仓位：" + str(
            #     self.spot_step))
            # self.save_trade_to_file(time_format, [' ' + time_format, self.cur_market_future_price, "",
            #                                       self.cur_market_future_price, "", ""])
            Message.dingding_warn("平掉一份多单了！")
            # msg = '多单卖出获利了！获得：' + str(
            #     (float(self.cur_market_future_price) - float(self.open_spot_price)) * float(
            #         self.quantity)) + "， 卖出价格：" + str(self.cur_market_future_price) + ", 买入的价格:" + str(self.open_spot_price
            #     ) + ", 买入的数量：" + str(self.quantity) + ', 目前总获利：' + str(dynamicConfig.total_earn) + ', 总格子数：' + str(dynamicConfig.total_earn_grids) + ', 毛利润率：' + self.gross_profit + ', 多仓:' + str(self.spot_step) + ', 空仓:' + str(self.future_step) + ', 仓位具体信息, 多仓:' + str(dynamicConfig.record_spot_price) + ', 空仓:' + str(dynamicConfig.record_future_price) + ', 底仓：' + str(dynamicConfig.long_bottom_position_price) + ', (' + str(self.get_long_bottom_position_scale()) + '), 阈值：' + str(fc.long_bottom_position_share) + ', ' + self.grid_run_time
            # print(msg)
            # Message.dingding_warn(msg)
            return spot_res
        else:
            print("貌似没有平多单成功，为啥：")
            print("spot_res：" + str(spot_res))
        return spot_res

    def open_short(self, quantity):
        future_res = {}
        print("进入开空单流程, 数量：" + str(quantity))
        # future_res
        # future_res= {'orderId': 'Order' + str(random.randint(1000, 10000))}
        # dynamicConfig.order_list.append(future_res)
        future_res = self.http_client_future.place_order(config.symbol, OrderSide.SELL, "SHORT", OrderType.MARKET,
                                                         quantity, "none", "")

        if future_res and future_res['orderId']:
            print("开空单成功")
            Message.dingding_warn("买入一份空单了！")

            return future_res
        else:
            print("貌似没有开空单成功，为啥：")
            print("future_res：" + str(future_res))
            # break

    def close_short(self, quantity):
        print("进入平空单流程")

        order_type = OrderType.MARKET
        time_inforce = ''
        future_res = self.http_client_future.place_order(config.symbol, OrderSide.BUY, "SHORT", order_type, quantity,
                                                         'none', time_inforce)
        if future_res and future_res['orderId']:
            Message.dingding_warn("平掉一份空单了！")
            # self.set_future_ratio()
            # self.set_future_next_buy_price(float(self.cur_market_future_price))
            # self.set_future_next_sell_price(float(self.cur_market_future_price))
            # 获取上一个价格
            # last_price = self.get_last_future_price()
            # self.set_future_price(float(self.cur_market_future_price))
            # msg = '空单买回获利了！获得：' + str((float(self.open_future_price) - float(self.cur_market_future_price)) * float(
            #         self.quantity)) + " usdt， 买回的价格：" + str(self.cur_market_future_price) + ", 卖出的价格:" + str(
            #     self.open_future_price) + ", 买回的数量：" + str(self.quantity) + ', 目前总获利：' + str(dynamicConfig.total_earn) + ', 总格子数：' + str(dynamicConfig.total_earn_grids) + ', 毛利润率：' + self.gross_profit + ', 多仓:' + str(self.spot_step) + ', 空仓:' + str(self.future_step) + ', 仓位具体信息, 多仓:' + str(dynamicConfig.record_spot_price) + ', 空仓:' + str(dynamicConfig.record_future_price) + ', 底仓：' + str(dynamicConfig.long_bottom_position_price) + ', (' + str(self.get_long_bottom_position_scale()) + '), 阈值：' + str(fc.long_bottom_position_share) + ', ' + self.grid_run_time
            # print(msg)
            # Message.dingding_warn(msg)
            return future_res
        else:
            print("貌似没有平掉空单成功，为啥：")
            print("future_res：" + str(future_res))

    '''

    def save_trade_to_file(self, time_format, trade_info):
        try:
            record_market_price_dir = '../data/record'
            if not os.path.exists(record_market_price_dir):
                os.mkdir(record_market_price_dir)
            with open(os.path.join(record_market_price_dir, 'record_market_price_%s_%s.csv' % (time_format.replace(' ', '-'),  config.symbol)),
                      'a+', encoding='utf-8-sig') as ddf:
                writer_p = csv.writer(ddf, delimiter=',')
                if os.path.getsize(os.path.join(record_market_price_dir,
                                                'record_market_price_%s_%s.csv' % (time_format.replace(' ', '-'), config.symbol))) == 0:
                    writer_p.writerow(['datetime', 'price', 'long_buy', 'long_sell', 'short_sell', 'short_buy'])
                writer_p.writerow(trade_info)
        except Exception as ee:
            print('ee:' + str(ee))

    def set_spot_ratio(self):
        print("set_spot_ratio")
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
        print("set_future_ratio")
        ratio_24hr = round(float(self.http_client_spot.get_ticker_24hour(config.symbol)['priceChangePercent']), 1)
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
        dynamicConfig.record_spot_price.sort(reverse=True)#降序
        print('record_spot_price:' + str(dynamicConfig.record_spot_price))
        self.save_trade_info()

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
        self.save_trade_info()

    def add_record_future_price(self, value):
        dynamicConfig.record_future_price.append(value)
        dynamicConfig.record_future_price.sort()
        print('record_future_price:' + str(dynamicConfig.record_future_price))
        self.save_trade_info()

    def get_last_future_price(self):
        if len(dynamicConfig.record_future_price) == 0:
            return dynamicConfig.future_sell_price
        # else:
        #     print('sdfdfg:' + str(self.future_step) + str(dynamicConfig.record_future_price))
        return dynamicConfig.record_future_price[-1]

    def remove_last_future_price(self):
        del dynamicConfig.record_future_price[-1]
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
        print("get_spot_share, dynamicConfig.spot_step:" + str(dynamicConfig.spot_step), ", position:" + self.http_client_spot.get_future_position_info(config.symbol) + ", every piece quantity:" + self.quantity)
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
        dynamicConfig.spot_sell_price = round(deal_price * (1 + dynamicConfig.spot_rising_ratio / 100), demical_point)
        self.spot_sell_price = dynamicConfig.spot_sell_price
        # print("设置接下来多单卖出的价格:" + str(self.spot_sell_price))

    def set_future_next_sell_price(self, deal_price):
        price_str_list = str(deal_price).split(".")
        demical_point = len(price_str_list[1]) if len(price_str_list) > 1 else 0 + 2
        dynamicConfig.future_sell_price = round(deal_price * (1 + dynamicConfig.future_falling_ratio / 100), demical_point)
        self.future_sell_price = dynamicConfig.future_sell_price
        # print("设置接下来新开空单卖出的价格, " + str(self.future_sell_price))

    def set_future_next_buy_price(self, deal_price):
        price_str_list = str(deal_price).split(".")
        demical_point = len(price_str_list[1]) if len(price_str_list) > 1 else 0 + 2
        dynamicConfig.future_buy_price = round(deal_price * (1 - dynamicConfig.future_rising_ratio / 100), demical_point)  #空单涨的时候补仓 # 保留2位小数
        self.future_buy_price = dynamicConfig.future_buy_price
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
        return "{:.2}".format(round(quantity, 3))

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
            # current_falling_ratio = dynamicConfig.spot_falling_ratio
            #     current_rising_ratio = dynamicConfig.rising_ratio
            #     self.set_ratio()
            #     current_share_previous_market_price = float(self.future_sell_price) / (1 + float(current_rising_ratio))
            #     self.set_future_price(current_share_previous_market_price) #恢复回当时的市场价，然后根据传入的比率重新设置
            #     fc.change_ratio_singal_from_client = False
            time.sleep(1)
        self.save_trade_info()
        # self.place_left_orders()
        msg = 'stop by myself!'
        print(msg)
        Message.dingding_warn(str(msg))
        # os._exit(0)

    def place_left_orders(self):
        print('停止时，自动挂单吧')
        time_format = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        for spot_price in dynamicConfig.record_spot_price:
            self.close_long(time_format, False, str(int(float(spot_price) * (1 + dynamicConfig.spot_rising_ratio / 100))))
        for future_price in dynamicConfig.record_future_price:
            self.close_short(time_format, False, str(int(float(future_price) * (1 - dynamicConfig.future_falling_ratio / 100))))

    def open_receiver(self):
        #todo 最好还是放在另外一个进程里，方便命令调起网格策略
        app.run(host='104.225.143.245', port=5000 if config.platform == 'binance_future' else (5002 + random.randint(1, 50)), threaded=True)

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

        with open('../data/trade_info_%s.json' % config.symbol, 'r') as df:
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
        with open('../data/trade_info_%s.json' % config.symbol, "w") as df:
            json.dump(record_price_dict_to_file, df)

    def close_previous_position(self, time_format):
        print("清掉盈利的多单和空单仓位，未盈利的留着")
        ret_list_spot = []
        ret_list_future = []
        for tmp in dynamicConfig.record_spot_price:
            self.cur_market_future_price = self.http_client_spot.get_latest_price(config.symbol).get('price')
            if float(tmp) <= float(self.cur_market_future_price):
                self.close_long(time_format, True)
            else:
                ret_list_spot.append(tmp)
        dynamicConfig.record_spot_price = ret_list_spot
        # print("ssdfsdf:" + str(dynamicConfig.record_spot_price))

        for tmp in dynamicConfig.record_future_price:
            self.cur_market_future_price = self.http_client_spot.get_latest_price(config.symbol).get('price')
            if float(tmp) >= float(self.cur_market_future_price):
                self.close_short(time_format, True)
            else:
                ret_list_future.append(tmp)
        dynamicConfig.record_future_price = ret_list_future
        # del ret_list_spot[:]
        # del ret_list_future[:]

        self.save_trade_info()

    def long_bottom_position_full(self):
        tmp_list = [float(tmp) for tmp in dynamicConfig.long_bottom_position_price]
        current_position_share = (sum(tmp_list) * float(self.quantity)) / self.spot_money
        ret = (current_position_share >= fc.long_bottom_position_share)
        return ret

    def need_join_in_long_bottom_position_price(self, price):
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
                self.close_long(time_format, False, str(int(float(tmp) * (1 + dynamicConfig.spot_rising_ratio / 100))))#挂掉出了
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
    '''


if __name__ == "__main__":
    error_raw = ''
    ma_trader = None
    try:
        config.loads('../config_ma.json')
        # dynamicConfig.loads('./config.json')

        ma_trader = MA_trader()
        # receiver_thread = threading.Thread(target=ma_trader.open_receiver)
        # receiver_thread.start()
        # exit_thread = threading.Thread(target=ma_trader.normal_exit)
        # exit_thread.start()
        run_thread = threading.Thread(target=ma_trader.run)
        run_thread.start()
        '''
        while not fc.terminate:
            time.sleep(1)
            if run_thread:
                if fc.start_grid:
                    if sys.version_info.major == 3 and sys.version_info.minor >= 8:
                        if not run_thread.isAlive():
                            run_thread.start()
                    else:
                        if not run_thread.is_alive():
                            run_thread.start()
                    fc.start_grid = False
                if fc.stop_singal_from_client:
                    run_thread.join()
        '''
        # receiver_thread.join()
        # exit_thread.join()

    except Exception as e:
        print('出现异常了:' + str(e))
        error_raw = '出现异常了:' + str(e)
    except BaseException as be:
        if isinstance(be, KeyboardInterrupt):
            print('ctrl + c 程序中断了')
            error_raw = 'ctrl + c 程序中断了' + str(be)
    finally:
        # ma_trader.save_trade_info()
        if error_raw:
            error_info = "报警：币种{coin},服务停止.错误原因{info}".format(coin=config.symbol, info=str(error_raw) + "目前盈利：")
            # Message.dingding_warn(str(error_info))

