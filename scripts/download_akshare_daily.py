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

def get_mainboard_list():
    """获取所有主板股票代码"""
    print("\n========== 获取主板股票列表 ==========")
    
    # 获取所有A股代码
    df = ak.stock_info_a_code_name()

    
    # 筛选主板
    mainboard = []
    for _, row in df.iterrows():
        code = row['code']  # 修改为实际的列名
        # 沪市主板：6开头（600-605）
        if code.startswith(('600', '601', '603', '605')):
            mainboard.append(row)
        # 深市主板：000、001、002开头
        elif code.startswith(('000', '001', '002')):
            mainboard.append(row)
    
    result = pd.DataFrame(mainboard)
    print(f"主板股票数量：{len(result)}")
    print(f"示例：\n{result.head()}")
    return result

def download_stock_daily(symbol, name):
    """下载单只股票日线数据"""
    try:
        # 检查是否已有数据
        existing_data = None
        last_date = None
        
        # 查找该股票的所有数据文件
        stock_dir = DATA_ROOT / symbol
        if stock_dir.exists():
            parquet_files = list(stock_dir.rglob("*.parquet"))
            if parquet_files:
                # 读取已有数据
                dfs = [pd.read_parquet(f) for f in parquet_files]
                existing_data = pd.concat(dfs).sort_values('date')
                last_date = existing_data['date'].max()
                print(f"  本地已有数据：{len(existing_data)} 条，最新日期：{last_date.date()}")
                
                # 调整起始日期为已有数据的下一天
                start_date = (last_date + timedelta(days=1)).strftime('%Y%m%d')
                print(f"  将从 {start_date} 开始下载增量数据")
            else:
                start_date = START_DATE
        else:
            start_date = START_DATE
        
        # 如果最新日期已经是今天，则无需下载
        if last_date and last_date.date() >= datetime.now().date():
            print(f"  ⚠️ {symbol} {name} 数据已是最新，无需下载")
            return len(existing_data)
        
        print(f"正在下载 {symbol} {name}，时间范围：{start_date} 至 {END_DATE}")
        
        # 下载日线数据
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=END_DATE,
            adjust="qfq"  # 前复权
        )
        
        print(f"下载到 {len(df)} 条数据")
        
        if df.empty:
            if existing_data is not None:
                print(f"  ⚠️ {symbol} {name} 没有新数据")
                return len(existing_data)
            else:
                print(f"  ⚠️ {symbol} {name} 数据为空")
                return None
        
        # 重命名列
        df = df.rename(columns={
            '日期': 'date',
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
        
        # 添加股票代码
        df['code'] = symbol
        
        # 日期处理
        df['date'] = pd.to_datetime(df['date'])
        
        # 如果有已有数据，则合并
        if existing_data is not None:
            # 合并数据
            df = pd.concat([existing_data, df]).drop_duplicates(subset=['date'], keep='last')
            df = df.sort_values('date')
            print(f"  合并后总数据量：{len(df)} 条")
        
        # 打印日期范围
        print(f"  数据日期范围：{df['date'].min()} 至 {df['date'].max()}")
        
        # 按年份分组保存
        df['year'] = df['date'].dt.year.astype(str)
        
        for year, group in df.groupby('year'):
            save_dir = DATA_ROOT / symbol / year
            save_dir.mkdir(parents=True, exist_ok=True)
            save_path = save_dir / 'daily.parquet'
            
            group_to_save = group.drop(columns=['year'])
            group_to_save.to_parquet(save_path, index=False)
            print(f"  保存 {year} 年数据：{len(group_to_save)} 条")
        
        return len(df)
        
    except Exception as e:
        print(f"  ❌ {symbol} {name} 失败: {e}")
        return None



def download_all_mainboard(limit=None):
    """批量下载所有主板股票"""
    # 获取股票列表
    stocks_df = get_mainboard_list()
    
    if limit:
        stocks_df = stocks_df.head(limit)
        print(f"\n⚠️ 测试模式：仅下载前 {limit} 只")
    
    print("\n📥 开始增量下载，将跳过已有数据...")
    
    # 记录结果
    results = []
    
    # 使用tqdm显示进度条
    for idx, row in tqdm(stocks_df.iterrows(), total=len(stocks_df), desc="下载进度"):
        symbol = row['code']  # 修改为实际的列名
        name = row['name']    # 修改为实际的列名
        
        count = download_stock_daily(symbol, name)
        
        if count:
            results.append({'code': symbol, 'name': name, 'rows': count})
        else:
            results.append({'code': symbol, 'name': name, 'rows': 0})
        
        # 控制请求频率
        time.sleep(SLEEP_INTERVAL)
    
    # 统计结果
    df_result = pd.DataFrame(results)
    success = df_result[df_result['rows'] > 0]
    
    print("\n" + "="*50)
    print(f"下载完成！成功：{len(success)} 只，失败：{len(df_result) - len(success)} 只")
    print(f"总数据量：{success['rows'].sum()} 条")
    
    # 保存失败列表
    failed = df_result[df_result['rows'] == 0]
    if not failed.empty:
        failed.to_csv('failed_akshare.csv', index=False)
        print(f"失败列表已保存到 failed_akshare.csv")
    
    return df_result


def check_data():
    """检查已下载数据"""
    if not DATA_ROOT.exists():
        print("数据目录不存在")
        return
    
    stock_dirs = [d for d in DATA_ROOT.iterdir() if d.is_dir()]
    print(f"\n已下载股票数量：{len(stock_dirs)}")
    
    total_rows = 0
    for stock_dir in sorted(stock_dirs)[:10]:  # 只显示前10只
        files = list(stock_dir.rglob("*.parquet"))
        if files:
            df_sample = pd.read_parquet(files[0])
            total_rows += len(df_sample)
            print(f"{stock_dir.name}: {len(files)}个文件，最新数据 {df_sample['date'].max().date()}")
    
    print(f"总计数据量：{total_rows} 条（仅统计前10只）")

if __name__ == "__main__":
    # 1. 先测试单只股票
    # count = download_stock_daily('000001', '平安银行')
    # print(f"平安银行：{count}条")
    
    # 2. 正式下载（建议先 limit=10 测试）
    download_all_mainboard()  # 先下10只试试
    