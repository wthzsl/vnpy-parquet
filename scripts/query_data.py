import duckdb
from pathlib import Path

# ---------- 路径配置 ----------
project_root = Path(__file__).parent.parent
data_dir = project_root / 'data'

daily_glob = str(data_dir / 'daily' / '*' / '*.parquet')
basic_file = str(data_dir / 'stock_info' / 'stock_basic.parquet')
industry_file = str(data_dir / 'stock_info' / 'stock_industry.parquet')

start_date = '2022-02-04'
end_date = '2022-03-04'

# ---------- DuckDB 连接 ----------
con = duckdb.connect()

# ---------- 第一步：查看实际文件名样例，帮助调试 ----------
filename_sample = con.execute(f"""
SELECT filename 
FROM read_parquet('{daily_glob}', filename = true) 
LIMIT 5
""").df()


# ---------- 第二步：测试股票代码提取 ----------
extract_test = con.execute(f"""
SELECT 
    filename,
    regexp_extract(filename, '[\\\\/]([^\\\\/]+)[\\\\/][^\\\\/]+\\.parquet$', 1) AS stock_code_num
FROM read_parquet('{daily_glob}', filename = true) 
WHERE datetime BETWEEN '{start_date}' AND '{end_date}'
LIMIT 10
""").df()


# ---------- 第三步：查看基础表/行业表样例 ----------
basic_sample = con.execute(f"SELECT stock_code FROM read_parquet('{basic_file}') LIMIT 10").df()


industry_sample = con.execute(f"""
SELECT stock_code, industry_name 
FROM read_parquet('{industry_file}') 
WHERE industry_level = 'L3' AND industry_name != '-' 
LIMIT 10
""").df()
print("\n行业表（三级行业）stock_code 样例：")
print(industry_sample)

# ---------- 第四步：执行完整查询（修正正则，兼容路径分隔符）----------
# 注意：SQL 中的正则需要使用 '\\d+'（因为 Python 字符串中反斜杠需转义）
full_query = f"""
WITH daily_with_path AS (
    SELECT *, filename
    FROM read_parquet('{daily_glob}', filename = true)
    WHERE datetime BETWEEN '{start_date}' AND '{end_date}'
),
daily_with_code AS (
    SELECT 
        datetime, open, high, low, close, volume, amount,
        -- 使用兼容 Windows 和 Linux 的正则提取目录名
        regexp_extract(filename, '[\\\\/]([^\\\\/]+)[\\\\/][^\\\\/]+\\.parquet$', 1) AS stock_code_num
    FROM daily_with_path
),
first_last AS (
    SELECT 
        stock_code_num,
        first(close ORDER BY datetime) AS first_close,
        last(close ORDER BY datetime) AS last_close
    FROM daily_with_code
    GROUP BY stock_code_num
    HAVING COUNT(*) >= 2
),
returns AS (
    SELECT 
        stock_code_num,
        (last_close - first_close) / first_close * 100 AS pct_chg
    FROM first_last
),
top20 AS (
    SELECT stock_code_num, pct_chg
    FROM returns
    ORDER BY pct_chg DESC
    LIMIT 20
)
SELECT 
    t.stock_code_num AS stock_code,
    b.stock_name,
    i.industry_name AS level3_industry,
    ROUND(t.pct_chg, 2) AS pct_chg
FROM top20 t
LEFT JOIN read_parquet('{basic_file}') b 
    ON t.stock_code_num = regexp_extract(b.stock_code, '(\\d+)', 1)   -- 注意这里用 '(\\d+)'
LEFT JOIN read_parquet('{industry_file}') i 
    ON t.stock_code_num = regexp_extract(i.stock_code, '(\\d+)', 1)
    AND i.industry_level = 'L3' 
    AND i.industry_name != '-'
ORDER BY t.pct_chg DESC;
"""

result_df = con.execute(full_query).df()
print("\n最终结果：")
print(result_df)