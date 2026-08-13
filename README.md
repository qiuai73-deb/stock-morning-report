# 股票盘前晨报 (GitHub Actions 版)

每天开盘前自动采集全球市场数据与财经资讯，生成结构化盘前晨报并 commit 回本仓库。

## 定时运行

通过 GitHub Actions 的 `schedule` 触发，无需本机开机：

- 计划时间：**北京时间每个交易日 06:30**
- cron（UTC）：`30 22 * * 0-4`
  （北京时间 UTC+8，故 06:30 = 前一天 UTC 22:30；周一~周五北京对应 UTC 周日~周四）
- 也可在仓库 **Actions → 股票盘前晨报 → Run workflow** 手动触发一次

## 报告内容

- 🏛️ 宏观政策 / 🌍 国际要闻 / 📰 其他要闻
- ⚡ 财联社快讯（7×24 电报，情感分类）
- 💰 资金面（北向资金 / 融资融券，东方财富备用源）
- 📋 操作建议（保守 / 稳健 / 激进）
- ⚠️ 风险提示 + 🎯 综合结论

生成文件保存在 `reports/YYYY-MM-DD_morning_brief.txt`，每次运行后自动 commit 回仓库，可在 GitHub 上直接查看历史。

## 本地运行

```bash
pip install -r requirements.txt
python main.py --now          # 立即生成一次
python main.py --schedule     # 常驻进程，按 06:30 定时（需一直运行）
```

## 可选：飞书推送

1. 在飞书群添加一个「自定义机器人」并复制 webhook 地址
2. 仓库 **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `LARK_WEBHOOK`
   - Value: 机器人 webhook 地址
3. 之后每次运行会自动把最新晨报以文本消息发到该群；不配置则跳过此步

> 注：自定义机器人发到「群」。若需发到「自己」私聊，需用飞书应用
> `app_id/app_secret` 调用消息 API，可在此基础上扩展。

## 数据源

东方财富 API、新浪财经、财联社 API、新浪 Feed（见各 collector 实现）。
