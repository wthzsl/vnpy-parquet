# scripts/run_backtest.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from datetime import datetime

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.constant import Interval
from vnpy.trader.setting import SETTINGS
from vnpy_ctabacktester import BacktesterEngine

# 强制替换底层数据加载函数
import vnpy_ctastrategy.backtesting
from parquet_database import ParquetDatabase
from strategies.simple_ma import SimpleMaStrategy

# 屏蔽数据服务警告（不影响回测）
SETTINGS["datafeed.name"] = "dummy"

# ========== 配置 ==========
STOCK_CODE = "605133"
EXCHANGE = "SSE"
VT_SYMBOL = f"{STOCK_CODE}.{EXCHANGE}"
START_DATE = datetime(2022, 1, 1)
END_DATE = datetime(2022, 12, 31)
INIT_CAPITAL = 1_000_000
STRATEGY_PARAMS = {
    "fast_window": 5,
    "slow_window": 20
}
# ==========================

# 创建自定义数据库实例
custom_db = ParquetDatabase()

# 强制替换 backtesting 模块中的 load_bar_data 函数
def my_load_bar_data(symbol, exchange, interval, start, end):
    return custom_db.load_bar_data(symbol, exchange, interval, start, end)

vnpy_ctastrategy.backtesting.load_bar_data = my_load_bar_data
print("✅ 数据接口已替换为 ParquetDatabase")

# 初始化引擎
event_engine = EventEngine()
main_engine = MainEngine(event_engine)
engine = BacktesterEngine(main_engine, event_engine)

# 必须调用 init_engine 以创建内部 backtesting_engine
engine.init_engine()
print("✅ 回测引擎初始化完成")

# 加载策略类
engine.classes["SimpleMaStrategy"] = SimpleMaStrategy

# 启动回测
print("开始回测...")
engine.start_backtesting(
    class_name="SimpleMaStrategy",
    vt_symbol=VT_SYMBOL,
    interval="d",
    start=START_DATE,
    end=END_DATE,
    rate=0.0003,
    slippage=0.01,
    size=1,
    pricetick=0.01,
    capital=INIT_CAPITAL,
    setting=STRATEGY_PARAMS
)

# 等待回测完成
timeout = 10
start_wait = time.time()
while time.time() - start_wait < timeout:
    stats = engine.get_result_statistics()
    if stats is not None:
        break
    time.sleep(0.5)

# 输出统计指标
if stats:
    print("\n========== 回测统计 ==========")
    for key, value in stats.items():
        print(f"{key}: {value}")

    # 输出交易记录
    trades = engine.get_all_trades()
    if trades:
        print("\n========== 交易记录 ==========")
        for trade in trades:
            print(f"{trade.datetime} {trade.symbol}.{trade.exchange} {trade.direction} {trade.volume}股 @ {trade.price}")
    else:
        print("\n无交易记录。")

    # 显示曲线（通过 backtesting_engine）
    try:
        if engine.backtesting_engine:
            fig = engine.backtesting_engine.show_chart()
            fig.show()
        else:
            print("回测引擎未就绪，无法显示图表。")
    except Exception as e:
        print(f"无法显示曲线: {e}")
else:
    print("⚠️ 未生成统计结果。")

# 清理
event_engine.stop()
print("回测结束。")