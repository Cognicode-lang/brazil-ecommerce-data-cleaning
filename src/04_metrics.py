# -*- coding: utf-8 -*-
"""
步骤4/5：业务指标计算（ADS 层）

四类分析目标：
  1. 销售情况：月度订单量、GMV、各州订单量、类目销售额
  2. 物流配送：平均配送天数、P90、延迟率、各州延迟率
  3. 客户满意度：评分分布、延迟 vs 准时的评分对比
  4. 客户特征：复购率、支付方式偏好、客户地域分布

输出：output/metrics/*.csv（供 05_visualize.py 画图）
运行：py src\04_metrics.py
"""
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "output")
MET_DIR = os.path.join(OUT_DIR, "metrics")
os.makedirs(MET_DIR, exist_ok=True)

TIME_COLS = [
    "order_purchase_timestamp", "order_approved_at",
    "order_delivered_carrier_date", "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def save(df, fname):
    df.to_csv(os.path.join(MET_DIR, fname), index=False, encoding="utf-8-sig")
    print(f"  保存 metrics/{fname}: {len(df)} 行")


def main():
    df = pd.read_csv(os.path.join(OUT_DIR, "wide_table.csv"), parse_dates=TIME_COLS)
    items_full = pd.read_csv(os.path.join(OUT_DIR, "items_full.csv"))

    # CSV 读回的布尔列可能是字符串，统一转 bool
    df["is_late"] = (df["is_late"].astype(str).str.lower()
                     .map({"true": True, "false": False}))

    df_delivered = df[(df["order_status"] == "delivered")
                      & df["delivery_days"].notna()
                      & (df["delivery_days"] >= 0)].copy()
    print(f"宽表 {df.shape}，配送分析样本 {len(df_delivered)}")

    # ================= 目标1：销售 =================
    print("\n" + "=" * 60)
    print("目标1：销售情况")
    print("=" * 60)

    monthly = (df.groupby("order_month")
               .agg(order_count=("order_id", "count"),
                    gmv=("total_price", "sum"))
               .reset_index())
    monthly["avg_order_value"] = monthly["gmv"] / monthly["order_count"]
    print("月度趋势（首尾各3行）:")
    print(pd.concat([monthly.head(3), monthly.tail(3)]).round(2).to_string(index=False))

    state_orders = (df.groupby("customer_state")["order_id"]
                    .count().sort_values(ascending=False)
                    .reset_index())
    state_orders.columns = ["customer_state", "order_count"]
    print("\n订单量 Top5 州:")
    print(state_orders.head(5).to_string(index=False))

    category_sales = (items_full.groupby("product_category_name_english")
                      .agg(sales_amount=("price", "sum"),
                           item_count=("order_item_id", "count"))
                      .sort_values("sales_amount", ascending=False)
                      .reset_index())
    print("\n销售额 Top5 类目:")
    print(category_sales.head(5).round(2).to_string(index=False))

    save(monthly, "monthly.csv")
    save(state_orders, "state_orders.csv")
    save(category_sales, "category_sales.csv")

    # ================= 目标2：物流 =================
    print("\n" + "=" * 60)
    print("目标2：物流配送")
    print("=" * 60)

    avg_days = df_delivered["delivery_days"].mean()
    p90 = df_delivered["delivery_days"].quantile(0.90)
    late_rate = df_delivered["is_late"].mean()
    print(f"平均配送天数 : {avg_days:.1f} 天")
    print(f"P90 配送天数 : {p90:.0f} 天")
    print(f"延迟订单占比 : {late_rate:.2%}")

    state_late = (df_delivered.groupby("customer_state")
                  .agg(order_count=("order_id", "count"),
                       avg_days=("delivery_days", "mean"),
                       late_rate=("is_late", "mean"))
                  .query("order_count >= 100")   # 样本过小的州不参与排名
                  .sort_values("late_rate", ascending=False)
                  .reset_index())
    print("\n延迟率最高 Top5 州（订单>=100）:")
    print(state_late.head(5).round(3).to_string(index=False))

    delivery_summary = pd.DataFrame([{
        "avg_delivery_days": round(avg_days, 2),
        "p90_delivery_days": p90,
        "late_rate": round(late_rate, 4),
        "sample_orders": len(df_delivered),
    }])
    save(delivery_summary, "delivery_summary.csv")
    save(state_late, "state_late.csv")

    # ================= 目标3：满意度 =================
    print("\n" + "=" * 60)
    print("目标3：客户满意度（延迟 vs 评分）")
    print("=" * 60)

    d = df_delivered.dropna(subset=["review_score"]).copy()
    d["review_score"] = d["review_score"].astype(int)

    score_dist = (d["review_score"].value_counts().sort_index().reset_index())
    score_dist.columns = ["review_score", "order_count"]
    print("评分分布:")
    print(score_dist.to_string(index=False))

    late_vs_score = (d.groupby("is_late")
                     .agg(order_count=("order_id", "count"),
                          avg_score=("review_score", "mean"),
                          bad_rate=("review_score", lambda s: (s <= 2).mean()),
                          good_rate=("review_score", lambda s: (s >= 4).mean()))
                     .reset_index())
    late_vs_score["delivery_type"] = late_vs_score["is_late"].map(
        {True: "延迟送达", False: "准时送达"})
    print("\n延迟 vs 准时:")
    print(late_vs_score[["delivery_type", "order_count", "avg_score",
                         "bad_rate", "good_rate"]].round(3).to_string(index=False))

    cross = pd.crosstab(d["is_late"], d["review_score"], normalize="index")
    print("\n配送状态 × 评分占比:")
    print(cross.round(3).to_string())

    save(score_dist, "score_dist.csv")
    save(late_vs_score, "late_vs_score.csv")
    cross.reset_index().to_csv(os.path.join(MET_DIR, "cross.csv"),
                               index=False, encoding="utf-8-sig")

    # ================= 目标4：客户特征 =================
    print("\n" + "=" * 60)
    print("目标4：客户特征")
    print("=" * 60)

    per_customer = df.groupby("customer_unique_id")["order_id"].nunique()
    repurchase_rate = (per_customer > 1).mean()
    print(f"客户总数（去重自然人）: {len(per_customer):,}")
    print(f"复购率（下单>=2次）   : {repurchase_rate:.2%}")
    print(f"人均订单数            : {per_customer.mean():.2f}")

    state_customer = (df.groupby("customer_state")["customer_unique_id"]
                      .nunique().sort_values(ascending=False).reset_index())
    state_customer.columns = ["customer_state", "customer_count"]

    # 支付方式：每单取金额最大的一条作为主支付方式
    pay_main = (df.dropna(subset=["payment_types"])
                .sort_values("payment_value", ascending=False)
                .drop_duplicates("order_id"))
    pay_dist = (pay_main["payment_types"].str.split(",").str[0]
                .value_counts().reset_index())
    pay_dist.columns = ["payment_type", "order_count"]
    pay_dist["share"] = pay_dist["order_count"] / pay_dist["order_count"].sum()
    print("\n支付方式占比:")
    print(pay_dist.round(3).to_string(index=False))

    customer_summary = pd.DataFrame([{
        "customer_count": len(per_customer),
        "repurchase_rate": round(repurchase_rate, 4),
        "avg_orders_per_customer": round(per_customer.mean(), 3),
    }])
    save(customer_summary, "customer_summary.csv")
    save(state_customer, "state_customer.csv")
    save(pay_dist, "pay_type.csv")

    print("\n步骤5 完成。下一步：py src\\05_visualize.py")


if __name__ == "__main__":
    main()
