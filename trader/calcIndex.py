
import os,json,time

import numpy as np

from gateway import BinanceSpotHttp
from utils import config
from utils.dingding import Message

msg = Message()

class CalcIndex:

    def __init__(self, test_data=None):
        self.coinType = config.symbol  # 交易币种
        self.http_client = BinanceSpotHttp(api_key=config.api_key, secret=config.api_secret,
                                           proxy_host=config.proxy_host, proxy_port=config.proxy_port)
        self.test_data = test_data

    def calcMA(self,symbol,interval,point):
        '''
        :param symbol: 交易对
        :param interval: 间隔时间 1h 4h 1d
        :return: 当前时间ma20 40 60 120 的值
        '''
        sum_ma10=0
        sum_ma20=0
        sum_ma40=0
        sum_ma60 = 0
        sum_ma120 = 0

        num = 0
        data = self.http_client.get_kline(symbol, interval, 120)
        for i in range(len(data)):
            if i>=110 and i <=120:
                sum_ma10 += float(data[i][4])
            if i>=100 and i <=120:
                sum_ma20 += float(data[i][4])
            if i>=80 and i <=120:
                sum_ma40 += float(data[i][4])
            if i >= 60 and i <= 120:
               sum_ma60 += float(data[i][4])

            sum_ma120 +=float(data[i][4])
        return [round(sum_ma10/10,point),round(sum_ma20/20,point),round(sum_ma40/40,point),round(sum_ma60/60,point), round(sum_ma120/120,point)]



    # def set_trendStatus(self,symbol,interval,point):
    #     '''
    #
    #     :param symbol:
    #     :param interval:
    #     :param point:
    #     :return: 1:多头趋势 -1 空头趋势 0 震荡
    #     '''
    #     ma_list = self.calcMA(symbol,interval, point)
    #     max_value = max(ma_list)
    #     min_value = min(ma_list)
    #     future_total = self.calcTotal(runbet.get_future_list(),runbet.get_future_step())
    #     spot_total = self.calcTotal(runbet.get_spot_list(),runbet.get_spot_step())
    #     positive_two_value = ma_list[1] if ma_list[1] > ma_list[2] and ma_list[1] > ma_list[3] else 0  # ma20 大于 ma40 60
    #     lose_two_value = ma_list[1] if ma_list[1] < ma_list[2] and ma_list[1] < ma_list[3] else 0  # ma20 小于ma40 60
    #     if ma_list[0] == max_value and ma_list[4] == min_value and positive_two_value != 0: # 多头排列，直到形态走坏
    #         if runbet.get_hedgingStatus() != 11 and future_total is not 0: #多头趋势未开启对冲
    #
    #             res = msg.buy_market_msg(self.coinType,future_total)
    #             if res['orderId']:
    #                 runbet.set_hedgingStatus(11)
    #         return 1
    #     elif ma_list[0] == min_value and ma_list[4] == max_value and lose_two_value is not 0: # 空头
    #         if runbet.get_hedgingStatus() != -11 and spot_total is not 0: #空头趋势未开启对冲
    #                 res = msg.open_sell_market_msg(self.coinType, spot_total)
    #                 if res['orderId']:
    #                     runbet.set_hedgingStatus(-11)
    #         return -1
    #     else:
    #         if runbet.get_hedgingStatus() == 11 and future_total is not 0 : #已经开启多头对冲，关闭掉
    #             res = msg.sell_market_msg(self.coinType,future_total)
    #             if res['orderId']:
    #                 runbet.set_hedgingStatus(0)
    #
    #         elif runbet.get_hedgingStatus() == -11 and future_total is not 0: # 已经开启空头对冲，关闭掉
    #             res = msg.do_sell_market_msg(self.coinType,spot_total)
    #             if res['orderId']:
    #                 runbet.set_hedgingStatus(0)
    #         return 0

    def calcTotal(self,arr,step):
        total = 0
        for i in range(step):
            if len(arr) <= i:
                total += arr[-1]
            else:
                total += arr[i]
        return total

    def calcSlopeMA10(self,symbol,interval,point):
        '''

        :param symbol:
        :param interval:
        :return: 上一时刻的m20值
        '''
        last_ma10 = 0
        next_ma10 = 0
        num = 0
        data = self.http_client.get_kline(symbol, interval, 11)
        for i in range(len(data)):
            if i==0:
                last_ma10+=float(data[i][4])
            elif i==10:
                next_ma10+=float(data[i][4])
            else:
                last_ma10+=float(data[i][4])
                next_ma10+=float(data[i][4])

        return [round(last_ma10/10,point),round(next_ma10/10,point)]

    def calcSlopeMA5(self, symbol, interval, point, j):
        '''

        :param symbol:
        :param interval:
        :return: 上一时刻的m20值
        '''
        last_ma5 = 0
        next_ma5 = 0
        data = self.http_client.get_kline(symbol, interval, limit=6)

        # test
        # data = self.test_data[j - 6:j]

        tmp_list_ma5 = []
        for i in range(len(data)):
            if i==0:
                last_ma5+=float(data[i][4])
            elif i==5:
                next_ma5+=float(data[i][4])
            else:
                last_ma5+=float(data[i][4])
                next_ma5+=float(data[i][4])
            tmp_list_ma5.append(float(data[i][4]))

        return [round(last_ma5/5,point), round(next_ma5/5,point)]

    def calcSlopeMA5_list(self, symbol, interval, point, j=0):
        '''

        :param symbol:
        :param interval:
        :return: 上一时刻的m20值
        '''
        last_ma5 = 0
        next_ma5 = 0
        data = self.http_client.get_kline(symbol, interval, limit=11)#临时从6改为11了,多几根线参与趋势判断

        # test
        # data = self.test_data[j - 6:j]

        tmp_list_ma5 = []
        for i in range(len(data)):
            if i==0:
                last_ma5+=float(data[i][4])
            elif i==10:
                next_ma5+=float(data[i][4])
            else:
                last_ma5+=float(data[i][4])
                next_ma5+=float(data[i][4])
            tmp_list_ma5.append(float(data[i][4]))

        return tmp_list_ma5


    # def calcSlope(self,symbol,interval,direction):
    #     '''
    #
    #     :param symbol:
    #     :param interval:
    #     :param direction: 多头还是空头 多:true 空为:false
    #     :return: 斜率是否满足开仓
    #     '''
    #     lastMA10,tmpMA10 = self.calcSlopeMA10(symbol,interval)
    #     if direction:
    #         return tmpMA10 > lastMA10
    #     else:
    #         return lastMA10 > tmpMA10



    def Mann_Kenddall_Trend_desc(self, inputdata):
        # 计算总趋势秩次和
        inputdata = np.array(inputdata)
        n = inputdata.shape[0]
        sum_sgn = 0
        for i in np.arange(n):
            if i <= (n - 1):
                for j in np.arange(i + 1, n):
                    if inputdata[j] > inputdata[i]:
                        sum_sgn = sum_sgn + 1
                    elif inputdata[j] < inputdata[i]:
                        sum_sgn = sum_sgn - 1
                    else:
                        sum_sgn = sum_sgn
        # 计算Z统计值
        if n <= 10:
            Z_value = sum_sgn / (n * (n - 1) / 2)
        else:
            if sum_sgn > 0:
                Z_value = (sum_sgn - 1) / np.sqrt(n * (n - 1) * (2 * n + 5) / 18)
            elif sum_sgn == 0:
                Z_value = 0
            else:
                Z_value = (sum_sgn + 1) / np.sqrt(n * (n - 1) * (2 * n + 5) / 18)
        # 趋势描述
        # 99% ——> +—2.576
        # 95% ——> +—1.96
        # 90% ——> +—1.645
        if np.abs(Z_value) > 1.96 and np.abs(Z_value) <= 2.576:
            if Z_value > 0:
                result_desc = u"95% up"
            else:
                result_desc = u"95% down"
        elif np.abs(Z_value) > 2.576:
            if Z_value > 0:
                result_desc = u"99% up"
            else:
                result_desc = u"99% down"
        else:
            result_desc = u"not trendency"
        return result_desc

    def calcTrend(self, symbol, interval, ascending, point, i):
        '''

        :param symbol:
        :param interval:
        :param direction:
        :return: 趋势来了 正在拉伸 不买
        '''
        lastMA5,curMA5 = self.calcSlopeMA5(symbol, interval, point, i)
        print("ascending：" + str(ascending) +", curMA5:" + str(curMA5) + ",lastMA5:" + str(lastMA5))
        if ascending:
            return curMA5 >= lastMA5 #是否上涨
        else:
            return curMA5 <= lastMA5 #是否下跌

    def calcTrend_MK(self, symbol, interval, ascending, point, i=0):
        '''

        :param symbol:
        :param interval:
        :param direction:
        :return: 趋势来了 正在拉伸 不买不卖，锁死
        '''
        tmp_list_ma5 = self.calcSlopeMA5_list(symbol, interval, point, i)
        result = str(self.Mann_Kenddall_Trend_desc(tmp_list_ma5))
        print('最近几根均线为:' + str(tmp_list_ma5))
        print("Mann_Kenddall_Trend_desc, 趋势为:" + str(result))
        if ascending:
            if 'up' in result or 'down' in result:
                if 'up' in result:
                    print('拉升')
                elif 'down' in result:
                    print('下跌')
                return True
        else:
            if 'up' in result or 'down' in result:
                if 'up' in result:
                    print('拉升')
                elif 'down' in result:
                    print('下跌')
                return True
        print('震荡')
        return False

    def calcMA10(self,symbol,interval,point):
        sum_ma10 = 0
        data = self.http_client.get_kline(symbol, interval, 10)
        for i in range(len(data)):
            sum_ma10+=float(data[i][4])

        return round(sum_ma10 / 10,point)

    def get_position_price(self,direction=True):
        tmp = self.http_client.get_positionInfo(config.symbol)
        for item in tmp:  # 遍历所有仓位
            if direction: # 多头持仓均价
                if item['positionSide'] == "LONG" and float(item['positionAmt']) != 0.0:
                    return float(item['entryPrice'])
            else:        # 空头持仓均价
                if item['positionSide'] == "SHORT" and float(item['positionAmt']) != 0.0:
                    return float(item['entryPrice'])

        return False