# strategies/daily_ma_cross.py
from vnpy_ctastrategy import (
    CtaTemplate,
    BarData,
    ArrayManager
)

class DailyMaCrossStrategy(CtaTemplate):
    """日线双均线交叉策略"""
    author = "deepseek"

    # 策略参数（可通过外部设置修改）
    fast_window = 5
    slow_window = 20

    # 策略变量
    fast_ma = 0.0
    slow_ma = 0.0

    def on_init(self):
        print("策略初始化...")
        """策略初始化"""
        self.am = ArrayManager(self.slow_window * 2)  # 缓存足够的数据
        self.load_bar(30)  # 加载30根日线用于预热

    def on_bar(self, bar: BarData):
        print(f"📊 on_bar 收到: {bar.datetime} 收盘价: {bar.close_price}")

        """处理新K线"""
        # 更新ArrayManager
        self.am.update_bar(bar)
        if not self.am.inited:
            return

        # 计算均线
        fast_ma = self.am.sma(self.fast_window)
        slow_ma = self.am.sma(self.slow_window)

        # 均线金叉：快线上穿慢线，开多
        if fast_ma > slow_ma and self.pos == 0:
            self.buy(bar.close_price, 100)  # 买入100股

        # 均线死叉：快线下穿慢线，平多
        elif fast_ma < slow_ma and self.pos > 0:
            self.sell(bar.close_price, abs(self.pos))

    def on_trade(self, trade):
        """成交回调（可选）"""
        self.write_log(f"成交：{trade.direction}，数量：{trade.volume}，价格：{trade.price}")
