# scripts/parquet_database.py
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import pandas as pd
from vnpy.event import EventEngine
from vnpy.trader.database import BaseDatabase, BarData, TickData
from vnpy.trader.object import BarData, TickData
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.utility import load_json, save_json
import traceback

# 数据存放根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_ROOT = PROJECT_ROOT / "data" / "daily"


class ParquetDatabase(BaseDatabase):
    """基于 Parquet 文件的数据库接口（只读）"""

    def __init__(
        self,        
        event_engine: Optional[EventEngine] = None,
        gateway_name: Optional[str] = None,
        main_engine: Optional[object] = None,):
        """
        初始化数据库

        :param event_engine: 事件引擎（本系统不需要，忽略）
        :param gateway_name: 网关名称（本系统不需要，忽略）
        :param main_engine: 主引擎引用（本系统不需要，忽略）
        """
        # 确保数据目录存在
        DATA_ROOT.mkdir(parents=True, exist_ok=True)
        print(f"ParquetDatabase 初始化完成，数据目录: {DATA_ROOT}")


    @property
    def default_name(self) -> str:
        """
        数据库的默认名称（必须实现）
        """
        return "PARQUET"
    def load_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime,
        ) -> List[BarData]:

        # 打印调用堆栈的前3层
        # 仅支持日线
        if interval != Interval.DAILY:
            return []

        # 构建股票数据目录：DATA_ROOT / symbol
        stock_dir = DATA_ROOT / symbol
        if not stock_dir.exists():
            return []

        # 获取该股票下所有年份的 parquet 文件
        parquet_files = list(stock_dir.glob("*.parquet"))
        if not parquet_files:
            return []

        # 读取所有年份文件并合并
        dfs = []
        for file_path in parquet_files:
            try:
                df = pd.read_parquet(file_path)
                dfs.append(df)
            except Exception as e:
                print(f"警告：读取文件 {file_path} 失败，错误：{e}")
                continue

        if not dfs:
            return []

        # 合并数据
        data = pd.concat(dfs, ignore_index=True)

        # 确保 datetime 列为 datetime 类型
        data["datetime"] = pd.to_datetime(data["datetime"])

        # 按时间范围过滤
        mask = (data["datetime"] >= start) & (data["datetime"] <= end)
        data = data.loc[mask]

        # 按时间排序
        data = data.sort_values("datetime")

        # 转换为 BarData 对象列表
        bars: List[BarData] = []
        for _, row in data.iterrows():
            bar = BarData(
                symbol=symbol,
                exchange=exchange,
                datetime=row["datetime"].to_pydatetime(),
                interval=interval,
                open_price=float(row["open"]),
                high_price=float(row["high"]),
                low_price=float(row["low"]),
                close_price=float(row["close"]),
                volume=float(row["volume"]),
                turnover=float(row["amount"]),
                gateway_name="PARQUET",
            )
            bars.append(bar)
        return bars
    
    def save_bar_data(self, bars: List[BarData]) -> bool:
        """
        保存 K 线数据（本系统只读，无需实现）
        """
        return True

    def delete_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval
    ) -> int:
        """
        删除 K 线数据（本系统不支持，返回 0）
        """
        return 0

    def load_tick_data(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime,
    ) -> List[TickData]:
        """加载 Tick 数据（本系统不支持，返回空列表）"""
        return []

    def save_tick_data(self, ticks: List[TickData]) -> bool:
        """保存 Tick 数据（本系统不支持，返回 True）"""
        return True

    def delete_tick_data(
        self,
        symbol: str,
        exchange: Exchange
    ) -> int:
        """删除 Tick 数据（本系统不支持，返回 0）"""
        return 0

    def get_bar_overview(self):
        """获取 K 线数据概览（本系统不支持，返回空列表）"""
        return []

    def get_tick_overview(self):
        """获取 Tick 数据概览（本系统不支持，返回空列表）"""
        return []
