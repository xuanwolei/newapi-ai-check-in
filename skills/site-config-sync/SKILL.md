# 网站配置与 Secrets 同步 Skill

## 用途

用于后续快速完成以下操作：

1. 增加或修改签到站点账号（`ACCOUNTS`）。
2. 增加或修改自定义 provider（`PROVIDERS`）。
3. 一键同步到 GitHub `production` 环境 secrets。

## 依赖文件

- 配置文件：`.local/ops-secrets.json`
- 脚本目录：`skills/site-config-sync/scripts/`

## 标准流程

0. 首次使用先初始化模板：  

```bash
uv run python skills/site-config-sync/scripts/init_ops_secrets.py \
  --repo owner/repo \
  --environment production
```

建议：`github_pat` 可不写入文件，改用环境变量 `GITHUB_PAT`。

1. 更新/新增站点账号（写入 `.local/ops-secrets.json`）  
   内置 provider 示例（如 `anyrouter`）：

```bash
uv run python skills/site-config-sync/scripts/upsert_site_account.py \
  --provider anyrouter \
  --name anyrouter-linuxdo
```

2. 新增自定义站点（需要 `origin`）：

```bash
uv run python skills/site-config-sync/scripts/upsert_site_account.py \
  --provider ccll \
  --origin https://ccll.xyz \
  --name ccll-linuxdo
```

3. 如需显式指定 Linux.do 账号（否则复用现有账号）：

```bash
uv run python skills/site-config-sync/scripts/upsert_site_account.py \
  --provider anyrouter \
  --linuxdo-username YOUR_USERNAME \
  --linuxdo-password YOUR_PASSWORD
```

4. 同步 secrets 到 GitHub（默认同步 `ACCOUNTS`、`PROVIDERS`、`DINGDING_WEBHOOK`）：

```bash
# 推荐先设置环境变量，避免 token 落盘
# Windows PowerShell:
# $env:GITHUB_PAT='ghp_xxx'
# macOS/Linux:
# export GITHUB_PAT='ghp_xxx'

uv run --with pynacl python skills/site-config-sync/scripts/sync_env_secrets.py
```

5. 本地配置快速校验：

```bash
uv run python -c "import json,os;from utils.config import AppConfig;d=json.load(open('.local/ops-secrets.json','r',encoding='utf-8'));os.environ['ACCOUNTS']=json.dumps(d['accounts'],ensure_ascii=False);os.environ['PROVIDERS']=json.dumps(d.get('providers',{}),ensure_ascii=False);c=AppConfig.load_from_env();print(len(c.accounts),[a.provider for a in c.accounts])"
```

## 安全要求

1. `.local/ops-secrets.json` 包含敏感信息，不可提交到 git。
2. 同步脚本不会打印 secret 明文。
3. 若 token 或账号泄漏，必须立即轮换。
4. 同步使用的是 GitHub PAT，不是 GitLab Token；建议最小权限 `repo` + `workflow`。
