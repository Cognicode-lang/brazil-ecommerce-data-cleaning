# -*- coding: utf-8 -*-
"""
步骤2：数据清洗

处理内容：
  2.1 时间列 -> datetime
  2.2 缺失值分类（业务缺失 / 结构性缺失 / 脏数据）
  2.3 重复行与业务主键重复
  2.4 异常值（负价格、负运费）
  2.5 商品类目 葡语 -> 英语
  2.6 地理表不参与连接（避免行数爆炸）

输出：output/clean/*.csv
运行：py src\02_clean.py
"""
import os
import pandas as pd

DATA_DIR = os.environ.get("OLIST_DATA_DIR", r"C:\Users\蛋哥\Desktop\离线数仓系统")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "output", "clean")
os.makedirs(OUT_DIR, exist_ok=True)

TIME_COLS = [
    "order_purchase_timestamp",       # 下单时间
    "order_approved_at",              # 审核通过时间
    "order_delivered_carrier_date",   # 交由物流时间
    "order_delivered_customer_date",  # 实际送达时间
    "order_estimated_delivery_date",  # 预计送达时间
]


def read_raw():
    obj = {}
    for key, fname in {
        "orders": "olist_orders_dataset.csv",
        "customers": "olist_customers_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
        "products": "olist_products_dataset.csv",
        "sellers": "olist_sellers_dataset.csv",
        "payments": "olist_order_payments_dataset.csv",
        "reviews": "olist_order_reviews_dataset.csv",
        "geo": "olist_geolocation_dataset.csv",
        "category_tr": "product_category_name_translation.csv",
    }.items():
        obj[key] = pd.read_csv(os.path.join(DATA_DIR, fname), low_memory=False)
        print(f"读取 {key:<12} {obj[key].shape}")
    return obj


def save(df, fname):
    path = os.path.join(OUT_DIR, fname)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  保存 {fname}: {df.shape}")


def main():
    t = read_raw()
    orders = t["orders"]
    order_items = t["order_items"]
    products = t["products"]
    reviews = t["reviews"]
    geo = t["geo"]
    category_tr = t["category_tr"]

    print("\n" + "=" * 60)
    print("2.1 时间列标准化")
    print("=" * 60)
    for col in TIME_COLS:
        # errors="coerce"：无法解析的值转 NaT，不中断流程，便于统计异常条数
        orders[col] = pd.to_datetime(orders[col], errors="coerce")
    print(orders[TIME_COLS].dtypes.to_string())
    for col in TIME_COLS:
        na = orders[col].isnull().sum()
        print(f"  {col:<32} 空值 {na:>6} ({na / len(orders):.2%})")

    print("\n" + "=" * 60)
    print("2.2 缺失值分类")
    print("=" * 60)
    print("订单状态分布：")
    print(orders["order_status"].value_counts().to_string())

    # 仅"已送达却无送达时间"属于脏数据；其余时间缺失是业务未走到该环节
    dirty = orders[
        (orders["order_status"] == "delivered")
        & (orders["order_delivered_customer_date"].isnull())
    ]
    print(f"\n已送达但送达时间为空（脏数据）: {len(dirty)} 条 -> 后续配送分析剔除")
    print(f"评价分为空（买家未评分）: {orders['order_id'].nunique() - reviews['order_id'].nunique()} 单左右")
    print("商品类目为空: "
          f"{products['product_category_name'].isnull().sum()} 条 -> 翻译后填 unknown")

    print("\n" + "=" * 60)
    print("2.3 重复值处理")
    print("=" * 60)
    tables = {
        "orders": orders, "customers": t["customers"], "order_items": order_items,
        "products": products, "sellers": t["sellers"], "payments": t["payments"],
        "reviews": reviews,
    }
    for name, df in tables.items():
        dup = df.duplicated().sum()
        if dup:
            df.drop_duplicates(inplace=True)
        print(f"  {name:<12} 完全重复 {dup:>5} 行 {'-> 已删除' if dup else ''}")

    # 业务主键重复：同一 review_id 可能重复提交，按时间保留最新
    reviews = reviews.copy()
    reviews["review_answer_timestamp"] = pd.to_datetime(
        reviews["review_answer_timestamp"], errors="coerce")
    before = len(reviews)
    reviews = (reviews.sort_values("review_answer_timestamp")
                      .drop_duplicates(subset=["review_id"], keep="last"))
    print(f"  reviews      按 review_id 去重 {before - len(reviews)} 行")

    print("\n" + "=" * 60)
    print("2.4 异常值处理")
    print("=" * 60)
    neg_price = (order_items["price"] < 0).sum()
    neg_freight = (order_items["freight_value"] < 0).sum()
    print(f"  price < 0          : {neg_price}")
    print(f"  freight_value < 0  : {neg_freight}")
    if neg_price or neg_freight:
        order_items = order_items[(order_items["price"] >= 0)
                                  & (order_items["freight_value"] >= 0)].copy()
    print("\n数值分布：")
    print(order_items[["price", "freight_value"]].describe().round(2).to_string())
    zero_price = (order_items["price"] == 0).sum()
    print(f"  price == 0 的记录: {zero_price}（保留，可能是赠品/补差价）")

    print("\n" + "=" * 60)
    print("2.5 商品类目翻译")
    print("=" * 60)
    products = products.merge(category_tr, on="product_category_name", how="left")
    products["product_category_name_english"] = (
        products["product_category_name_english"].fillna("unknown").str.lower()
    )
    unknown = (products["product_category_name_english"] == "unknown").sum()
    print(f"  翻译后类别数: {products['product_category_name_english'].nunique()}")
    print(f"  未能翻译(unknown): {unknown} 条")

    print("\n" + "=" * 60)
    print("2.6 地理表处理说明")
    print("=" * 60)
    print(f"  地理表 {len(geo)} 行，唯一邮编 {geo['geolocation_zip_code_prefix'].nunique()} 个")
    print("  一个邮编对应多条坐标，直接 join 会造成行数膨胀 -> 本流程不引入，")
    print("  地域分析统一使用 customers.customer_state。")

    print("\n" + "=" * 60)
    print("保存清洗结果")
    print("=" * 60)
    save(orders, "clean_orders.csv")
    save(t["customers"], "clean_customers.csv")
    save(order_items, "clean_order_items.csv")
    save(products, "clean_products.csv")
    save(t["sellers"], "clean_sellers.csv")
    save(t["payments"], "clean_payments.csv")
    save(reviews, "clean_reviews.csv")
    print("\n步骤2 完成。下一步：py src\\03_merge.py")


if __name__ == "__main__":
    main()
