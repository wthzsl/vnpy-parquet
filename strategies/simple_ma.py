# strategies/simple_ma.py
from vnpy_ctastrategy import CtaTemplate, BarData, ArrayManager
from vnpy.trader.constant import Interval

class SimpleMaStrategy(CtaTemplate):
    author = "test"
    fast_window = 5
    slow_window = 20

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.am = ArrayManager()

    def on_init(self):
        self.load_bar(30, interval=Interval.DAILY)   # 明确指定日线

    def on_bar(self, bar: BarData):
        self.am.update_bar(bar)
        if not self.am.inited:
            return
        fast_ma = self.am.sma(self.fast_window)
        slow_ma = self.am.sma(self.slow_window)
        if fast_ma > slow_ma and self.pos == 0:
            self.buy(bar.close_price, 100)
        elif fast_ma < slow_ma and self.pos > 0:
            self.sell(bar.close_price, abs(self.pos))