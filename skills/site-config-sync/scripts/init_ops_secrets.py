#!/usr/bin/env python3
"""
初始化 .local/ops-secrets.json 模板。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化 ops-secrets.json 模板")
    parser.add_argument("--ops-file", default=".local/ops-secrets.json", help="输出文件路径")
    parser.add_argument("--repo", default="", help="GitHub 仓库，格式 owner/repo")
    parser.add_argument("--environment", default="production", help="GitHub Environment 名称")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的文件")
    args = parser.parse_args()

    ops_file = Path(args.ops_file)
    ops_file.parent.mkdir(parents=True, exist_ok=True)

    if ops_file.exists() and not args.force:
        print(f"❌ 文件已存在: {ops_file}")
        print("ℹ️ 如需覆盖，请追加 --force")
        return 2

    template = {
        "repo": args.repo,
        "environment": args.environment,
        # 建议优先使用环境变量 GITHUB_PAT，避免长期明文落盘
        "github_pat": "",
        "accounts": [
            {
                "name": "example-linuxdo-account",
                "provider": "anyrouter",
                "linux.do": [{"username": "YOUR_LINUXDO_USERNAME", "password": "YOUR_LINUXDO_PASSWORD"}],
            }
        ],
        "providers": {},
        "dingtalk_webhook": "",
    }

    with ops_file.open("w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)

    print(f"✅ 已生成模板: {ops_file}")
    print("ℹ️ 下一步:")
    print("1) 填写 repo / github_pat / accounts")
    print("2) 执行 upsert_site_account.py 增改站点")
    print("3) 执行 sync_env_secrets.py 同步到 GitHub")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
