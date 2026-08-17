from __future__ import annotations

import logging
from datetime import datetime, timedelta

from collectors.base import BaseCollector, MarketData
from analysis.sentiment import SentimentAnalyzer

logger = logging.getLogger(__name__)

_sentiment_analyzer = SentimentAnalyzer()


class CLSNewsCollector(BaseCollector):
    category = "实时快讯"

    async def collect(self) -> MarketData:
        items = []
        try:
            items.extend(await self._fetch_sina_flash())
        except Exception as e:
            logger.error("新浪快讯采集失败: %s", e)
        if not items:
            try:
                items.extend(await self._fetch_eastmoney_live())
            except Exception as e:
                logger.error("东方财富7x24采集失败: %s", e)
        return MarketData(category=self.category, items=items)

    async def _fetch_sina_flash(self) -> list[dict]:
        url = "https://feed.mix.sina.com.cn/api/roll/get"
        params = {"pageid": "153", "lid": "2516", "k": "", "num": "30", "page": "1"}
        data = await self._get_json(url, params=params)
        if not data:
            return []
        items = []
        try:
            news_list = data.get("result", {}).get("data", [])
            cutoff = datetime.now() - timedelta(hours=24)
            for news in news_list[:30]:
                title = news.get("title", "").strip()
                if not title:
                    continue
                content = news.get("digest", news.get("intro", "")).strip()
                ctime = news.get("ctime", "")
                try:
                    ctime_num = float(ctime) if ctime else 0
                except (ValueError, TypeError):
                    ctime_num = 0
                time_str = ""
                if ctime_num > 0:
                    try:
                        pub_time = datetime.fromtimestamp(ctime_num)
                        if pub_time < cutoff:
                            continue
                        time_str = pub_time.strftime("%m-%d %H:%M")
                    except Exception:
                        time_str = str(ctime)
                full_text = title + " " + content
                sent = _sentiment_analyzer.analyze(full_text)
                items.append({
                    "title": title,
                    "content": content[:200],
                    "time": time_str,
                    "source": "新浪财经",
                    "sentiment": self._score_to_label(sent["score"]),
                    "sentiment_score": sent["score"],
                    "sentiment_label": sent["label"],
                })
        except Exception as e:
            logger.error("解析新浪快讯失败: %s", e)
        return items

    async def _fetch_eastmoney_live(self) -> list[dict]:
        url = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
        params = {
            "client": "web",
            "biz": "web_news_col",
            "column": "350",
            "order": "1",
            "needInteractData": "0",
            "page_index": "1",
            "page_size": "20",
            "req_trace": str(int(datetime.now().timestamp() * 1000)),
        }
        data = await self._get_json(url, params=params)
        if not data:
            return []
        items = []
        try:
            news_list = data.get("data", {}).get("list", [])
            for news in news_list[:20]:
                title = news.get("title", "").strip()
                if not title:
                    continue
                content = news.get("summary", news.get("content", "")).strip()
                pub_time = news.get("showTime", news.get("show_time", ""))
                full_text = title + " " + content
                sent = _sentiment_analyzer.analyze(full_text)
                items.append({
                    "title": title,
                    "content": content[:200],
                    "time": str(pub_time) if pub_time else "",
                    "source": "东方财富7x24",
                    "sentiment": self._score_to_label(sent["score"]),
                    "sentiment_score": sent["score"],
                    "sentiment_label": sent["label"],
                })
        except Exception as e:
            logger.error("解析东方财富7x24数据失败: %s", e)
        return items

    def _score_to_label(self, score: float) -> str:
        if score >= 0.1:
            return "positive"
        elif score <= -0.1:
            return "negative"
        return "neutral"
