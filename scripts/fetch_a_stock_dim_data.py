import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
import time
import os
import warnings
warnings.filterwarnings('ignore')



# -------------------------------
# 1. 获取所有A股代码和简称（主名单）
# -------------------------------
print("正在获取A股主名单...")
main_df = ak.stock_info_a_code_name()
print(f"共获取到 {len(main_df)} 只股票。")

# 测试模式：只取前10只（正式运行时注释掉）
# main_df = main_df.head(10)

# -------------------------------
# 2. 获取所有申万三级行业代码列表
# -------------------------------
print("正在获取申万三级行业列表...")
sw_third_info = ak.sw_index_third_info()
industry_code_list = sw_third_info['行业代码'].tolist()
print(f"获取到 {len(industry_code_list)} 个申万三级行业。")

# -------------------------------
# 3. 遍历每个三级行业，获取成分股，构建股票-申万行业映射
# -------------------------------
print("正在获取申万三级行业成分股...")
sw_industry_records = []  # 用于存储股票-行业记录

for idx, industry_code in enumerate(industry_code_list):
    print(f"处理行业 {idx+1}/{len(industry_code_list)}: {industry_code}")
    try:
        cons_df = ak.sw_index_third_cons(symbol=industry_code)
        if cons_df.empty:
            continue

        # 提取需要的列：股票代码、申万1级、申万2级、申万3级
        for _, row in cons_df.iterrows():
            stock_code_raw = row['股票代码']          # 纯数字，如 '600000'
            # 转换为带后缀的格式（与主名单一致，但主名单是带后缀的，需要统一）
            # 这里我们统一使用纯数字作为关联键（去掉后缀）
            stock_code = str(stock_code_raw).strip()
            
            industry_l1 = row.get('申万1级', None)
            industry_l2 = row.get('申万2级', None)
            industry_l3 = row.get('申万3级', None)

            # 记录三级行业
            if pd.notna(industry_l3):
                sw_industry_records.append({
                    'stock_code': stock_code,
                    'industry_standard': 'sw',
                    'industry_level': 'L3',
                    'industry_name': str(industry_l3).strip(),
                    'is_current': True
                })
            # 记录二级行业
            if pd.notna(industry_l2):
                sw_industry_records.append({
                    'stock_code': stock_code,
                    'industry_standard': 'sw',
                    'industry_level': 'L2',
                    'industry_name': str(industry_l2).strip(),
                    'is_current': True
                })
            # 记录一级行业
            if pd.notna(industry_l1):
                sw_industry_records.append({
                    'stock_code': stock_code,
                    'industry_standard': 'sw',
                    'industry_level': 'L1',
                    'industry_name': str(industry_l1).strip(),
                    'is_current': True
                })
    except Exception as e:
        print(f"  获取行业 {industry_code} 成分股失败: {e}")
        continue

    time.sleep(0.3)  # 礼貌性延时

print(f"申万行业成分股记录共 {len(sw_industry_records)} 条。")

# -------------------------------
# 4. 遍历股票，获取详细基础信息和概念板块
# -------------------------------
basic_list = []          # 用于存储基础信息
concept_records = []     # 用于存储概念板块记录

print("开始遍历股票获取详细信息...")
for idx, row in main_df.iterrows():
    code_raw = row['code']          # 如 '600000.SH'
    name = row['name']
    # 提取纯数字部分作为关联键
    stock_code = code_raw.split('.')[0]
    print(f"处理进度: {idx+1}/{len(main_df)} - {code_raw} ({stock_code}) {name}")

    # 4.1 初始化基础信息字典
    basic = {
        'stock_code': stock_code,   # 使用纯数字作为主键
        'code_with_suffix': code_raw,  # 保留原始带后缀的代码，便于关联行情文件夹
        'name': name,
        'full_name': None,
        'list_date': None,
        'delist_date': None,
        'established_date': None,
        'registered_addr': None,
        'office_addr': None,
        'province': None,
        'city': None,
        'website': None,
        'profile': None,
        'legal_repr': None,
        'controller_name': None,
        'list_sector': None,
        'exchange': None,
        'total_share': None,
        'circulating_share': None,
        'employees_num': None,
        'updated_date': datetime.today().date()
    }

    # 4.2 根据代码前缀判断交易所和板块
    if code_raw.startswith('6'):
        basic['exchange'] = '上海证券交易所'
        if code_raw.startswith('688'):
            basic['list_sector'] = '科创板'
        else:
            basic['list_sector'] = '主板'
    elif code_raw.startswith('0'):
        basic['exchange'] = '深圳证券交易所'
        basic['list_sector'] = '主板'
    elif code_raw.startswith('3'):
        basic['exchange'] = '深圳证券交易所'
        basic['list_sector'] = '创业板'
    elif code_raw.startswith('8') or code_raw.startswith('4'):
        basic['exchange'] = '北京证券交易所'
        basic['list_sector'] = '北交所'
    else:
        basic['exchange'] = '其他'
        basic['list_sector'] = '其他'

    # 4.3 调用东方财富个股信息接口获取详细数据
    try:
        info = ak.stock_individual_info_em(symbol=code_raw)
        info_dict = pd.Series(info['value'].values, index=info['item']).to_dict()

        # 打印实际返回的字段，便于调试（可选）
        # print(info_dict.keys())

        # 填充基础信息（使用可能存在的字段名）
        basic['full_name'] = info_dict.get('公司名称')
        list_date_str = info_dict.get('上市时间')
        if list_date_str and list_date_str != '-':
            # 处理多种日期格式
            try:
                basic['list_date'] = pd.to_datetime(list_date_str)
            except:
                pass
        basic['website'] = info_dict.get('公司网址')
        basic['legal_repr'] = info_dict.get('法人代表')
        basic['profile'] = info_dict.get('主营业务')
        
        # 尝试获取注册地址（可能字段名为 '注册地址' 或 '注册地'）
        basic['registered_addr'] = info_dict.get('注册地址') or info_dict.get('注册地')
        
        # 概念板块（可能字段名为 '概念板块' 或 '题材板块'）
        concept_str = info_dict.get('概念板块') or info_dict.get('题材板块')
        if concept_str and concept_str != '-':
            concepts = [c.strip() for c in concept_str.split('，') if c.strip()]
            for c in concepts:
                concept_records.append({
                    'stock_code': stock_code,
                    'industry_standard': 'concept',
                    'industry_level': None,
                    'industry_name': c,
                    'is_current': True
                })
    except Exception as e:
        print(f"  东财接口获取失败: {e}")

    basic_list.append(basic)
    time.sleep(0.2)  # 礼貌性延时

# 将基础信息列表转为DataFrame
basic_df = pd.DataFrame(basic_list)

# -------------------------------
# 5. 合并行业记录（申万 + 概念）并去重
# -------------------------------
industry_records = sw_industry_records + concept_records
industry_df = pd.DataFrame(industry_records)
# 去重（防止同一股票同一标准同一名称重复）
industry_df = industry_df.drop_duplicates(subset=['stock_code', 'industry_standard', 'industry_name'])

# -------------------------------
# 6. 数据清洗与类型调整
# -------------------------------
# 基础表日期处理
basic_df['list_date'] = pd.to_datetime(basic_df['list_date'], errors='coerce')
basic_df['updated_date'] = pd.to_datetime(basic_df['updated_date'])

# 调整基础表列顺序
basic_columns = [
    'stock_code', 'code_with_suffix', 'name', 'full_name', 'list_date', 'delist_date',
    'established_date', 'registered_addr', 'office_addr', 'province', 'city',
    'website', 'profile', 'legal_repr', 'controller_name',
    'list_sector', 'exchange', 'total_share', 'circulating_share',
    'employees_num', 'updated_date'
]
# 只保留存在的列
basic_columns = [col for col in basic_columns if col in basic_df.columns]
basic_df = basic_df[basic_columns]

# 行业表排序
industry_df = industry_df[['stock_code', 'industry_standard', 'industry_level', 'industry_name', 'is_current']]

# -------------------------------
# 7. 保存为Parquet文件
# -------------------------------
basic_parquet_path = 'data/stock_basic.parquet'
industry_parquet_path = 'data/stock_industry.parquet'

basic_df.to_parquet(basic_parquet_path, engine='pyarrow', index=False)
industry_df.to_parquet(industry_parquet_path, engine='pyarrow', index=False)

print(f"基础信息表已保存至: {basic_parquet_path}，共 {len(basic_df)} 条记录。")
print(f"行业分类表已保存至: {industry_parquet_path}，共 {len(industry_df)} 条记录。")

print("\n基础信息表示例：")
print(basic_df.head())
print("\n行业分类表示例：")
print(industry_df.head())
print("\n概念板块示例：")
print(industry_df[industry_df['industry_standard'] == 'concept'].head())