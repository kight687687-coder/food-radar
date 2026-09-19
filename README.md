# 食安雷达

食安雷达是一款面向家庭场景的微信小程序，提供配料表识别、食品添加剂查询、食品安全风险提示、AI 营养问答和家庭健康档案管理。

## 核心功能

- 配料表拍照识别
- 食品安全评分与风险提示
- 添加剂百科查询
- 配料表对比
- AI 营养师问答
- 家庭成员与健康档案管理

## 项目结构

- `miniprogram/` 微信小程序前端
- `backend/` Flask 后端服务
- `docs/` 设计与规范文档

## 技术栈

- 微信小程序
- Flask
- SQLite / 本地数据文件
- OpenAI / DeepSeek 风格 AI 接口

## 运行说明

前端和后端分开运行。

### 后端

```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 小程序

用微信开发者工具打开 `miniprogram/` 目录。

## 说明

本项目提供的分析结果仅用于日常食品风险参考，不替代医学、营养或监管结论。

## Web 版

The original WeChat mini-program remains under `miniprogram/`. The browser migration is an independent React/Vite app under `web/`.

不要通过 `file:///.../web/index.html` 直接打开。最简单的本地启动方式是双击仓库根目录的 `启动Web版.bat`。

From the repository root:

```bash
npm install
npm run build
```

For local development run `npm run dev` and open the URL printed by Vite. For Vercel, set Root Directory to `web`, Build Command to `npm run build`, and Output Directory to `dist`. See `web/README.md` for the backend environment variable and deployment notes.
