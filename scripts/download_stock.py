# scripts/download_stock.py
import akshare as ak
import pandas as pd
from pathlib import Path
from datetime import datetime
import time

def download_stock_minute(symbol: str, stock_name: str = "", start_date: str = "20240101"):
    """
    下载单只股票的分钟数据并保存为Parquet（按月分片）
    
    Args:
        symbol: 股票代码，如 "000001"
        stock_name: 股票名称，仅用于显示
        start_date: 开始日期，格式 "YYYYMMDD"
    """
    print(f"\n========== 开始下载 {symbol} {stock_name} ==========")
    
    # 构建AKShare的股票代码格式
    if symbol.startswith('6'):
        aksymbol = f"sh{symbol}"
        exchange = "SSE"
    else:
        aksymbol = f"sz{symbol}"
        exchange = "SZSE"
    
    try:
        # 下载数据
        print(f"正在从AKShare获取数据...")
        df = ak.stock_zh_a_minute(
            symbol=aksymbol,
            period='1',
            adjust='qfq'  # 前复权
        )
        
        if df.empty:
            print(f"警告：{symbol} 返回数据为空")
            return
        
        print(f"获取到原始数据 {len(df)} 条")
        
        # 重命名列以符合我们的标准
        df = df.rename(columns={
            'day': 'datetime',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'amount': 'amount'
        })
        
        # 添加股票代码列
        df['code'] = symbol
        
        # 确保datetime是datetime类型
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        # 按开始日期过滤
        df = df[df['datetime'] >= pd.to_datetime(start_date)]
        
        if df.empty:
            print(f"警告：{symbol} 在 {start_date} 之后无数据")
            return
        
        # 按月份分组保存
        df['year'] = df['datetime'].dt.year.astype(str)
        df['month'] = df['datetime'].dt.month.astype(str).str.zfill(2)
        
        for (year, month), group in df.groupby(['year', 'month']):
            # 创建保存目录
            save_dir = Path(f"data/stocks/{symbol}/{year}")
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # 保存路径
            save_path = save_dir / f"{month}.parquet"
            
            # 如果文件已存在，可以选择覆盖或追加
            # 这里简单起见，直接覆盖（因为我们是初次下载）
            group_to_save = group.drop(columns=['year', 'month'])
            group_to_save.to_parquet(save_path, index=False)
            
            print(f"已保存: {save_path} | {len(group)} 条 | "
                  f"{group['datetime'].min().strftime('%Y-%m-%d')} 至 {group['datetime'].max().strftime('%Y-%m-%d')}")
        
        print(f"✅ {symbol} 下载完成\n")
        
    except Exception as e:
        print(f"❌ {symbol} 下载失败: {str(e)}")
        # 打印更详细的错误信息以便调试
        import traceback
        traceback.print_exc()

def download_sample_stocks():
    """下载几只样本股票用于测试"""
    
    # 股票列表：代码、名称、开始日期
    stocks = [
        ("000001", "平安银行", "20240101"),
        ("000002", "万科A", "20240101"),
        ("600519", "贵州茅台", "20240101"),
        ("000858", "五粮液", "20240101"),
    ]
    
    for symbol, name, start in stocks:
        download_stock_minute(symbol, name, start)
        # AKShare有频率限制，暂停2秒避免被封
        time.sleep(2)
    
    print("\n========== 全部下载任务完成 ==========")

if __name__ == "__main__":
    # 先测试单只股票
    download_stock_minute("000001", "平安银行", "20240101")
    
    # 或者下载多只
    #download_sample_stocks()