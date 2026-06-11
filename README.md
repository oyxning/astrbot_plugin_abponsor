# Sponsor API - 赞助计划信息发布服务

## API 接口

### 基础约定

- **Content-Type**: `application/json`
- **CORS**: 已全放开
- **限流**: 每 IP 10 秒内最多 200 次请求
- **响应格式**: 统一 `{ "code": 200, "data": ... }`

---

### GET /api/all

获取完整数据（推荐前端使用此接口）。

**响应示例**:

```json
{
  "code": 200,
  "data": {
    "current": {
      "period": 1,
      "announcement": "欢迎参加第1期赞助计划",
      "registrantCount": 50,
      "sponsorAmount": 10000,
      "reviewerCount": 5,
      "voteUrl": "https://example.com/vote/1",
      "registrationEnabled": true,
      "registrationUrl": "https://fixed.com/register",
      "summaryEnabled": false,
      "summaryUrl": "https://fixed.com/summary"
    },
    "previousDevelopers": [
      { "name": "张三", "period": 1, "amount": 5000, "project": "开源项目A" }
    ]
  }
}
```

**字段说明** (`data.current`):

| 字段 | 类型 | 说明 |
|------|------|------|
| period | number | 当前第几期 |
| announcement | string | 活动公告 |
| registrantCount | number | 本期报名人数 |
| sponsorAmount | number | 本期赞助总金额 |
| reviewerCount | number | 本期评选人数 |
| voteUrl | string | 投票入口链接（每期可配） |
| registrationEnabled | boolean | 报名按钮是否可点击 |
| registrationUrl | string | 报名链接（固定不变） |
| summaryEnabled | boolean | 查询总表按钮是否可点击 |
| summaryUrl | string | 总表链接（固定不变） |

---

### GET /api/current

仅返回当前期赞助计划信息（`data.current` 部分）。

---

### GET /api/previous-developers

仅返回往期开发者列表。

```json
{
  "code": 200,
  "data": [
    { "name": "张三", "period": 1, "amount": 5000, "project": "开源项目A" }
  ]
}
```

---

### PUT /api/current

更新当前期配置。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| period | number | 否 | 第几期 |
| announcement | string | 否 | 活动公告 |
| registrantCount | number | 否 | 报名人数 |
| sponsorAmount | number | 否 | 赞助金额 |
| reviewerCount | number | 否 | 评选人数 |
| voteUrl | string | 否 | 投票链接 |
| registrationEnabled | boolean | 否 | 开放报名 |
| registrationUrl | string | 否 | 报名链接 |
| summaryEnabled | boolean | 否 | 开放总表 |
| summaryUrl | string | 否 | 总表链接 |

> 只传要改的字段，其余保持不变。

---

### POST /api/previous-developers

添加一位往期获赞助开发者。

```json
{
  "name": "张三",
  "period": 1,
  "amount": 5000,
  "project": "开源项目A"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 开发者名称 |
| period | number | 是 | 期数 |
| amount | number | 否 | 赞助金额 |
| project | string | 否 | 项目名称 |

---

### GET /health

健康检查。

```json
{ "status": "ok", "uptime": 123.45 }
```

---

## 典型发布流程

1. **新一期开始**: 在 `/admin` 页面更新 `period`、`announcement`、`voteUrl`，开启 `registrationEnabled`，重置计数为 0
2. **报名进行中**: 更新 `registrantCount`（递增）
3. **报名截止**: 关闭 `registrationEnabled`
4. **本期结束**: 开启 `summaryEnabled`，添加获赞助开发者
5. **前端无需改动** — 自动拉取最新 JSON

---

## 防灾机制

| 机制 | 实现 |
|------|------|
| 内存缓存 | 3 秒 TTL，磁盘故障时用缓存兜底 |
| 限流 | 令牌桶，每 IP 10 秒 200 次 |
| 熔断 | 连续 10 次 5xx 自动熔断 15 秒 |
| 数据持久化 | `data/db.json` 挂载到宿主机 |
