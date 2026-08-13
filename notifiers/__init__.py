from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import time
import urllib.parse
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    @abstractmethod
    async def send(self, content: str) -> bool:
        ...


class ConsoleNotifier(BaseNotifier):
    async def send(self, content: str) -> bool:
        import sys
        import io
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
            except Exception:
                pass
        try:
            print(content)
        except UnicodeEncodeError:
            safe = content.encode('utf-8', errors='replace').decode('utf-8')
            print(safe)
        return True


class FileNotifier(BaseNotifier):
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir

    async def send(self, content: str) -> bool:
        import os
        from datetime import datetime

        os.makedirs(self.output_dir, exist_ok=True)
        filename = datetime.now().strftime("%Y-%m-%d_morning_brief.txt")
        filepath = os.path.join(self.output_dir, filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info("简报已保存到 %s", filepath)
            return True
        except Exception as e:
            logger.error("保存简报失败: %s", e)
            return False


class FeishuNotifier(BaseNotifier):
    """飞书自定义机器人通知器，支持签名校验（加签）。

    通过环境变量配置（GitHub Actions 用 secrets 注入）：
      LARK_WEBHOOK : 自定义机器人 webhook 地址
      LARK_SECRET  : 加签密钥（机器人安全设置里开启“签名校验”后获得）
    未配置 LARK_WEBHOOK 则静默跳过；未配置 LARK_SECRET 按无签名方式发送。
    消息超过 LARK_MAX_LEN（默认 4000 字符）自动分片发送。
    """

    def __init__(self, webhook: str | None = None, secret: str | None = None):
        self.webhook = webhook or os.getenv("LARK_WEBHOOK")
        self.secret = secret or os.getenv("LARK_SECRET")
        self.timeout = int(os.getenv("LARK_TIMEOUT", "15"))
        self.max_len = int(os.getenv("LARK_MAX_LEN", "4000"))

    def _signed_url(self) -> str:
        url = self.webhook
        if not self.secret:
            return url
        timestamp = str(int(time.time()))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}timestamp={timestamp}&sign={urllib.parse.quote_plus(sign)}"

    def _chunks(self, text: str):
        if len(text) <= self.max_len:
            return [text]
        return [text[i : i + self.max_len] for i in range(0, len(text), self.max_len)]

    async def send(self, content: str) -> bool:
        if not self.webhook:
            logger.warning("未配置 LARK_WEBHOOK，跳过飞书推送")
            return False
        url = self._signed_url()
        chunks = self._chunks(content)
        ok = True
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for idx, chunk in enumerate(chunks, 1):
                payload = {"msg_type": "text", "content": {"text": chunk}}
                try:
                    resp = await client.post(url, json=payload)
                    data = resp.json()
                except Exception as e:
                    logger.error("飞书推送请求失败: %s", e)
                    ok = False
                    continue
                if data.get("code") != 0:
                    logger.error("飞书推送失败 [%d/%d]: %s", idx, len(chunks), data)
                    ok = False
                else:
                    logger.info("飞书推送成功 [%d/%d]", idx, len(chunks))
        return ok
