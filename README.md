# AstrBot 赞助计划插件

在 AstrBot WebUI 中展示公司赞助计划数据，支持聊天指令快速查询摘要，以及新一期自动通知管理员。

- **赞助计划官网**：[abponsor.tongujiyu.cn](https://abponsor.tongujiyu.cn)
- **免责声明**：本赞助计划与 AstrBot 团队无任何直接的商业关联，仅面向非官方插件开发者提供赞助支持。

## 功能

- **Dashboard Page**：在 WebUI 插件详情页展示期数、活动公告、报名人数、赞助金额、评选人数、投票/报名/总表入口、往期获赞助开发者
- **聊天指令**：群聊中发送 `/赞助计划` 查看赞助计划摘要
- **管理员提醒**：每小时轮询后端，发现新一期时自动通知管理员（可在配置中开关）
- **投票入口兜底**：后端未配置投票 URL 时显示"暂未开放投票"

## 配置

在 WebUI 插件配置页面填写：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `api_base_url` | 公司赞助计划后端 API 地址，例如 `https://sponsor.example.com` | 空 |
| `admin_reminder` | 是否提醒管理员新一期开始 | `true` |

## 依赖的后端 API

插件作为代理，将前端请求转发到公司后端。后端需提供以下接口（`{api_base_url}` 即配置中的地址）：

| 接口 | 说明 |
|------|------|
| `GET {api_base_url}/api/all` | 获取完整数据（current + previousDevelopers） |
| `GET {api_base_url}/api/current` | 获取当前期信息 |
| `GET {api_base_url}/api/previous-developers` | 获取往期开发者列表 |

### 响应格式

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

### 字段说明 (data.current)

| 字段 | 类型 | 说明 |
|------|------|------|
| period | number | 当前第几期 |
| announcement | string | 活动公告 |
| registrantCount | number | 报名人数 |
| sponsorAmount | number | 赞助金额 |
| reviewerCount | number | 评选人数 |
| voteUrl | string | 投票链接（空则不显示投票按钮） |
| registrationEnabled | boolean | 是否开放报名 |
| registrationUrl | string | 报名链接 |
| summaryEnabled | boolean | 是否开放总表 |
| summaryUrl | string | 总表链接 |

## 文件结构

```
astrbot_plugin_abponsor/
├── _conf_schema.json       # 插件配置定义
├── metadata.yaml            # 插件元数据
├── requirements.txt         # Python 依赖 (aiohttp)
├── main.py                  # 插件主逻辑
└── pages/
    └── sponsor/
        ├── index.html       # Dashboard Page
        ├── app.js           # 页面逻辑
        └── style.css        # 页面样式
```
