# -*- coding: utf-8 -*-
"""
步骤6：数据可视化

读取 output/metrics/*.csv，输出 6 张图拼成的看板：
  1 月度订单量        折线图
  2 各州订单量 Top10  柱状图
  3 类目销售额 Top10  横向柱状图
  4 支付方式占比      饼图
  5 评分分布          柱状图
  6 延迟 vs 准时差评率 分组柱状图

输出：output/figures/dashboard.png 及单张图
运行：py src\05_visualize.py
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Windows 中文字体；Linux 可改为 WenQuanYi Micro Hei / Noto Sans CJK SC
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MET_DIR = os.path.join(BASE_DIR, "output", "metrics")
FIG_DIR = os.path.join(BASE_DIR, "output", "figures")
os.makedirs(FIG_DIR, exist_ok=True)


def load(name):
    return pd.read_csv(os.path.join(MET_DIR, name))


def main():
    monthly = load("monthly.csv")
    state_orders = load("state_orders.csv").head(10)
    category_sales = load("category_sales.csv").head(10)
    pay_dist = load("pay_type.csv")
    score_dist = load("score_dist.csv")
    late_vs = load("late_vs_score.csv")

    sns.set_style("whitegrid")
    fig, ax = plt.subplots(2, 3, figsize=(19, 10), constrained_layout=True)
    fig.suptitle("Olist 巴西电商离线数仓分析看板", fontsize=17)

    # 1 月度订单量（折线图：看趋势与拐点）
    ax[0, 0].plot(monthly["order_month"], monthly["order_count"],
                  marker="o", ms=4, color="#2196F3")
    ax[0, 0].set_title("月度订单量趋势")
    ax[0, 0].set_ylabel("订单数")
    ax[0, 0].tick_params(axis="x", rotation=60, labelsize=8)

    # 2 各州订单量（柱状图：离散类别对比）
    ax[0, 1].bar(state_orders["customer_state"], state_orders["order_count"],
                 color="#4CAF50")
    ax[0, 1].set_title("各州订单量 Top10")
    ax[0, 1].set_ylabel("订单数")

    # 3 类目销售额（横向柱状图：类目名长，横排更易读）
    cs = category_sales.sort_values("sales_amount")
    ax[0, 2].barh(cs["product_category_name_english"], cs["sales_amount"],
                  color="#FF9800")
    ax[0, 2].set_title("类目销售额 Top10")
    ax[0, 2].set_xlabel("销售额")
    ax[0, 2].tick_params(axis="y", labelsize=8)

    # 4 支付方式占比（饼图：部分与整体）
    ax[1, 0].pie(pay_dist["order_count"], labels=pay_dist["payment_type"],
                 autopct="%.1f%%", startangle=90,
                 colors=sns.color_palette("Set2"))
    ax[1, 0].set_title("支付方式占比")

    # 5 评分分布（柱状图：1-5 分是离散等级）
    ax[1, 1].bar(score_dist["review_score"].astype(str),
                 score_dist["order_count"], color="#9C27B0")
    ax[1, 1].set_title("评分分布")
    ax[1, 1].set_xlabel("评分")
    ax[1, 1].set_ylabel("订单数")

    # 6 延迟 vs 准时（分组柱状图：同一指标两个类别对比）
    late_vs = late_vs.sort_values("is_late")  # False(准时) 在前
    labels = late_vs["delivery_type"].tolist()
    bad = late_vs["bad_rate"].to_numpy()
    good = late_vs["good_rate"].to_numpy()
    x = np.arange(len(labels))
    w = 0.35
    ax[1, 2].bar(x - w / 2, bad, w, label="差评率(1-2分)", color="#F44336")
    ax[1, 2].bar(x + w / 2, good, w, label="好评率(4-5分)", color="#2196F3")
    ax[1, 2].set_xticks(x)
    ax[1, 2].set_xticklabels(labels)
    ax[1, 2].set_title("延迟对评分的影响")
    ax[1, 2].legend(fontsize=9)

    out = os.path.join(FIG_DIR, "dashboard.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"看板已保存: {out}")

    # 单图单独导出，便于插入报告
    singles = [
        ("01_monthly_orders.png", lambda: (monthly.plot(x="order_month", y="order_count",
                                                        marker="o", legend=False),
                                           plt.xlabel("月份"), plt.ylabel("订单数"),
                                           plt.title("月度订单量趋势"),
                                           plt.xticks(rotation=60))),
        ("02_late_vs_score.png", lambda: (pd.DataFrame({"配送": labels, "差评率": bad})
                                          .plot(x="配送", y="差评率", kind="bar",
                                                legend=False, color="#F44336"),
                                          plt.title("延迟与差评率"),
                                          plt.ylabel("差评率"))),
    ]
    for fname, draw in singles:
        plt.figure(figsize=(8, 4.5))
        draw()
        plt.tight_layout()
        plt.savefig(os.path.join(FIG_DIR, fname), dpi=150)
        plt.close()

    print(f"单图已保存至 {FIG_DIR}")
    plt.show()


if __name__ == "__main__":
    main()
