# AGENTS 快速入口

本项目支持通过本地 Skill 自动维护站点与 GitHub Actions secrets。

## 推荐入口

- Skill 文档：`skills/site-config-sync/SKILL.md`
- 初始化模板：`skills/site-config-sync/scripts/init_ops_secrets.py`
- 增改站点：`skills/site-config-sync/scripts/upsert_site_account.py`
- 同步 secrets：`skills/site-config-sync/scripts/sync_env_secrets.py`

## 最短流程

1. 初始化本地私有配置：

```bash
uv run python skills/site-config-sync/scripts/init_ops_secrets.py --repo owner/repo --environment production
```

2. 增加或修改站点：

```bash
uv run python skills/site-config-sync/scripts/upsert_site_account.py --provider anyrouter --name anyrouter-linuxdo
```

3. 同步到 GitHub Environment Secrets：

```bash
uv run --with pynacl python skills/site-config-sync/scripts/sync_env_secrets.py
```

## 注意事项

- `ops-secrets.json` 建议放在 `.local/`，且不得提交到 git。
- 同步使用 GitHub PAT（`repo` + `workflow`），不是 GitLab Token。
- GitHub PAT 需用户先手动创建并提供（获取说明见 `README.md` 的 `2.3.1`）。
