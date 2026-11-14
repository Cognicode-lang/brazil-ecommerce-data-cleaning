# 巴西电商数据清洗项目（Olist）

基于 Olist 巴西电商公开数据集（9 张业务表，约 10 万订单）的离线数仓分析项目，覆盖
**ODS → DWD → DWS → ADS** 四层链路：数据探查 → 数据清洗 → 多表合并 → 指标计算 → 可视化。

## 目录结构

```
巴西电商数据清洗项目/
├── README.md                       本文件
├── requirements.txt                依赖清单
├── src/
│   ├── 01_explore.py               步骤1 数据探查（只读，输出表结构/类型/空值/关联键）
│   ├── 02_clean.py                 步骤2 数据清洗（时间/缺失/重复/异常/类目翻译）
│   ├── 03_merge.py                 步骤3 多表合并 → 订单级宽表
│   ├── 04_metrics.py               步骤4/5 四类业务指标计算
│   └── 05_visualize.py             步骤6 生成图表看板
├── output/
│   ├── clean/                      清洗后的业务明细（clean_*.csv）
│   ├── wide_table.csv              订单级宽表（行数 = 订单数）
│   ├── items_full.csv              商品明细 + 英文类目
│   ├── metrics/                    指标结果（metrics 表）
│   └── figures/                    图表 PNG
   

## 数据源



如果数据放在别处，设置环境变量即可（脚本优先读它）：

```powershell
$env:OLIST_DATA_DIR = "D:\data\olist"
```

包含 9 个文件：

| 文件 | 内容 |
| --- | --- |
| olist_orders_dataset.csv | 订单主表，5 个时间节点 + 订单状态 |
| olist_order_items_dataset.csv | 订单商品明细（一单多行） |
| olist_customers_dataset.csv | 客户表（customer_id / customer_unique_id） |
| olist_products_dataset.csv | 商品表（类目、尺寸、重量） |
| olist_sellers_dataset.csv | 卖家表 |
| olist_order_payments_dataset.csv | 支付表（一单可多笔） |
| olist_order_reviews_dataset.csv | 评价表（一单可多条） |
| olist_geolocation_dataset.csv | 地理表（邮编 → 经纬度，本次不参与连接） |
| product_category_name_translation.csv | 类目葡语 → 英语字典 |

## 环境与运行

```powershell
pip install -r requirements.txt

cd "l:\Work  space\project\new-project\client\hms\巴西电商数据清洗项目"
py src\01_explore.py
py src\02_clean.py
py src\03_merge.py
py src\04_metrics.py
py src\05_visualize.py
```

必须按 01 → 05 顺序执行，后一步读取前一步的落盘文件。

## 清洗要点

| 问题 | 判定方法 | 处理 |
| --- | --- | --- |
| 时间列是字符串 | dtype 为 object | `pd.to_datetime(errors="coerce")` |
| 缺失值 | 需区分业务缺失与脏数据 | 未送达属正常；已送达却无送达时间才剔除 |
| 完全重复行 | `duplicated().sum()` | `drop_duplicates()` |
| 业务键重复 | `duplicated(subset=["review_id"])` | 按时间保留最新一条 |
| 一对多合并膨胀 | merge 后行数 ≠ 订单数 | 先 `groupby("order_id")` 聚合再连接 |
| 价格/运费为负 | 规则校验 | 过滤 |
| 地理表笛卡尔膨胀 | 邮编唯一值 << 表行数 | 不参与连接，地域用州字段 |
| 类目为葡语 | 需翻译 | 关联翻译表，未匹配填 unknown |

## 关键指标口径

| 指标 | 口径 |
| --- | --- |
| GMV | 商品金额 `price` 合计（不含运费） |
| 平均配送天数 | 送达时间 − 下单时间，仅已送达且非负 |
| 延迟 | 实际送达时间 > 预计送达时间 |
| 延迟率 | 延迟订单数 / 已送达订单数 |
| 差评率 | 评分 ≤ 2 的订单占比 |
| 复购率 | 下单 ≥ 2 次的 `customer_unique_id` 占比 |
| 客单价 | GMV / 订单数 |

## 产出

- 宽表 `wide_table.csv`：每行一个订单，含客户地区、商品金额、支付、评分、配送天数、是否延迟
- 指标 CSV：月度趋势、各州订单与延迟、类目销售额、评分分布、延迟对比、支付方式、复购率
- 图表看板 `output/figures/dashboard.png`
- 文字报告 `docs/Olist离线数仓数据分析项目总结报告.docx`

## 常见问题

1. **`ModuleNotFoundError: 'matplotlib' is not a package`**
   脚本所在目录存在同名文件 `matplotlib.py`，删掉或改名即可。同理适用于 `seaborn.py`、`pandas.py`。
2. **`NameError: name 'df' is not defined`**
   多文件拆分后变量不共享，必须靠落盘文件传递（本项目已按此设计）。
3. **中文显示为方块**
   缺少中文字体，Windows 用 Microsoft YaHei / SimHei；Linux 安装 `fonts-wqy-microhei`。
