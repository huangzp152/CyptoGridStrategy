import sys
sys.path.append("/usr/local/lib/python3.6/dist-packages")
from flask import Flask, request
app = Flask(__name__)

@app.route('/')
def index():
    return 'hzp, hello world!'

class flaskConfig(object):
    def __init__(self):
        self.stop_singal_from_client=False
        self.change_ratio_singal_from_client=False
        self.change_quantity_singal_from_client=False
        self.change_long_bottom_position_share_singal_from_client=False
        self.cut_position_threshold_singal_from_client=False
        self.ease_position_share_singal_from_client=False
        self.change_every_time_trade_share_signal_from_client=False
        self.update_position_list_signal_from_client=False
        self.long_buy_ratio_scale_signal_from_client=False
        self.change_position_side_singal_from_client=False
        self.ratio_no_trendency=0.3
        self.ratio_up_or_down=0.6
        self.long_buy_ratio_scale=0.33 # 0.25 多空格子利率的比例，0.25即1:4,就是比如做多网格的利率是0.3的话，做空就是0.3 / 0.25= 1.2,通过多空格子大小的差异来形成对冲获利
        self.every_time_trade_share = 50 # 33 测试环境下要求小数点后面3位精度，买10u的话只要0.000304左右，四舍五入就是0.000了，这样买不上
        self.cut_position_threshold = 0.5 # 0.2为亏损到本金的2成仓位时，割肉
        self.quantity = 0.02
        self.leverage = 20
        self.position_side = 'BOTH'  # 切换网格的方向，BOTH:多空对冲网格， LONG：做多网格， SHORT：做空网格
        self.long_bottom_position_share = 0.05 #底仓的仓位成数， 0.2代表两成
        self.start_grid = False
        self.terminate = False
        self.ease_position_share = 50 #多空单都超过8个时，掐掉一些，减少持仓数量
        self.crazy_build = False



fc = flaskConfig()
@app.route('/grid/terminate')
def grid_terminate():
    fc.terminate=True
    return 'hzp, /grid/terminate flask!'

@app.route('/grid/stop')
def grid_stop():
    fc.stop_singal_from_client=True
    return 'hzp, /grid/stop!'

@app.route('/grid/update_position_list')
def grid_update_position_list():
    fc.update_position_list_signal_from_client=True
    return 'hzp, /grid/update_position_list!'

@app.route('/grid/change/params', methods=['GET'])
def grid_change_params():
    param1 = ''
    param2 = ''
    try:
        # data = request.get_json()
        param1 = str(request.args.get('ratio_up_or_down'))
        param2 = str(request.args.get('ratio_no_trendency'))
        if param1:
            fc.ratio_up_or_down = float(param1)
        if param2:
            fc.ratio_no_trendency = float(param2)
        if param1 or param2:
            fc.change_ratio_singal_from_client = True
    except RuntimeError as e:
        print(str(e))
    return 'hzp, /change/params, ratio_up_or_down:' + param1 + ', ratio_no_trendency:' + param2

@app.route('/grid/change/every_time_trade_share', methods=['GET'])
def grid_change_trade_share():

    # data = request.get_json()
    every_time_trade_share = ''
    try:
        every_time_trade_share = str(request.args.get('every_time_trade_share'))
        if every_time_trade_share:
            fc.every_time_trade_share = float(every_time_trade_share)
            fc.change_every_time_trade_share_signal_from_client=True
    except RuntimeError as e:
        print(str(e))
    return 'hzp, /change/every_time_trade_share, every_time_trade_share:' + every_time_trade_share

@app.route('/grid/change/quantity', methods=['GET'])
def grid_change_quantity():

    # data = request.get_json()
    quantity = ''
    try:
        quantity = str(request.args.get('quantity'))
        if quantity:
            fc.quantity = float(quantity)
            fc.change_quantity_singal_from_client=True
    except RuntimeError as e:
        print(str(e))
    return 'hzp, /change/trade_share, quantity:' + quantity

@app.route('/grid/change/long_bottom_position_share', methods=['GET'])
def grid_change_long_bottom_position_share():
    # data = request.get_json()
    quantity = ''
    try:
        long_bottom_position_share = str(request.args.get('long_bottom_position_share'))
        if long_bottom_position_share:
            fc.long_bottom_position_share = float(long_bottom_position_share)
            fc.change_long_bottom_position_share_singal_from_client=True
    except RuntimeError as e:
        print(str(e))
    return 'hzp, /change/long_bottom_position_share, long_bottom_position_share:' + long_bottom_position_share

@app.route('/grid/change/position_side', methods=['GET'])
def grid_change_position_side():
    # data = request.get_json()
    position_side = ''
    try:
        position_side = str(request.args.get('position_side'))
        if position_side:
            fc.position_side = position_side
            fc.change_position_side_singal_from_client=True
    except RuntimeError as e:
        print(str(e))
    return 'hzp, /change/position_side, position_side:' + position_side

@app.route('/grid/change/leverage', methods=['GET'])
def grid_change_leverage():

    # data = request.get_json()
    leverage = str(request.args.get('leverage'))
    if leverage:
        fc.leverage = int(leverage)
    return 'hzp, /change/leverage, leverage:' + leverage

@app.route('/grid/change/cut_position_threshold', methods=['GET'])
def grid_change_cut_position_threshold():

    # data = request.get_json()
    cut_position_threshold = str(request.args.get('cut_position_threshold'))
    if cut_position_threshold:
        fc.cut_position_threshold = float(cut_position_threshold)
        fc.cut_position_threshold_singal_from_client = True
    return 'hzp, /change/cut_position_threshold, cut_position_threshold:' + cut_position_threshold

@app.route('/grid/change/ease_position_share', methods=['GET'])
def grid_change_ease_position_share():

    # data = request.get_json()
    ease_position_share = str(request.args.get('ease_position_share'))
    if ease_position_share:
        fc.ease_position_share = float(ease_position_share)
        fc.ease_position_share_singal_from_client = True
    return 'hzp, /change/ease_position_share, ease_position_share:' + ease_position_share

@app.route('/grid/change/long_buy_ratio_scale', methods=['GET'])
def grid_change_long_buy_ratio_scale():

    # data = request.get_json()
    long_buy_ratio_scale = str(request.args.get('long_buy_ratio_scale'))
    if long_buy_ratio_scale:
        fc.long_buy_ratio_scale = float(long_buy_ratio_scale)
        fc.long_buy_ratio_scale_singal_from_client = True
    return 'hzp, /change/long_buy_ratio_scale, long_buy_ratio_scale:' + long_buy_ratio_scale

@app.route('/grid/change/crazy_build', methods=['GET'])
def crazy_buy():
    try:
        fc.crazy_build = True
    except RuntimeError as e:
        print(str(e))
    return 'hzp, /change/crazy_build, crazy_build'

@app.route('/grid/start', methods=['GET'])
def grid_start():
    try:
        fc.start_grid = True
    except RuntimeError as e:
        print(str(e))
    return 'hzp, /change/start, start_grid'


    #todo
    # error_raw = ''
    # try:
    #     config.loads('../config.json')
    #     # dynamicConfig.loads('./config.json')
    #
    #     hengedGrid = HengedGrid()
    #     receiver_thread = threading.Thread(target=hengedGrid.open_receiver)
    #     receiver_thread.start()
    #     exit_thread = threading.Thread(target=hengedGrid.normal_exit)
    #     exit_thread.start()
    #     hengedGrid.run()
    #     receiver_thread.join()
    #     exit_thread.join()
    #
    # except Exception as e:
    #     print('出现异常了:' + str(e))
    #     error_raw = '出现异常了:' + str(e)
    # except BaseException as be:
    #     if isinstance(be, KeyboardInterrupt):
    #         print('ctrl + c 程序中断了')
    #         error_raw = 'ctrl + c 程序中断了' + str(be)
    # finally:
    #     if error_raw:
    #         error_info = "报警：币种{coin},服务停止.错误原因{info}".format(coin=config.symbol, info=str(error_raw))
    #         Message.dingding_warn(str(error_info))
    return 'hzp, /grid/start!'

if __name__ == '__main__':
    app.run(host='104.225.143.245',
            port=5001,
            debug=True)