# UN Comtrade 数据获取与文献复现

本项目利用联合国商品贸易统计数据库（UN Comtrade），对已发表文章涉及的贸易数据开展获取与复现试验，主要研究两个场景：

- 20 个国家对中国的机器人出口贸易。
- 2014—2025 年芯片供应链相关产品的全球双边贸易明细。

项目保留通过 `comtradeapicall` 包和直接构造 URL 两种获取方式，使用 pandas 整理结果并导出 CSV。研究目标中的芯片明细粒度为“年份 × 报告国 × 贸易伙伴 × HS 六位商品 × 进出口方向”。

## 文件结构

```text
UN_Comtrade/
├── comtradeapicall/             # 第三方 API 包源码、示例、测试及原许可证
├── fetch_chips/
│   ├── fetch_api.py             # API 包调用脚本
│   ├── fetch_url.py             # 直接请求 URL 的脚本
│   ├── test_fetch_bilateral.py  # 旧版实现的测试文件，当前不作为运行入口
│   ├── reporters.csv           # 本地报告国名单
│   └── data/                   
├── fetch_robots/
│   ├── fetch.py                # 机器人出口数据脚本
│   ├── fetch copy.py           # 历史副本
│   ├── reporters.csv
│   └── data/               
├── .gitignore
├── README.md
└── requirements.txt
```

GitHub 仓库保留代码、说明及依赖配置；CSV 名单、下载结果、缓存、日志、虚拟环境和密钥保留在本地。目录树中的本地数据文件需要自行准备，不会随克隆获得。

## 当前脚本说明

以下内容依据当前代码描述，不表示已完成研究目标中的全部数据处理。

| 脚本 | 请求组织 | 当前商品参数 | 当前伙伴参数 | 输出文件 |
| --- | --- | --- | --- | --- |
| `fetch_robots/fetch.py` | 按年份，4 个线程 | 7 个机器人相关编码 | 中国 `156`，出口 `X` | `fetch_robots/data/robots_preview.csv` |
| `fetch_chips/fetch_api.py` | 按年份，4 个线程，每批 10 个报告国 | 22 个芯片供应链编码 | `0`，分别请求 `X` / `M` | `fetch_chips/data/robots_preview.csv` |
| `fetch_chips/fetch_url.py` | 逐年顺序执行，每批 5 个报告国 | 调用处为 `TOTAL` | `0`，分别请求 `X` / `M` | `fetch_chips/data/chips_trade_data_2014_2025.csv` |

芯片研究目标是全球双边产品明细；当前代码调用处的 `partnerCode='0'` 表示世界合计，URL 主循环还使用 `cmdCode='TOTAL'`。这些现有参数尚未与研究目标对齐，不能仅凭文件名把当前输出认定为双边芯片明细。本文如实记录代码现状，不修改脚本参数。

两个芯片脚本彼此独立，没有共用下载流程。当前版本没有批次缓存、断点续传、全线程统一限速或自动拆分返回上限的实现。`test_fetch_bilateral.py` 对应此前另一版实现，与当前脚本接口不匹配，不能用它宣称当前版本已通过明细测试。

## 环境准备

在项目根目录的 PowerShell 中执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

如需使用项目内保存的 `comtradeapicall` 源码：

```powershell
.\.venv\Scripts\python.exe -m pip install -e .\comtradeapicall
```

检查依赖：

```powershell
.\.venv\Scripts\python.exe -c "import pandas, requests, dotenv, comtradeapicall; print('依赖导入成功')"
```

直接指定虚拟环境解释器即可，不需要同时激活 Conda 环境。出现 `ModuleNotFoundError` 时，应检查依赖是否安装在实际运行脚本的解释器中。

### API 密钥与本地路径

在 [UN Comtrade 开发者门户](https://comtradedeveloper.un.org/)申请订阅密钥，并在脚本指定的 `.venv/.env` 文件中填写：

```dotenv
API_KEY=替换为你的订阅密钥
```

当前脚本使用本机绝对路径。迁移到其他电脑时，需要自行核对 `BASE_DIR`、`ENV_PATH`，以及派生的报告国名单和输出路径。

`reporters.csv` 至少需要 `id`、`text` 两列，例如：

```csv
id,text
36,Australia
124,Canada
```

`partners.csv` 目前只是参考名单，现有芯片脚本没有读取或遍历该文件。国家与地区参考表可从 [UN Comtrade 官方说明](https://uncomtrade.org/docs/country-codes/)获取；机器人研究需按原文范围选取 20 个报告国。

## 获取 20 个国家对中国的机器人出口数据

### 数据范围

- 年份：2014—2025 年，年度商品贸易。
- 报告国：由 `fetch_robots/reporters.csv` 指定，包括 Australia、Canada、Denmark 等国家。
- 贸易方向：报告国出口 `X`，贸易伙伴为中国 `156`。
- 商品范围：以下 7 个 HS 六位编码，作为机器人相关产品的宽口径代理。

| HS 编码 | 原研究口径中的用途 / 类别 |
| --- | --- |
| 851531 | 电弧焊接机器人相关设备 |
| 847950 | 工业机器人 |
| 851521 | 电阻焊接机器人相关设备 |
| 851580 | 其他焊接机器人相关设备 |
| 842489 | 喷涂机器人相关设备 |
| 842890 | 搬运机器人相关设备 |
| 848640 | 半导体工厂自动搬运机器人相关设备 |

这里的研究类别不是各编码官方商品描述的逐字转录；部分编码覆盖范围宽于机器人本身。正式复现时，应与原文商品口径及相应 HS 版本核对。

### 运行

核对本地路径并准备名单后，在项目根目录执行：

```powershell
New-Item -ItemType Directory -Force .\fetch_robots\data | Out-Null
.\.venv\Scripts\python.exe .\fetch_robots\fetch.py
```

结果保存到 `fetch_robots/data/robots_preview.csv`，使用 UTF-8 BOM 编码。文件名虽然含 `preview`，实际调用的是 `getFinalData`。

## 芯片供应链全球双边贸易研究

### 产品范围

研究涉及上游材料与设备、中游芯片制造以及下游应用的 22 个 HS 六位编码。下表保留原研究设计中的分组，产品名称用于说明研究口径，不代替官方 HS 定义。

| 环节 | 产品类别 | 产品名称 | 海关HS 6位产品编码 |
| :--- | :--- | :--- | :--- |
| 上游 | 原材料 | 硅片、光刻胶、掩模版、电子特气 | 381800、370710、900290、280429 |
| 上游 | 制造设备 | 切割机、刻蚀机、光刻机、清洗机 | 848610、848620、848630、848690 |
| 中游 | 芯片制造 | CPU芯片、存储芯片、放大器芯片 | 854231、854232、854233 |
| 中游 | 芯片制造 | 传感器 芯片框架 | 854151、854190 |
| 下游 | 汽车电子 | 汽车传感器、控制芯片 | 840999、852721 |
| 下游 | 消费电子 | 智能手机、固态硬盘、平板电脑 | 851713、847170、847130 |
| 下游 | 网络通信 | 光纤、路由器 | 900190、851762 |
| 下游 | 工业应用 | 工业机器人、电子仪器 | 847950、903082 |

### API 方式

```powershell
New-Item -ItemType Directory -Force .\fetch_chips\data | Out-Null
.\.venv\Scripts\python.exe .\fetch_chips\fetch_api.py
```

核心函数为 `fetch_by_year(year)`，每次处理 10 个报告国，分别调用 `comtradeapicall.getFinalData` 获取进出口数据，主线程合并各年份结果。当前请求使用 22 个商品编码、世界伙伴合计，`maxRecords=250000`；实际可返回的行数受订阅权限限制。

当前输出名沿用 `robots_preview.csv`，实际路径为 `fetch_chips/data/robots_preview.csv`，不要与机器人目录中的同名文件混淆。

### URL 方式

```powershell
New-Item -ItemType Directory -Force .\fetch_chips\data | Out-Null
.\.venv\Scripts\python.exe .\fetch_chips\fetch_url.py
```

`get_data_un_comtrade(...)` 负责构造查询 URL，`download_url(...)` 负责请求和解析 JSON / CSV。主程序逐年执行，每组 5 个报告国，分别获取 X/M 后合并，输出 `fetch_chips/data/chips_trade_data_2014_2025.csv`。

当前主循环传入的是 `TOTAL` 和世界伙伴 `0`，虽然脚本定义了 `CHIP_CODES`，该列表未用于主循环的请求。代理类保留配置入口，默认调用不启用代理。

错误日志写入运行目录下的 `uncomtrade_data/`。现有重试使用递归，尚未设置重试次数或基于状态码的完整限额处理；重试返回值也未向外传递。

## 请求限额与数据核对

- **调用配额：**以 [官方订阅说明](https://uncomtrade.org/docs/subscriptions/)和账户实际权限为准。短时间请求过快需要降低频率；每日配额耗尽需要等待恢复。换 IP 不会增加账户配额。
- **现有限速：**API 脚本在各线程的组内请求之后等待 2 秒；URL 脚本在一组进出口请求后等待 1.5 秒。这些等待不等于对每一次请求实施全局限速。
- **中断处理：**当前结果主要保存在内存，结束后才写入 CSV，没有自动断点续传。配额错误或其他中断可能导致本轮结果未保存。
- **完整性：**成功生成文件不代表每个年份、报告国、商品和伙伴都已获取完整。需核对请求错误、返回上限与数据覆盖范围，不能把空结果直接当作零贸易额。
- **统计口径：**跨年使用 HS 六位编码时，应核对分类版本及编码变更。进口与出口的镜像数据不能不加区分地直接相加。
- **日志：**当前 URL 脚本会打印带订阅密钥的请求地址；控制台输出和错误日志不应直接上传或公开。

## GitHub 文件范围

仓库地址：[Carbonsteel2749/UN-Comtrade-Database](https://github.com/Carbonsteel2749/UN-Comtrade-Database)。

`.gitignore` 保留原有规则，并补充排除结果目录、下载缓存、临时文件和常见二进制结果格式。以下内容只保留在本地：

- `.venv/`、IDE 设置、Python 缓存等运行环境文件。
- `.env`、密钥文件及错误日志。
- 全部 CSV（包含 `reporters.csv`、`partners.csv`）、Excel 和 Parquet 文件。
- `data/`、`output/`、`outputs/`、`result/`、`results/`、`uncomtrade_data/` 等结果目录，以及批次缓存目录。
- JSONL、Feather、Pickle、HDF5、Stata、数据库及压缩下载结果等文件。

结果文件不会随项目上传；克隆后需自行准备报告国名单和密钥，并创建输出目录。`comtradeapicall/` 保留第三方源码、示例和许可证，其内层 Git 历史不作为项目文件上传。

## 参考资料

- [UN Comtrade 数据查询平台](https://comtradeplus.un.org/)
- [UN Comtrade API 官方说明](https://uncomtrade.org/docs/un-comtrade-api/)
- [国家与地区代码](https://uncomtrade.org/docs/country-codes/)
- [comtradeapicall 官方源码](https://github.com/uncomtrade/comtradeapicall)
- [机器人脚本参考文章](https://www.cnblogs.com/chenyangqit/p/16594946.html)
- [芯片脚本参考文章](https://blog.csdn.net/standingflower/article/details/126843518)
