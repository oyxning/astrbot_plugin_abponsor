import asyncio
import json
import os
from typing import Any, Dict

import aiohttp
from astrbot.api import AstrBotConfig, Context, Star
from astrbot.api.event import EventResult


class SponsorPlugin(Star):
    """赞助计划信息展示插件

    通过 AstrBot 插件 Pages 展示公司赞助计划数据，包括：
    - 当前期赞助信息（期数、公告、报名人数、赞助金额、评选人数）
    - 往期获赞助开发者列表
    - 投票入口、报名入口、总表入口
    """

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.api_base_url: str = config.get("api_base_url", "").rstrip("/")
        self.admin_reminder: bool = config.get("admin_reminder", True)

        self._last_period: int = 0
        self._session: aiohttp.ClientSession | None = None

        # 注册插件 Page 所需的 API 代理路由
        self._register_page_routes()

        # 若开启管理员提醒，启动定时检测任务
        if self.admin_reminder and self.api_base_url:
            asyncio.ensure_future(self._reminder_loop())

    # ──────────────────────────── 路由注册 ────────────────────────────

    def _register_page_routes(self) -> None:
        """向 AstrBot 注册插件 Page 可调用的 API 路由。"""
        self.context.register_page_handler("GET", "all", self._proxy_get_all)
        self.context.register_page_handler("GET", "current", self._proxy_get_current)
        self.context.register_page_handler("GET", "previous-developers", self._proxy_get_previous_developers)

    # ──────────────────────────── 代理请求 ────────────────────────────

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=15)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _proxy_request(self, method: str, path: str) -> Dict[str, Any]:
        """向公司后端 API 发起代理请求。"""
        if not self.api_base_url:
            return {"code": 500, "message": "API 地址未配置，请在插件配置中设置 api_base_url"}

        session = await self._get_session()
        url = f"{self.api_base_url}/api/{path}"
        try:
            async with session.request(method, url) as resp:
                data = await resp.json()
                return data
        except aiohttp.ClientError as e:
            return {"code": 500, "message": f"后端 API 请求失败: {str(e)}"}
        except asyncio.TimeoutError:
            return {"code": 500, "message": "后端 API 请求超时"}

    async def _proxy_get_all(self) -> Dict[str, Any]:
        return await self._proxy_request("GET", "all")

    async def _proxy_get_current(self) -> Dict[str, Any]:
        return await self._proxy_request("GET", "current")

    async def _proxy_get_previous_developers(self) -> Dict[str, Any]:
        return await self._proxy_request("GET", "previous-developers")

    # ──────────────────────── 管理员提醒 ──────────────────────────────

    async def _reminder_loop(self) -> None:
        """定时检测后端 API，发现新一期赞助计划时通知管理员。"""
        while True:
            try:
                data = await self._proxy_request("GET", "current")
                if data.get("code") == 200:
                    current_data = data.get("data", {})
                    current_period = current_data.get("period", 0)

                    if self._last_period > 0 and current_period > self._last_period:
                        announcement = current_data.get("announcement", "")
                        sponsor_amount = current_data.get("sponsorAmount", 0)
                        msg = (
                            f"🔔 新一期赞助计划已开始！\n"
                            f"━━━━━━━━━━━━━━━━\n"
                            f"第 {current_period} 期\n"
                            f"公告：{announcement}\n"
                            f"赞助金额：{sponsor_amount} 元\n"
                            f"━━━━━━━━━━━━━━━━\n"
                            f"请在 WebUI 插件页面查看详情。"
                        )
                        await self._notify_admin(msg)

                    self._last_period = current_period
            except Exception:
                pass  # 静默处理，避免日志刷屏
            await asyncio.sleep(3600)  # 每小时检测一次

    async def _notify_admin(self, message: str) -> None:
        """向 AstrBot 管理员发送通知消息。"""
        try:
            await self.context.send_message_to_admin(message)
        except Exception:
            pass

    # ──────────────────────────── 用户指令 ────────────────────────────

    async def on_message(self, event) -> EventResult | None:
        """处理用户消息指令。"""
        msg = event.get_message_str().strip()

        if msg == "/赞助计划" or msg == "/sponsor":
            await self._send_sponsor_summary(event)
            return EventResult(stop=True)

        return None

    async def _send_sponsor_summary(self, event) -> None:
        """在聊天窗口中输出赞助计划摘要。"""
        data = await self._proxy_get_all()
        if data.get("code") != 200:
            await event.reply("⚠️ 赞助计划数据获取失败，请稍后重试。")
            return

        info = data.get("data", {})
        current = info.get("current", {})
        previous = info.get("previousDevelopers", [])

        period = current.get("period", "—")
        announcement = current.get("announcement", "暂无公告")
        registrant_count = current.get("registrantCount", 0)
        sponsor_amount = current.get("sponsorAmount", 0)
        reviewer_count = current.get("reviewerCount", 0)
        vote_url = current.get("voteUrl", "")
        registration_enabled = current.get("registrationEnabled", False)
        registration_url = current.get("registrationUrl", "")
        summary_enabled = current.get("summaryEnabled", False)
        summary_url = current.get("summaryUrl", "")

        lines = [
            f"💰 第 {period} 期赞助计划",
            f"━━━━━━━━━━━━━━━━",
            f"📢 公告：{announcement}",
            f"👥 报名人数：{registrant_count}",
            f"💵 赞助金额：{sponsor_amount} 元",
            f"🏆 评选人数：{reviewer_count}",
        ]

        if vote_url:
            lines.append(f"🗳️ 投票入口：{vote_url}")
        if registration_enabled and registration_url:
            lines.append(f"📝 报名入口：{registration_url}")
        if summary_enabled and summary_url:
            lines.append(f"📊 总表查询：{summary_url}")

        if previous:
            lines.append("")
            lines.append("🏅 往期获赞助开发者：")
            for dev in previous[:5]:  # 最多显示 5 位
                lines.append(
                    f"  · {dev.get('name', '—')} "
                    f"(第{dev.get('period', '—')}期, "
                    f"{dev.get('amount', 0)}元, "
                    f"{dev.get('project', '—')})"
                )
            if len(previous) > 5:
                lines.append(f"  ... 共 {len(previous)} 位开发者")

        lines.append("━━━━━━━━━━━━━━━━")
        await event.reply("\n".join(lines))

    # ──────────────────────────── 清理 ────────────────────────────────

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session and not self._session.closed:
            await self._session.close()
