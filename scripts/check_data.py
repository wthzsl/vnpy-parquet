# scripts/check_data.py

import pandas as pd
from pathlib import Path

# 指定要查看的股票代码
symbol = "000524"  # 例如：平安银行
SOURCE_FILE = f"data/yearly/{symbol}/2024.parquet" 
#SOURCE_FILE =f"data/daily/{symbol}/2022/000514/2022.parquet"
parquet_files=[SOURCE_FILE]
# 查找该股票的所有数据文件
#data_dir = Path(f"data/daily/{symbol}")
#parquet_files = list(data_dir.rglob("*.parquet"))

if parquet_files:
    # 读取所有文件并合并
    dfs = [pd.read_parquet(f) for f in parquet_files]
    df = pd.concat(dfs).sort_values('datetime')

    
    # 显示数据信息
    print(f"股票代码: {symbol}")
    print(f"数据条数: {len(df)}")
    print(f"日期范围: {df['datetime'].min()} 至 {df['datetime'].max()}")
    print("\n数据示例:")
    print(df.head())
    print("\n数据统计:")
    print(df.describe())
else:
    print(f"未找到 {symbol} 的数据文件")
