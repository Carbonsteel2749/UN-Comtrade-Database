# 多线程获取2014-2025年20个国家向中国出口机器人的贸易数据（UN Comtrade）
# 数据来源：联合国商品贸易统计数据库
# 参考网站：https://www.cnblogs.com/chenyangqit/p/16594946.html#:~:text=Python%E7%88%AC%E8%99%AB%E4%B9%8B%E5%A4%9A

import pandas as pd
import time
import os
import threading
import random
import comtradeapicall
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
 

BASE_DIR = "C:\\Users\\18610\\Desktop\\数字贸易统计\\UN_Comtrade\\fetch_robots"
REPORTER_CSV = BASE_DIR + "\\reporters.csv"
OUTPUT_DIR = BASE_DIR + "\\data"

# 加载 API 密钥
ENV_PATH = r"C:\Users\18610\Desktop\数字贸易统计\UN_Comtrade\.venv\.env"
load_dotenv(ENV_PATH)
SUBSCRIPTION_KEY = os.getenv("API_KEY")

if not SUBSCRIPTION_KEY:
    raise ValueError("未找到 API_KEY，请检查 .env 文件路径和变量名")
print(f"API 密钥加载成功: {SUBSCRIPTION_KEY[:8]}...")

start_year = 2014
end_year = 2025
periods = [str(i) for i in range(start_year, end_year + 1)]
periods_str = ','.join(periods)

# 读取 reporters.csv，返回20个出口国编码列表
df = pd.read_csv(REPORTER_CSV)
reporters = df['id'].astype(str).str.strip().tolist()   # 将 id 列转换为字符串并去除空格
print(f'共读取 {len(reporters)} 个出口国: {",".join(reporters)}')   # 打印读取的出口国数量和列表

ROBOT_CODES = ['851531', '847950', '851521', '851580',
               '842489', '842890', '848640']
robots = ','.join(ROBOT_CODES)

def fetch_by_year(year):
    """获取每年所有国家的数据"""
    results = []
    print(f'正在获取 {year} 年全部国家的数据...')
    
    reporter_codes = ','.join(reporters)
    mydf = comtradeapicall.getFinalData(SUBSCRIPTION_KEY, typeCode='C', freqCode='A', clCode='HS', period=year,
                                        reporterCode=reporter_codes, cmdCode=robots, flowCode='X', partnerCode=156,
                                        partner2Code=None, customsCode=None, motCode=None, maxRecords=250000,
                                        format_output='JSON', aggregateBy=None, breakdownMode='classic',
                                        countOnly=None, includeDesc=True)
    
    if mydf is not None and not mydf.empty:
        results.append(mydf)
        print(f'✓ {year} 年: {len(mydf)} 条')
    else:
        print(f'○ {year} 年: 无数据')

    time.sleep(2) 
        
    return results


if __name__ == '__main__':

    start_time = time.time()
    results = []
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
    