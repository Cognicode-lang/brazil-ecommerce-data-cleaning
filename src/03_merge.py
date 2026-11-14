# -*- coding: utf-8 -*-
"""
步骤3：多表合并，构建订单级分析宽表（DWS 层）

核心原则：
  订单与商品 / 支付 / 评价 都是一对多关系，
  直接 merge 会让一个订单复制成多行，指标被重复计数。
  所以必须「先按 order_id 聚合，再连接」。

输出：
  output/wide_table.csv   订单级宽表（行数 == 订单数）
  output/items_full.csv   商品明细 + 类目（供类目分析）

运行：py src\03_merge.py
"""
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DIR = os.path.join(BASE_DIR, "output", "clean")
OUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)

TIME_COLS = [
    "order_purchase_timestamp", "order_approved_at",
    "order_delivered_carrier_date", "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def main():
    orders = pd.read_csv(os.path.join(CLEAN_DIR, "clean_orders.csv"),
                         parse_dates=TIME_COLS)
    order_items = pd.read_csv(os.path.join(CLEAN_DIR, "clean_order_items.csv"))
    products = pd.read_csv(os.path.join(CLEAN_DIR, "clean_products.csv"))
    customers = pd.read_csv(os.path.join(CLEAN_DIR, "clean_customers.csv"))
    payments = pd.read_csv(os.path.join(CLEAN_DIR, "clean_payments.csv"))
    reviews = pd.read_csv(os.path.join(CLEAN_DIR, "clean_reviews.csv"))

    print(f"读入: orders={orders.shape} items={order_items.shape} "
          f"products={products.shape} customers={customers.shape} "
          f"payments={payments.shape} reviews={reviews.shape}")

    # ---------- 3.1 商品明细 + 类目 ----------
    items_full = order_items.merge(
        products[["product_id", "product_category_name_english"]],
        on="product_id", how="left")
    print(f"\nitems_full: {items_full.shape}，"
          f"类目缺失 {items_full['product_category_name_english'].isna().sum()} 行")

    # ---------- 3.2 聚合到订单粒度 ----------
    items_agg = items_full.groupby("order_id").agg(
        total_price=("price", "sum"),
        total_freight=("freight_value", "sum"),
        item_count=("order_item_id", "count"),
        seller_count=("seller_id", "nunique"),
        categories=("product_category_name_english",
                    lambda s: ",".join(sorted(set(s.dropna())))),
    ).reset_index()
    print(f"items_agg: {items_agg.shape}")

    pay_agg = payments.groupby("order_id").agg(
        payment_value=("payment_value", "sum"),
        payment_installments=("payment_installments", "max"),
        payment_types=("payment_type",
                       lambda s: ",".join(sorted(set(s.dropna())))),
    ).reset_index()
    print(f"pay_agg  : {pay_agg.shape}")

    reviews["review_answer_timestamp"] = pd.to_datetime(
        reviews["review_answer_timestamp"], errors="coerce")
    rev_agg = (reviews.sort_values("review_answer_timestamp")
               .groupby("order_id")
               .agg(review_score=("review_score", "last"))
               .reset_index())
    print(f"rev_agg  : {rev_agg.shape}")

    # ---------- 3.3 以订单主表为核心左连接 ----------
    df = (orders
          .merge(customers[["customer_id", "customer_unique_id",
                            "customer_city", "customer_state"]],
                 on="customer_id", how="left")
          .merge(items_agg, on="order_id", how="left")
          .merge(pay_agg, on="order_id", how="left")
          .merge(rev_agg, on="order_id", how="left"))

    print("\n" + "=" * 60)
    print(f"订单数   : {len(orders)}")
    print(f"宽表行数 : {len(df)}")
    # 行数必须守恒，一旦膨胀说明还有表没聚合干净
    assert len(df) == len(orders), "行数膨胀，检查一对多表是否已聚合"
    print("行数守恒校验通过")

    # ---------- 3.4 派生字段 ----------
    df["order_month"] = df["order_purchase_timestamp"].dt.to_period("M").astype(str)
    df["delivery_days"] = (df["order_delivered_customer_date"]
                           - df["order_purchase_timestamp"]).dt.days
    df["is_late"] = (df["order_delivered_customer_date"]
                     > df["order_estimated_delivery_date"])

    delivered = df[(df["order_status"] == "delivered") & df["delivery_days"].notna()]
    print(f"已送达且时间完整: {len(delivered)} 单")
    print(f"配送天数为负的异常记录: {(df['delivery_days'] < 0).sum()} 条")

    print("\n关键字段缺失率:")
    for c in ["total_price", "payment_value", "review_score", "delivery_days"]:
        print(f"  {c:<16} {df[c].isna().mean():.2%}")

    # ---------- 3.5 落盘 ----------
    df.to_csv(os.path.join(OUT_DIR, "wide_table.csv"), index=False, encoding="utf-8-sig")
    items_full.to_csv(os.path.join(OUT_DIR, "items_full.csv"), index=False, encoding="utf-8-sig")
    print("\n已保存 wide_table.csv / items_full.csv")
    print("步骤3 完成。下一步：py src\\04_metrics.py")


if __name__ == "__main__":
    main()
