# 多线程动态IP获取2014-2025年芯片供应链中22种产品的全球双边贸易数据
# 数据来源：联合国商品贸易统计数据库
# 参考网站：https://blog.csdn.net/standingflower/article/details/126843518

import requests
import time
import os
import datetime
import threading
import random
import comtradeapicall
import pandas as pd
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = "C:\\Users\\18610\\Desktop\\数字贸易统计\\UN_Comtrade\\fetch_chips"
REPORTERS_CSV = BASE_DIR + "\\reporters.csv"
PARTNERS_CSV = BASE_DIR + "\\partners.csv"
OUTPUT_DIR = BASE_DIR + "\\data"

# 加载 API 密钥
ENV_PATH = "C:\\Users\\18610\\Desktop\\数字贸易统计\\UN_Comtrade\\.venv\\.env"
load_dotenv(ENV_PATH)
SUBSCRIPTION_KEY = os.getenv("API_KEY")

if not SUBSCRIPTION_KEY:
    raise ValueError("未找到 API_KEY，请检查 .env 文件路径和变量名")
print(f"API 密钥加载成功: {SUBSCRIPTION_KEY[:8]}...")

start_year = 2014
end_year = 2025
periods = [str(i) for i in range(start_year, end_year + 1)]
periods_str = ','.join(periods)

# 读取 reporters.csv，返回出口国编码列表
df = pd.read_csv(REPORTERS_CSV)
df['id'] = df['id'].astype(str).str.strip()  
reporters = dict(zip(df['id'], df['text']))
print(f'共读取 {len(reporters)} 个出口国')
      
CHIP_CODES = ['381800', '370710', '900290', '280429', '848610',
              '848620', '848630', '848690', '854231', '854232',
              '854233', '854151', '854190', '840999', '852721',
              '851713', '847170', '847130', '900190', '851762',
              '847950', '903082']
chips = ','.join(CHIP_CODES)

def chunk_list(lst, n):
    """把列表按每 n 个一组切分，返回二维列表"""
    return [lst[i:i + n] for i in range(0, len(lst), n)]

def fetch_by_year(year):
    """获取每年所有国家的数据"""
    results = []
    print(f'正在获取 {year} 年全部国家的数据...')
    
    for chunk in chunk_list(reporter_ids, 10):  
        # 每次处理10个出口国
        reporter_str = ','.join(chunk)
        reporter_names = ', '.join(reporters[rid] for rid in chunk)
        print(f"\n[year={year}] [reporters={reporter_names}]")
        
        mydf_exp = comtradeapicall.getFinalData(SUBSCRIPTION_KEY, typeCode='C', freqCode='A', clCode='HS', period=year,
                                            reporterCode=reporter_str, cmdCode=chips, flowCode='X', partnerCode='0',
                                            partner2Code=None, customsCode=None, motCode=None, maxRecords=250000,
                                            format_output='JSON', aggregateBy=None, breakdownMode='classic',
                                            countOnly=None, includeDesc=True)
        if mydf_exp is not None and not mydf_exp.empty:
            results.append(mydf_exp)
            print(f'✓ {year} 年: {len(mydf_exp)} 条')
        else:
            print(f'○ {year} 年: 无数据')
    
        mydf_imp = comtradeapicall.getFinalData(SUBSCRIPTION_KEY, typeCode='C', freqCode='A', clCode='HS', period=year,
                                        reporterCode=reporter_str, cmdCode=chips, flowCode='M', partnerCode='0',
                                        partner2Code=None, customsCode=None, motCode=None, maxRecords=250000,
                                        format_output='JSON', aggregateBy=None, breakdownMode='classic',
                                        countOnly=None, includeDesc=True)
        if mydf_imp is not None and not mydf_imp.empty:
            results.append(mydf_imp)
            print(f'✓ {year} 年: {len(mydf_imp)} 条')
        else:
            print(f'○ {year} 年: 无数据')

        time.sleep(2) 
        
    return results


if __name__ == '__main__':

    start_time = time.time()
    results = []
    reporter_ids = list(reporters.keys())
    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="robots") as executor:
        futures = [executor.submit(fetch_by_year, year) for year in periods]
        for future in as_completed(futures):
            df = future.result()
            if df is not None:
                results.append(df)
    
    if results:
        final_df = pd.concat([item for sublist in results for item in sublist], ignore_index=True)
        output_path = OUTPUT_DIR + r"\robots_preview.csv"
        final_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f'已保存 {len(final_df)} 条数据到 {output_path}')
    else:
        print('未获取到任何数据')
        
    elapsed = time.time() - start_time
    print(f"总耗时: {elapsed:.2f} 秒 ({elapsed / 60:.1f} 分钟)")
    print("主线程结束")