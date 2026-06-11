import asyncio
import logging
from typing import Any, Dict

import aiohttp
from astrbot.api import AstrBotConfig
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star

logger = logging.getLogger("astrbot")


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
        raw = config.get("api_base_url", "").rstrip("/")
        # 用户可能误填了完整的 API 路径，自动截取到域名部分
        if "/api/" in raw:
            idx = raw.index("/api/")
            raw = raw[:idx]
        self.api_base_url: str = raw
        self.admin_reminder: bool = config.get("admin_reminder", True)

        self._last_period: int = 0
        self._session: aiohttp.ClientSession | None = None

        # 注册插件 Page 的 API 路由（供前端 bridge.apiGet 调用）
        self._register_page_routes()

    # ─────────────────────── 初始化完成钩子 ───────────────────────────

    @filter.on_astrbot_loaded()
    async def _on_loaded(self):
        """AstrBot 初始化完成后，启动管理员提醒定时任务。"""
        if self.admin_reminder and self.api_base_url:
            asyncio.create_task(self._reminder_loop())

    # ──────────────────────────── Page 路由 ────────────────────────────

    def _register_page_routes(self) -> None:
        """通过 Context.register_web_api 注册 API 路由，供 bridge.apiGet 调用。
        路由格式：/插件目录名/端点名，bridge 会自动拼接 /api/plug/ 前缀。
        """
        pre = "/astrbot_plugin_abponsor/"
        self.context.register_web_api(
            f"{pre}sponsor-all", self._page_get_all, ["GET"], "获取赞助计划全部数据"
        )
        self.context.register_web_api(
            f"{pre}sponsor-current", self._page_get_current, ["GET"], "获取当前期赞助信息"
        )
        self.context.register_web_api(
            f"{pre}sponsor-history", self._page_get_previous_developers, ["GET"], "获取往期开发者列表"
        )

    async def _page_get_all(self) -> Dict[str, Any]:
        return await self._proxy_request("all")

    async def _page_get_current(self) -> Dict[str, Any]:
        return await self._proxy_request("current")

    async def _page_get_previous_developers(self) -> Dict[str, Any]:
        return await self._proxy_request("previous-developers")

    # ──────────────────────────── 代理请求 ────────────────────────────

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=15)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _proxy_request(self, path: str) -> Dict[str, Any]:
        """向公司后端 API 发起代理请求。"""
        if not self.api_base_url:
            return {"code": 500, "message": "API 地址未配置，请在插件配置中设置 api_base_url"}

        session = await self._get_session()
        url = f"{self.api_base_url}/api/{path}"
        try:
            async with session.get(url) as resp:
                logger.info(f"[赞助计划] 请求 {url} → status={resp.status} content_type={resp.content_type}")
                # 处理非 JSON 响应
                if "application/json" not in (resp.content_type or ""):
                    text = await resp.text()
                    logger.warning(f"[赞助计划] 非JSON响应: {text[:300]}")
                    return {"code": 500, "message": f"后端API返回非JSON: HTTP {resp.status}"}
                data = await resp.json()
                logger.info(f"[赞助计划] 响应 code={data.get('code')}, 有data={bool(data.get('data'))}")
                return data
        except aiohttp.ClientError as e:
            return {"code": 500, "message": f"后端 API 请求失败: {str(e)}"}
        except asyncio.TimeoutError:
            return {"code": 500, "message": "后端 API 请求超时"}

    # ──────────────────────────── 管理员提醒 ──────────────────────────

    async def _reminder_loop(self) -> None:
        """定时检测后端 API，发现新一期赞助计划时通知管理员。"""
        while True:
            try:
                data = await self._proxy_request("current")
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
                pass
            await asyncio.sleep(3600)

    async def _notify_admin(self, message: str) -> None:
        """向 AstrBot 管理员发送通知消息。"""
        try:
            admins = self.context.get_admins()
            if admins:
                await self.context.send_message(admins[0], message)
        except Exception:
            pass

    # ──────────────────────────── 用户指令 ────────────────────────────

    @filter.command("赞助计划")
    async def sponsor(self, event: AstrMessageEvent):
        """/赞助计划 查看赞助计划摘要。"""
        data = await self._proxy_request("all")
        if data.get("code") != 200:
            yield event.plain_result("⚠️ 赞助计划数据获取失败，请稍后重试。")
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
            for dev in previous[:5]:
                lines.append(
                    f"  · {dev.get('name', '—')} "
                    f"(第{dev.get('period', '—')}期, "
                    f"{dev.get('amount', 0)}元, "
                    f"{dev.get('project', '—')})"
                )
            if len(previous) > 5:
                lines.append(f"  ... 共 {len(previous)} 位开发者")

        lines.append("━━━━━━━━━━━━━━━━")
        yield event.plain_result("\n".join(lines))

    # ──────────────────────────── 清理 ────────────────────────────────

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session and not self._session.closed:
            await self._session.close()
