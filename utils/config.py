# -*- coding:utf-8 -*-
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


import json


class Config:

    def __init__(self):

        self.platform: str = "binance_spot"  # 交易的平台
        self.symbol:str = "BTCUSDT"  # 交易对.
        self.gap_percent: float = 0.01  # 网格变化交易的单位.
        self.api_key: str = None
        self.api_secret: str = None
        self.pass_phrase = None
        self.quantity:float = 0.0004
        self.min_price =  0.0001
        self.min_qty = 0.01
        self.max_orders = 1
        self.proxy_host = ""  # proxy host
        self.proxy_port = 0  # proxy port
        self.initial_price = 0
        self.grid_number = 0
        self.max_border_price = 0
        self.min_border_price = 0


    def loads(self, config_file=None):
        """ Load config file.

        Args:
            config_file: config json file.
        """
        configures = {}
        if config_file:
            try:
                with open(config_file) as f:
                    data = f.read()
                    configures = json.loads(data)
            except Exception as e:
                print(e)
                exit(0)
            if not configures:
                print("config json file error!")
                exit(0)
        self._update(configures)

    def _update(self, update_fields):
        """
        更新update fields.
        :param update_fields:
        :return: None

        """

        for k, v in update_fields.items():
            setattr(self, k, v)

config = Config()

class DynamicConfig(object):

    def __init__(self):
        self.rising_ratio = 2.25
        self.falling_ratio = 2.25
        self.spot_buy_price = 32000
        self.spot_sell_price = 33000
        self.spot_step = 0 #步数/仓位数
        self.record_spot_price = []

        self.future_buy_price = 32000
        self.future_sell_price = 32221
        self.future_step = 0 #步数/仓位数
        self.record_future_price = []

        # test
        self.order_list = []
        self.total_earn = 0
        self.total_invest = 0

    def loads(self, config_file=None):
        """ Load config file.

        Args:
            config_file: config json file.
        """
        configures = {}
        if config_file:
            try:
                with open(config_file) as f:
                    data = f.read()
                    configures = json.loads(data)
            except Exception as e:
                print(e)
                exit(0)
            if not configures:
                print("config json file error!")
                exit(0)
        self._update(configures)

    def _update(self, update_fields):
        """
        更新update fields.
        :param update_fields:
        :return: None

        """

        for k, v in update_fields.items():
            setattr(self, k, v)

dynamicConfig = DynamicConfig()