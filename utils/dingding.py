# author-wechat：findpanpan
import time

import requests,json

# windows
# from app.authorization import dingding_token, recv_window,api_secret,api_key
# from app.BinanceAPI import BinanceAPI
# linux
from utils.config_ma import config


class Message:

    def do_buy_limit_msg(self,market, quantity, price, profit_usdt=0):
        '''
        合约开多，带有钉钉消息的封装
        :param market:
        :param quantity: 数量
        :param rate: 价格
        :return:
        '''
        try:
            res = BinanceAPI(api_key,api_secret).limit_future_order("SELL",market, quantity,"LONG", price)
            if res['orderId']:
                buy_info = "报警：币种为：{cointype}。做多卖单价为：{price}。卖单量为：{num}.".format(cointype=market,price=price,num=quantity)
                self.dingding_warn(buy_info)
                return res
        except BaseException as e:
            error_info = "报警：币种为：{cointype},做多多单失败.api返回内容为:{reject}".format(cointype=market,reject=res['msg'])
            self.dingding_warn(error_info+str(res))
            return res

    def open_buy_market_msg(self, market, quantity):
        '''
        合约开多 市价单
        :param market:
        :param quantity: 数量
        :param price: 价格
        :return:
        '''
        try:
            res = BinanceAPI(api_key, api_secret).market_future_order("BUY", market, quantity, "LONG")
            if res['orderId']:
                buy_info = "报警：币种为：{cointype}。开多买单量为：{num}".format(cointype=market,num=quantity)
                self.dingding_warn(buy_info)
                return res
        except BaseException as e:
            error_info = "报警：币种为：{cointype},开多多单失败.api返回内容为:{reject}".format(cointype=market, reject=res['msg'])

    def do_buy_market_msg(self, market, quantity,profit_usdt=0):
        '''
        合约平多 市价单
        :param market:
        :param quantity: 数量
        :param price: 价格
        :return:
        '''
        try:
            res = BinanceAPI(api_key, api_secret).market_future_order("SELL", market, quantity, "LONG")
            if res['orderId']:
                buy_info = "报警：币种为：{cointype}。做多卖单量为：{num}.".format(cointype=market,num=quantity)
                self.dingding_warn(buy_info)
                return res
        except BaseException as e:
            error_info = "报警：币种为：{cointype},开多多单失败.api返回内容为:{reject}".format(cointype=market, reject=res['msg'])

    def open_sell_market_msg(self, market, quantity):
        '''
        合约开空 市价单
        :param market:
        :param quantity: 数量
        :param price: 价格
        :return:
        '''
        try:
            res = BinanceAPI(api_key, api_secret).market_future_order("SELL", market, quantity, "SHORT")
            if res['orderId']:
                buy_info = "报警：币种为：{cointype}。开空买单量为：{num}".format(cointype=market,num=quantity)
                self.dingding_warn(buy_info)
                return res
        except BaseException as e:
            error_info = "报警：币种为：{cointype},开多多单失败.api返回内容为:{reject}".format(cointype=market, reject=res['msg'])

    def do_sell_market_msg(self, market, quantity,profit_usdt=0):
        '''
        合约平空 市价单
        :param market:
        :param quantity: 数量
        :param price: 价格
        :return:
        '''
        try:
            res = BinanceAPI(api_key, api_secret).market_future_order("BUY", market, quantity, "SHORT")
            if res['orderId']:
                buy_info = "报警：币种为：{cointype}。做空卖单量为：{num}.".format(cointype=market,num=quantity)
                self.dingding_warn(buy_info)
                return res
        except BaseException as e:
            error_info = "报警：币种为：{cointype},开多多单失败.api返回内容为:{reject}".format(cointype=market, reject=res['msg'])


    # def open_buy_limit_msg(self,market, quantity, price):
    #     '''
    #     合约开多
    #     :param market:
    #     :param quantity: 数量
    #     :param price: 价格
    #     :return:
    #     '''
    #     try:
    #         res = BinanceAPI(api_key,api_secret).limit_future_order("BUY",market, quantity,"LONG", price)
    #         if res['orderId']:
    #             buy_info = "报警：币种为：{cointype}。开多买单价为：{price}。买单量为：{num}".format(cointype=market,price=price,num=quantity)
    #             self.dingding_warn(buy_info)
    #             return res
    #     except BaseException as e:
    #         error_info = "报警：币种为：{cointype},开多多单失败.api返回内容为:{reject}".format(cointype=market,reject=res['msg'])
    #         self.dingding_warn(error_info)



    # def open_sell_future_msg(self,market, quantity, price):
    #     '''
    #     合约开空单，带有钉钉消息
    #     :param market: 交易对
    #     :param quantity: 数量
    #     :param price: 价格
    #     :return:
    #     '''
    #     try:
    #         res = BinanceAPI(api_key,api_secret).limit_future_order('SELL', market, quantity,"SHORT", price)
    #         if res['orderId']:
    #             buy_info = "报警：币种为：{cointype}。开空买入价格为：{price}。数量为：{num}".format(cointype=market,price=price,num=quantity)
    #             self.dingding_warn(buy_info)
    #             return res
    #     except BaseException as e:
    #         error_info = "报警：币种为：{cointype},开空空单失败.api返回内容为:{reject}".format(cointype=market,reject=res['msg'])
    #         self.dingding_warn(error_info+str(res))
    #         return res
        
    def do_sell_future_msg(self,market, quantity, price,profit_usdt=0):
        '''
        合约做空单，带有钉钉消息
        :param market: 交易对
        :param quantity: 数量
        :param price: 价格
        :return:
        '''
        try:
            res = BinanceAPI(api_key,api_secret).limit_future_order('BUY', market, quantity,"SHORT", price)
            if res['orderId']:
                buy_info = "报警：币种为：{cointype}。做空卖单价为：{price}。数量为：{num}。".format(cointype=market,price=price,num=quantity)
                self.dingding_warn(buy_info)
                return res
        except BaseException as e:
            error_info = "报警：币种为：{cointype},做空空单失败.api返回内容为:{reject}".format(cointype=market,reject=res['msg'])
            self.dingding_warn(error_info+str(res))
            return res


    def buy_market_msg(self, market, quantity):
        '''
            现货市价买入
        :param market:
        :param quantity:
        :return:
        '''
        try:
            res = BinanceAPI(api_key,api_secret).buy_market(market, quantity)
            if res['orderId']:
                buy_info = "报警：币种为：{cointype}。买单量为：{num}".format(cointype=market,num=quantity)
                self.dingding_warn(buy_info)
                return res
        except BaseException as e:
            error_info = "报警：币种为：{cointype},买单失败.".format(cointype=market)
            self.dingding_warn(error_info)


    def sell_market_msg(self,market, quantity):
        '''
            现货市价卖出
        :param market:
        :param quantity: 数量
        :param rate: 价格
        :return:
        '''
        try:
            res = BinanceAPI(api_key,api_secret).sell_market(market, quantity)
            if res['orderId']:
                buy_info = "报警：币种为：{cointype}。卖单量为：{num}".format(cointype=market,num=quantity)
                self.dingding_warn(buy_info)
                return res
        except BaseException as e:
            error_info = "报警：币种为：{cointype},卖单失败".format(cointype=market)
            self.dingding_warn(error_info)
            return res
    @staticmethod
    def dingding_warn(text):
        time_format = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        text = text + ', \n时间：' + time_format
        if config.test:
            pass
        else:
            headers = {'Content-Type': 'application/json;charset=utf-8'}
            api_url_dingding = "https://oapi.dingtalk.com/robot/send?timestamp=%s&access_token=%s" % (str(round(time.time() * 1000)), '4fa42dfced14210f79fde669863f72de96ef969ef74cc2de0f52d08bf845136a')
            d = json.dumps({"msgtype": "text", "text": {"content": text}})
            api_url_telegram = "https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s" % ('1858698079:AAEo4iunenZ3mZSVUICqVAKFoiHU4LGnO6U', '1540332281', text)
            # json_text = self._msg(text)
            requests.post(api_url_dingding, data=d, headers=headers).content
            requests.post(api_url_telegram, headers=headers).content

    def _msg(self,text):
        json_text = {
            "msgtype": "text",
            "at": {
                "atMobiles": [
                    "11111"
                ],
                "isAtAll": False
            },
            "text": {
                "content": text
            }
        }
        return json_text

if __name__ == "__main__":
    msg = Message()
    msg.dingding_warn("hzp~~~")
    # print(msg.buy_limit_future_msg("EOSUSDT",3,2))