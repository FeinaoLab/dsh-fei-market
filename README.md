# dsh-fei-market

飞系插件索引源：把飞系（52 个企业管理系统 + 飞脑 Agent 网关）接入 DeepSeek Harness 的「发现」页。

## 用法

在 DSH 桌面端/Web UI：插件 → 实验性插件 → 打开「自定义插件索引」→ 发现 → 添加索引源：

```text
https://raw.githubusercontent.com/dukema81/dsh-fei-market/main/site/index.json
```

## 结构

```text
site/index.json      # 索引（format 1，官方 schema）
site/icons/          # 插件图标（与索引同源发布）
tools/validate_index.py  # 发布前校验器（按官方格式参考实现）
```

## 规则

- 索引是第三方内容：DSH 只检查格式，不验证声明。本源只收录飞系自研组合包。
- 发布前必须跑 `python tools/validate_index.py site/index.json`，全绿才推。
- 只用 https 源。

## 收录

| 插件 | 版本 | 说明 |
|---|---|---|
| dsh-plugin-fei-bridge | 0.1.0 | 飞系桥接第一块基石（fei-bridge 插件行） |
