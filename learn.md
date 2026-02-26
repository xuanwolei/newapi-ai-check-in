# Linux.do 授权原理与 GitHub Actions 配置记录

## 1. 这项目里 Linux.do 授权的原理是什么？

结论：这是 **OAuth 授权码流程 + 站点会话 cookies**，不是长期固定 token 模式。

主链路：
1. `main.py` 调用 `CheckIn.execute()`。
2. `checkin.py` 在 Linux.do 分支中先获取 provider 的 `client_id` 和 `auth_state`。
3. 进入 `sign_in_with_linuxdo.py`，浏览器访问 `https://connect.linux.do/oauth2/authorize?...`。
4. 登录 Linux.do 并点击授权后，回跳到目标 provider。
5. 从回跳后的页面提取 `api_user` 和用户 cookies，再调用签到接口完成签到。

## 2. 需要每次都登录 Linux.do 吗？

结论：**不一定**。

项目会将浏览器会话状态保存到 `storage-states/linuxdo_<hash>_storage_state.json`。

运行时会先尝试加载该缓存：
- 如果缓存有效，通常可直接进入授权流程，不需要重新输入账号密码。
- 如果缓存失效（过期、风控、缓存 miss），才会重新登录。

## 3. 会记录 token 吗？

结论：会记录的是 **浏览器会话状态**（cookies/localStorage 等），而不是让你手工维护一个永久 token。

签到时真正使用的是当前 OAuth 回跳后得到的会话信息与用户信息（如 `api_user`、cookies）。

## 4. 在 GitHub Actions 上如何把环境变量配置到可跑通？

### 最小可跑通方案

只配置 `ACCOUNTS` 即可先跑通（`PROVIDERS` 可不配，走内置 provider）。

示例（放到 `production` 环境的 Secret `ACCOUNTS`）：

```json
[
  {
    "name": "my-anyrouter-linuxdo",
    "provider": "anyrouter",
    "linux.do": [
      { "username": "你的linuxdo用户名", "password": "你的linuxdo密码" }
    ]
  }
]
```

### 什么时候必须配置全局账号？

如果你在 `ACCOUNTS` 里写的是：

```json
{ "linux.do": true }
```

或

```json
{ "github": true }
```

那就必须额外配置：
- `ACCOUNTS_LINUX_DO`
- `ACCOUNTS_GITHUB`

### 本仓库 workflow 的缓存行为

`checkin.yml` 会恢复并保存 `storage-states` 缓存，所以登录态可以跨次运行复用。

## 5. 本次疑问汇总（Q&A）

Q1：Linux.do 授权是啥原理？  
A1：OAuth 授权码流程，回跳后拿会话 cookies + api_user 完成签到。

Q2：每次都要登录吗？  
A2：不一定。优先复用 `storage-states` 缓存，失效才重登。

Q3：会记录 token 吗？  
A3：主要记录浏览器会话状态，不是固定长期 token。

Q4：GitHub Action 怎么配才能跑通？  
A4：先配 `ACCOUNTS`（最小集），再按是否使用 `linux.do: true/github: true` 决定是否补全 `ACCOUNTS_LINUX_DO/ACCOUNTS_GITHUB`。

## 6. 本地调试是怎么执行的？

本地调试时，使用了一个启动器脚本做三件事：
1. 读取 `.local/ops-secrets.json` 的 `accounts/providers`。
2. 注入环境变量：`ACCOUNTS`、`PROVIDERS`、`PROXY`、`DEBUG`。
3. 执行 `uv run python -u main.py` 跑完整签到流程。

本次可用代理配置示例：

```json
{"server":"socks5://127.0.0.1:10808"}
```

说明：
- 代理会同时作用到 `curl_cffi` 请求与 Camoufox 浏览器流程。
- 本地 `127.0.0.1:10808` 只对本机有效，GitHub Actions runner 无法直接使用本地回环代理。

## 7. 执行链路（调试视角）

1. `main.py` 加载配置并遍历账号。
2. `checkin.py` 进入 Linux.do 分支，先请求 provider 的 `/api/status` 和 `/api/oauth/state`。
3. `sign_in_with_linuxdo.py` 启动浏览器走 OAuth 授权，优先复用 `storage-states` 缓存登录态。
4. 若缓存失效则重新登录 Linux.do 并点击授权。
5. 回跳后提取 `api_user` 与 cookies，继续走签到/余额查询。

## 8. 看到弹出窗口时，实际是什么浏览器？

结论：是 **Camoufox 浏览器实例**，不是系统默认浏览器。

代码使用的是 `AsyncCamoufox(..., headless=False)`，因此会看到真实浏览器窗口。  
接口层请求仍由 `curl_cffi` 完成（例如日志中的 `impersonate=chrome136`）。

## 9. 敏感信息存放建议

- 可以将账号与 token 放在 `.local/ops-secrets.json` 供本地复用。
- 必须确保该文件不进入 git（推荐放在 `.git/info/exclude` 或 `.gitignore`）。
- 账号密码和 PAT 一旦明文外泄，应及时轮换。
