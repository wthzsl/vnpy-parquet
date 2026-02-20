# scripts/parquet_datafeed.py
from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.object import HistoryRequest
from vnpy.trader.constant import Interval
from parquet_database import ParquetDatabase
from typing import List, Optional

class ParquetDatafeed(BaseDatafeed):
    def __init__(self):
        self.database = ParquetDatabase()

    def query_bar_history(self, req: HistoryRequest) -> Optional[List]:
        print(f"📊 [ParquetDatafeed] 收到请求: {req.symbol}, {req.interval}, {req.start} - {req.end}")
        interval_map = {
            '1m': Interval.MINUTE,
            '1h': Interval.HOUR,
            'd': Interval.DAILY,
        }
        vnpy_interval = interval_map.get(req.interval)
        if not vnpy_interval:
            print(f"不支持的周期: {req.interval}")
            return None
        bars = self.database.load_bar_data(
            symbol=req.symbol,
            exchange=req.exchange,
            interval=vnpy_interval,
            start=req.start,
            end=req.end
        )
        print(f"📊 [ParquetDatafeed] 返回 {len(bars)} 条数据")
        return bars