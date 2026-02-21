import pandas as pd

# 读取 Parquet 文件
df = pd.read_parquet("data\stock_info\stock_basic.parquet")

# 使用 rename 方法重命名列
df.rename(columns={ "name": "stock_name"}, inplace=True)

# 保存为新的 Parquet 文件
df.to_parquet("data/stock_info/stock_basic.parquet")