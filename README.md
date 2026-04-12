# Bug Agent - 智能Bug分析助手

一个用于辅助开发人员分析和解决测试环境 Bug 的工具。

## 快速开始

### 1. 安装依赖

```bash
cd server
pip install -r requirements.txt
```

### 2. 配置

编辑 `config.yaml`，设置：
- 日志 API 的地址和认证信息
- LLM 提供商的 API Key
- 项目根目录

### 3. 启动服务

```bash
python server/main.py
```

服务默认启动在 http://127.0.0.1:8765

### 4. IDE 插件

参考 `jetbrains-plugin/README.md` 安装 JetBrains 插件

## 功能特性

- 自动获取测试环境日志
- 智能解析 Java StackTrace
- 代码上下文分析
- LLM 驱动的根因分析
- 自动生成修复建议
- 一键代码修复

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| /analyze | POST | 分析错误信息 |
| /logs | GET | 获取日志列表 |
| /logs/{id} | GET | 获取日志详情 |
| /fix | POST | 执行代码修复 |
| /health | GET | 健康检查 |
