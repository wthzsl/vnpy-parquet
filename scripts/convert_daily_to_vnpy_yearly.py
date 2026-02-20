# scripts/batch_convert_to_yearly.py
import pandas as pd
from pathlib import Path
from tqdm import tqdm

# ========== 配置 ==========
SOURCE_ROOT = Path("data/daily")          # 原始数据根目录
TARGET_ROOT = Path("data/yearly")         # 目标数据根目录

# 需要保留的额外列（请根据你的实际列名修改）
EXTRA_COLUMNS = [
    "振幅",
    "pct_chg",
    "change",
    "turnover"
]
# =========================

# 核心列（vn.py 回测必需）
CORE_COLUMNS = ["datetime", "open", "high", "low", "close", "volume", "amount"]

# 重命名映射（将原始列名映射为英文核心列名）
RENAME_MAP = {
    "date": "datetime",
    "股票代码": "code",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
    "amount": "amount"
    # 其他列（如额外列）保持原名，不在此映射
}

# 确保目标根目录存在
TARGET_ROOT.mkdir(parents=True, exist_ok=True)

# 遍历所有股票代码目录
stock_dirs = [d for d in SOURCE_ROOT.iterdir() if d.is_dir()]
print(f"找到 {len(stock_dirs)} 个股票代码目录")

for stock_dir in tqdm(stock_dirs, desc="处理股票"):
    stock_code = stock_dir.name
    
    # 遍历该股票下的年份目录
    year_dirs = [d for d in stock_dir.iterdir() if d.is_dir()]
    for year_dir in year_dirs:
        year = year_dir.name
        source_file = year_dir / "daily.parquet"
        
        if not source_file.exists():
            print(f"警告：{source_file} 不存在，跳过")
            continue
        
        # 读取数据
        try:
            df = pd.read_parquet(source_file)
        except Exception as e:
            print(f"读取 {source_file} 失败：{e}")
            continue
        
        # 重命名列（仅重命名存在的列）
        rename_actual = {k: v for k, v in RENAME_MAP.items() if k in df.columns}
        df.rename(columns=rename_actual, inplace=True)
        
        # 确保 datetime 列存在且为 datetime 类型
        if "datetime" not in df.columns:
            print(f"警告：{source_file} 缺少 datetime 列，跳过")
            continue
        df["datetime"] = pd.to_datetime(df["datetime"])
        
        # 构建最终要保存的列：核心列 + 额外列（只保留存在的列）
        save_columns = CORE_COLUMNS + [col for col in EXTRA_COLUMNS if col in df.columns]
        # 去重（防止重复列名）
        save_columns = list(dict.fromkeys(save_columns))
        
        # 检查核心列是否都存在
        missing_core = [col for col in CORE_COLUMNS if col not in df.columns]
        if missing_core:
            print(f"警告：{source_file} 缺少核心列 {missing_core}，跳过")
            continue
        
        # 构建目标文件路径：data/yearly/{stock_code}/{year}.parquet
        target_dir = TARGET_ROOT / stock_code
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / f"{year}.parquet"
        
        # 保存
        df[save_columns].to_parquet(target_file, index=False)

print("批量转换完成！")