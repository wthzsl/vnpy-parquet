import cnlunar
import pandas as pd
from datetime import datetime, timedelta

def get_lunar_info(dt):
    """
    返回公历日期时间 dt 对应的年、月、日干支。
    dt 必须是 datetime 对象（包含时间），例如 datetime(2024,2,4,12,0)
    """
    lunar = cnlunar.Lunar(dt, godType='8char')  # 使用八字模式获取干支
    year_gz = lunar.year8Char   # 年干支，如 "甲子"
    month_gz = lunar.month8Char # 月干支，如 "丙寅"
    day_gz = lunar.day8Char     # 日干支，如 "甲午"
    return year_gz, month_gz, day_gz

# 计算近十年的起止日期（以今天为终点）
end_date = datetime.now().date()
start_date = end_date - timedelta(days=10*365)  # 粗略十年，可根据需要精确调整

# 生成日期范围，时间统一设为 12:00（避免午夜边界问题）
dates = pd.date_range(start_date, end_date, freq='D', tz=None)

records = []
for dt in dates:
    # dt 是 pandas Timestamp，转换为 Python datetime 以确保兼容性
    dt_datetime = dt.to_pydatetime()  # 默认时间是 00:00，但 cnlunar 需要 hour，设置为 12:00 可避免可能的时辰影响
    # 建议将时间设为 12:00 以避开子时可能引起的日干支分歧（对于日干支，时辰不影响，但稳妥起见）
    dt_datetime = dt_datetime.replace(hour=12, minute=0, second=0, microsecond=0)
    
    y, m, d = get_lunar_info(dt_datetime)
    records.append([dt.date(), y, m, d, dt.year])

# 构建 DataFrame
df = pd.DataFrame(records, columns=['date', 'year_gz', 'month_gz', 'day_gz', 'year'])

# 保存为 Parquet，按 year 分区
df.to_parquet('data/tgdz_data.parquet', partition_cols=['year'], engine='pyarrow')
print("数据已生成并保存至 tgdz_data.parquet（按年分区）")