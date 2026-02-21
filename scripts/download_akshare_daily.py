# scripts/download_akshare_daily.py
import akshare as ak
import pandas as pd
from pathlib import Path
import time
from datetime import datetime, timedelta
from tqdm import tqdm

# ========== 配置区 ==========
START_DATE = (datetime.now() - timedelta(days=4*365)).strftime('%Y%m%d')
END_DATE = datetime.now().strftime('%Y%m%d')
DATA_ROOT = Path('data/daily')
SLEEP_INTERVAL = 0.3  # 避免被封
# ===========================

def get_all_a_stocks():
    """获取所有A股股票代码"""
    print("\n========== 获取全部A股股票列表 ==========")
    df = ak.stock_info_a_code_name()
    print(f"全部A股数量：{len(df)}")
    print(f"示例：\n{df.head()}")
    return df

def download_stock_daily(symbol, name):
    """下载单只股票日线数据（适配vnpy格式和本地存储）"""
    try:
        # 检查是否已有数据
        existing_data = None
        last_date = None
        stock_dir = DATA_ROOT / symbol

        if stock_dir.exists():
            # 查找所有年份文件，如 2022.parquet, 2023.parquet ...
            parquet_files = list(stock_dir.glob("*.parquet"))
            if parquet_files:
                dfs = [pd.read_parquet(f) for f in parquet_files]
                existing_data = pd.concat(dfs).sort_values('datetime')
                last_date = existing_data['datetime'].max()
                print(f"  本地已有数据：{len(existing_data)} 条，最新日期：{last_date.date()}")
                
                start_date = (last_date + timedelta(days=1)).strftime('%Y%m%d')
                print(f"  将从 {start_date} 开始下载增量数据")
            else:
                start_date = START_DATE
        else:
            start_date = START_DATE
            stock_dir.mkdir(parents=True, exist_ok=True)

        # 如果最新日期已经是今天，则无需下载
        if last_date and last_date.date() >= datetime.now().date():
            print(f"  ⚠️ {symbol} {name} 数据已是最新，无需下载")
            return len(existing_data) if existing_data is not None else 0

        print(f"正在下载 {symbol} {name}，时间范围：{start_date} 至 {END_DATE}")
        
        # 下载日线数据
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=END_DATE,
            adjust="qfq"  # 前复权
        )

        if df.empty:
            if existing_data is not None:
                print(f"  ⚠️ {symbol} {name} 没有新数据")
                return len(existing_data)
            else:
                print(f"  ⚠️ {symbol} {name} 数据为空")
                return None

        # 重命名列（适配vnpy格式）
        df = df.rename(columns={
            '日期': 'datetime',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume',
            '成交额': 'amount',
            '涨跌幅': 'pct_chg',
            '涨跌额': 'change',
            '换手率': 'turnover'
        })

        # 添加股票代码和交易所
        df['symbol'] = symbol
        # 根据代码前缀判断交易所
        if symbol.startswith(('600', '601', '603', '605', '688')):  # 沪市主板+科创板
            df['exchange'] = 'SSE'
        elif symbol.startswith(('000', '001', '002', '300')):       # 深市主板+创业板
            df['exchange'] = 'SZSE'
        elif symbol.startswith('8'):                                 # 北交所
            df['exchange'] = 'BSE'
        else:
            df['exchange'] = 'OTHER'   # 备用

        # 日期处理
        df['datetime'] = pd.to_datetime(df['datetime'])

        # 合并已有数据（按datetime去重）
        if existing_data is not None:
            df = pd.concat([existing_data, df]).drop_duplicates(subset=['datetime'], keep='last')
            df = df.sort_values('datetime')
            print(f"  合并后总数据量：{len(df)} 条")

        print(f"  数据日期范围：{df['datetime'].min()} 至 {df['datetime'].max()}")

        # 按年份分组保存
        df['year'] = df['datetime'].dt.year.astype(str)
        for year, group in df.groupby('year'):
            save_path = stock_dir / f"{year}.parquet"
            group_to_save = group.drop(columns=['year'])
            group_to_save.to_parquet(save_path, index=False)
            print(f"  保存 {year} 年数据：{len(group_to_save)} 条")

        return len(df)

    except Exception as e:
        print(f"  ❌ {symbol} {name} 失败: {e}")
        return None

def download_all_stocks(stocks_df, limit=None):
    """批量下载股票列表"""
    if limit:
        stocks_df = stocks_df.head(limit)
        print(f"\n⚠️ 测试模式：仅下载前 {limit} 只")

    print("\n📥 开始增量下载...")
    results = []

    for idx, row in tqdm(stocks_df.iterrows(), total=len(stocks_df), desc="下载进度"):
        symbol = row['code']
        name = row['name']
        count = download_stock_daily(symbol, name)
        results.append({'code': symbol, 'name': name, 'rows': count if count else 0})
        time.sleep(SLEEP_INTERVAL)

    df_result = pd.DataFrame(results)
    success = df_result[df_result['rows'] > 0]
    print("\n" + "="*50)
    print(f"下载完成！成功：{len(success)} 只，失败：{len(df_result) - len(success)} 只")
    print(f"总数据量：{success['rows'].sum()} 条")

    failed = df_result[df_result['rows'] == 0]
    if not failed.empty:
        failed.to_csv('failed_akshare.csv', index=False)
        print(f"失败列表已保存到 failed_akshare.csv")

    return df_result

if __name__ == "__main__":
    # 获取所有A股
    all_stocks = get_all_a_stocks()
    
    # 下载所有A股（建议先 limit=10 测试）
    download_all_stocks(all_stocks)  # 可加 limit=10 测试