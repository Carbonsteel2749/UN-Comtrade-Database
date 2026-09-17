# 多线程动态IP获取2014-2025年芯片供应链中22种产品的全球双边贸易数据
# 数据来源：联合国商品贸易统计数据库
# 参考网站：https://blog.csdn.net/standingflower/article/details/126843518

import requests
import time
import os
import datetime
import pandas as pd
import comtradeapicall
from pandas import json_normalize
from random import randint
from io import StringIO
from dotenv import load_dotenv

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

# 代理服务器的配置信息
class proxy:
    proxyHost = "your proxyHost "
    proxyPort = "your proxyPort "
    proxyUser = "your proxyUser "
    proxyPass = "your proxyPass "
    user_agents = [
        "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; AcooBrowser; .NET CLR 1.1.4322; .NET CLR 2.0.50727)",
        "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; Acoo Browser; SLCC1; .NET CLR 2.0.50727; Media Center PC 5.0; .NET CLR 3.0.04506)",
        "Mozilla/4.0 (compatible; MSIE 7.0; AOL 9.5; AOLBuild 4337.35; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)",
        "Mozilla/5.0 (Windows; U; MSIE 9.0; Windows NT 9.0; en-US)",
        "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Win64; x64; Trident/5.0; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 2.0.50727; Media Center PC 6.0)",
        "Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 6.0; Trident/4.0; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 1.0.3705; .NET CLR 1.1.4322)",
        "Mozilla/4.0 (compatible; MSIE 7.0b; Windows NT 5.2; .NET CLR 1.1.4322; .NET CLR 2.0.50727; InfoPath.2; .NET CLR 3.0.04506.30)",
        "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN) AppleWebKit/523.15 (KHTML, like Gecko, Safari/419.3) Arora/0.3 (Change: 287 c9dfb30)",
        "Mozilla/5.0 (X11; U; Linux; en-US) AppleWebKit/527+ (KHTML, like Gecko, Safari/419.3) Arora/0.6",
        "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.2pre) Gecko/20070215 K-Ninja/2.1.1",
        "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9) Gecko/20080705 Firefox/3.0 Kapiko/3.0",
        "Mozilla/5.0 (X11; Linux i686; U;) Gecko/20070322 Kazehakase/0.4.5",
        "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.8) Gecko Fedora/1.9.0.8-1.fc10 Kazehakase/0.5.6",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_3) AppleWebKit/535.20 (KHTML, like Gecko) Chrome/19.0.1036.7 Safari/535.20",
        "Opera/9.80 (Macintosh; Intel Mac OS X 10.6.8; U; fr) Presto/2.9.168 Version/11.52"]
    
    #调用数据获取函数，使用proxy，防止获取数据时ip被封禁
    def __init__(self, proxyHost, proxyPort, proxyUser, proxyPass, user_agents):
        self.proxyHost = proxyHost
        self.proxyPort = proxyPort
        self.proxyUser = proxyUser
        self.proxyPass = proxyPass
        self.user_agents = user_agents
        proxyMeta = "http://%(user)s:%(pass)s@%(host)s:%(port)s" % {
            "host": proxyHost,
            "port": proxyPort,
            "user": proxyUser,
            "pass": proxyPass,
        }
        self.proxies = {
            "http": proxyMeta,
            "https": proxyMeta,
        }
    
    
def download_url(url,  ifuse_proxy = False ,proxy = None):
    # 生成代理请求头
    if(ifuse_proxy):
        random_agent = proxy.user_agents[randint(0, len(proxy.user_agents) - 1)]		# chose an user agent from the user agent list above
        tunnel = randint(1, 10000)  # generate a random tunnel
        header = {
            "Proxy-Tunnel": str(tunnel),
            "User-Agent": random_agent
        }
        print(header,proxy.proxies)
 
    try:
        if(ifuse_proxy):
            # 发送 GET 请求
            content = requests.get(url, timeout=100,headers = header, proxies=proxy.proxies)
        else:
            content = requests.get(url, timeout=100, proxies=proxy)
        ''' note that sometimes we only get error informations in the responses, and here are some really dumb quick fixes'''
        if (
                content.text == "<html><body><h1>502 Bad Gateway</h1>\nThe server returned an invalid or incomplete response.\n</body></html>\n" or content.text == "Too Many Requests.\n" or content.text == "{\"Message\":\"An error has occurred.\"}"):
            with open("./uncomtrade_data/serverError.csv", 'a', encoding="utf-8") as log:
                log.write(str(datetime.datetime.now()) + "," + str(url) + "\n")
                print("\n" + content.content.decode())
                if(ifuse_proxy):
                    download_url(url,ifuse_proxy = True , proxy = proxy)
                else:
                    download_url(url,ifuse_proxy = False , proxy = None)
        else:
            if ('json' in url) or (url.endswith('json')):   # 新版 URL 不带 json 后缀
                resp_json = content.json()
                if 'dataset' in resp_json:
                    return json_normalize(resp_json['dataset'])
                elif 'data' in resp_json:
                    return pd.DataFrame(resp_json['data'])
                else:
                    print("未知返回格式:", str(resp_json)[:200])
                    return None
            elif ('csv' in url):
                return pd.read_csv(StringIO(content.text), on_bad_lines='skip')
            
    except requests.RequestException as e:
        ''' I have absolutely no knowledge about Request Exception Handling so I chose to write the error information to a log file'''
        print(type(e).__name__ + " has occurred, change proxy!")
#         if(type(e).__name__=='JSONDecodeError'):
#             print(content.content)
        with open("./uncomtrade_data/exp.csv", 'a', encoding="utf-8") as log:
            log.write(
                str(datetime.datetime.now()) + "," + str(type(e).__name__) + "," + str(url) + "\n")
        if(ifuse_proxy):
            download_url(url,ifuse_proxy = True , proxy = proxy)
        else:
            download_url(url,ifuse_proxy = False , proxy = None)
 
def get_data_un_comtrade(typeCode = 'C',freqCode = 'A', clCode = 'HS',subscription_key = SUBSCRIPTION_KEY,format = 'json',flowCode = 'X',reporterCode = '156',period = '2021',cmdCode = 'TOTAL',partnerCode = '0',ifuse_proxy = False ,proxy = None):
    '''
    typeCode:选择贸易类型，C为商品贸易，S为服务贸易；
    freqCode:选择数据频率，A为年度，M为月度；
    clCode:选择分类标准，HS为海关编码；
    subscription-key: API_KEY；
    format:选择输出文件格式，csv或json,默认使用json(实测中csv更快)；
    flowCode:选择进口或出口（进口为1，出口为2）；
    reporterCode:选择所需要的出口国；
    period:选择所需要的年份；
    cmdCode:选择分类标准，如常用的SITC Revision 3为S3；
    partnerCode:选择所需要的对象国家，如需要中国与俄罗斯的出口额，则目标为中国，对象为俄罗斯；
    ifuse_proxy:是否使用代理；
    proxy:代理信息。
    
    return:{数据名称: 数据}{str:dataframe}
    '''
    pre_url = "https://comtradeapi.un.org/data/v1/get/{}/{}/{}?subscription-key={}&format={}&flowCode={}&reporterCode={}&period={}&cmdCode={}&partnerCode={}"
    url_use = pre_url.format(typeCode,freqCode,clCode,subscription_key,format,flowCode,reporterCode,period,cmdCode,partnerCode)
    print("Getting data from:"+url_use)
    data = download_url(url_use, ifuse_proxy = ifuse_proxy ,proxy = proxy)

    data_name = period+"_"+reporterCode+"_"+partnerCode+"_"+cmdCode+"_"+flowCode+"_"+freqCode
    return {data_name:data}


if __name__ == "__main__":
    os.makedirs("./uncomtrade_data", exist_ok=True)
    start_time = time.time()
    
    results = []
    reporter_ids = list(reporters.keys())
    
    # 逐年 单个进口国 每5个出口国获取数据
    for year in periods:
        for chunk in chunk_list(reporter_ids, 5):
            reporter_str = ','.join(chunk)
            reporter_names = ', '.join(reporters[rid] for rid in chunk)
            print(f"\n[year={year}] [reporters={reporter_names}]")

                
            temp = get_data_un_comtrade(typeCode = 'C',freqCode = 'A', clCode = 'HS',subscription_key = SUBSCRIPTION_KEY,format = 'json',flowCode = 'X',reporterCode = reporter_str,period = year,cmdCode = 'TOTAL',partnerCode = '0',ifuse_proxy = False ,proxy = None)  # 获取出口数据
            name = list(temp.keys())[0]
            df_exp = temp[name]
            if df_exp is not None and not df_exp.empty:
                df_exp['flow'] = 'X'
                results.append(df_exp)
                print(f"出口：{len(df_exp)} 条")
            else:
                print("出口：无数据")
                
            temp = get_data_un_comtrade(typeCode = 'C',freqCode = 'A', clCode = 'HS',subscription_key = SUBSCRIPTION_KEY,format = 'json',flowCode = 'M',reporterCode = reporter_str,period = year,cmdCode = 'TOTAL',partnerCode = '0',ifuse_proxy = False ,proxy = None)  # 获取进口数据
            name = list(temp.keys())[0]
            df_imp = temp[name]
            if df_imp is not None and not df_imp.empty: 
                df_imp['flow'] = 'M'
                results.append(df_imp)
                print(f"进口：{len(df_imp)} 条")
            else:
                print("进口：无数据")
            
            time.sleep(1.5) 
    
    if results:
        final_df = pd.concat(results, ignore_index=True)
        output_file = os.path.join(OUTPUT_DIR, f"chips_trade_data_{start_year}_{end_year}.csv")
        final_df.to_csv(output_file, index=False)
        print(f"\n√已保存{len(final_df)}条数据到 {output_file}")
    else:
        print("\n×未获取到任何数据")

    elapsed = time.time() - start_time
    print(f"总耗时: {elapsed:.2f} 秒 ({elapsed / 60:.1f} 分钟)")