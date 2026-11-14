# -*- coding: utf-8 -*-
"""
步骤1：数据探查（拿到表的第一件事）

目标：
  1. 看清每张表有多少行、多少列，每列是什么含义
  2. 找出表与表之间的关联键（order_id / customer_id / product_id / seller_id）
  3. 初步识别空值、类型异常、明显错误

本脚本不做任何修改，只输出信息。
运行：py src\01_explore.py
"""
import os
import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 60)

# 数据目录：可用环境变量 OLIST_DATA_DIR 覆盖
DATA_DIR = os.environ.get("OLIST_DATA_DIR", r"C:\Users\蛋哥\Desktop\离线数仓系统")

FILES = {
    "orders 订单主表":        "olist_orders_dataset.csv",
    "customers 客户表":       "olist_customers_dataset.csv",
    "order_items 订单商品":   "olist_order_items_dataset.csv",
    "products 商品表":        "olist_products_dataset.csv",
    "sellers 卖家表":         "olist_sellers_dataset.csv",
    "payments 支付表":        "olist_order_payments_dataset.csv",
    "reviews 评价表":         "olist_order_reviews_dataset.csv",
    "geolocation 地理表":     "olist_geolocation_dataset.csv",
    "类目翻译表":             "product_category_name_translation.csv",
}


def main():
    print("数据目录:", DATA_DIR)
    tables = {}

    for name, fname in FILES.items():
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            print(f"[缺失] {path}")
            continue
        # low_memory=False：避免分块推断类型导致同一列出现混合类型
        tables[name] = pd.read_csv(path, low_memory=False)

    # ---------- 1. 形状与列名 ----------
    print("\n" + "=" * 70)
    print("一、每张表的规模与列名")
    print("=" * 70)
    for name, df in tables.items():
        print(f"\n【{name}】{df.shape[0]:>8} 行 × {df.shape[1]:>2} 列")
        print("列名:", list(df.columns))

    # ---------- 2. 数据类型 ----------
    print("\n" + "=" * 70)
    print("二、数据类型（重点看哪些时间列还是 object 字符串）")
    print("=" * 70)
    for name, df in tables.items():
        print(f"\n【{name}】")
        print(df.dtypes.to_string())

    # ---------- 3. 空值 ----------
    print("\n" + "=" * 70)
    print("三、空值分布")
    print("=" * 70)
    for name, df in tables.items():
        nulls = df.isnull().sum()
        nulls = nulls[nulls > 0].sort_values(ascending=False)
        if len(nulls):
            print(f"\n【{name}】")
            print(nulls.to_string())
        else:
            print(f"\n【{name}】无空值")

    # ---------- 4. 样本 ----------
    print("\n" + "=" * 70)
    print("四、各表前 3 行样本")
    print("=" * 70)
    for name, df in tables.items():
        print(f"\n【{name}】")
        print(df.head(3).to_string())

    # ---------- 5. 关联键唯一性 ----------
    print("\n" + "=" * 70)
    print("五、关联键唯一性（判断是一对一还是一对多）")
    print("=" * 70)
    checks = [
        ("orders.order_id", tables.get("orders 订单主表")),
        ("customers.customer_id", tables.get("customers 客户表")),
        ("customers.customer_unique_id", tables.get("customers 客户表")),
        ("products.product_id", tables.get("products 商品表")),
        ("sellers.seller_id", tables.get("sellers 卖家表")),
    ]
    for label, df in checks:
        if df is None:
            continue
        col = label.split(".")[1]
        print(f"{label:<34} 唯一值 {df[col].nunique():>8} / 总行数 {len(df):>8}")

    for label, table_name, key in [
        ("order_items 每单商品行数", "order_items 订单商品", "order_id"),
        ("payments 每单支付笔数", "payments 支付表", "order_id"),
        ("reviews 每单评价条数", "reviews 评价表", "order_id"),
    ]:
        df = tables.get(table_name)
        if df is None:
            continue
        vc = df[key].value_counts()
        print(f"{label:<34} 订单数 {vc.shape[0]:>8}，单订单最多 {vc.max()} 条")

    print("\n探查完成。下一步：py src\\02_clean.py")


if __name__ == "__main__":
    main()
