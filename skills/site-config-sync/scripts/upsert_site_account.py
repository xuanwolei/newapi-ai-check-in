#!/usr/bin/env python3
"""
更新 .local/ops-secrets.json 中的账号与 provider 配置。
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path


def build_default_provider(origin: str) -> dict:
    """构建自定义 provider 的默认配置。"""
    return {
        "origin": origin,
        "login_path": "/login",
        "status_path": "/api/status",
        "auth_state_path": "/api/oauth/state",
        "check_in_path": "/api/user/checkin",
        "check_in_status": True,
        "user_info_path": "/api/user/self",
        "topup_path": "/api/user/topup",
        "api_user_key": "new-api-user",
        "linuxdo_auth_path": "/api/oauth/linuxdo",
        "linuxdo_auth_redirect_path": "/oauth/**",
        "github_auth_path": "/api/oauth/github",
        "github_auth_redirect_path": "/oauth/**",
    }


def pick_linuxdo_accounts(data: dict, username: str | None, password: str | None) -> list[dict]:
    """优先使用入参账号，否则复用已有 linux.do 账号。"""
    if username and password:
        return [{"username": username, "password": password}]

    accounts = data.get("accounts", [])
    for account in accounts:
        linuxdo = account.get("linux.do")
        if isinstance(linuxdo, list) and linuxdo:
            return deepcopy(linuxdo)

    raise ValueError("未找到可复用的 linux.do 账号，请通过参数传入用户名和密码")


def upsert_account(
    data: dict,
    provider: str,
    name: str | None,
    linuxdo_accounts: list[dict],
) -> None:
    """按 provider 更新或新增账号配置。"""
    accounts = data.setdefault("accounts", [])
    account_name = name or f"{provider}-linuxdo"

    for account in accounts:
        if account.get("provider") == provider:
            account["name"] = account_name
            account["linux.do"] = deepcopy(linuxdo_accounts)
            return

    accounts.append(
        {
            "name": account_name,
            "provider": provider,
            "linux.do": deepcopy(linuxdo_accounts),
        }
    )


def upsert_provider(data: dict, provider: str, origin: str) -> None:
    """更新或新增自定义 provider。"""
    providers = data.setdefault("providers", {})
    current = providers.get(provider, {})
    merged = build_default_provider(origin)
    merged.update(current)
    merged["origin"] = origin
    providers[provider] = merged


def main() -> int:
    parser = argparse.ArgumentParser(description="更新 ops-secrets 中的网站账号配置")
    parser.add_argument("--ops-file", default=".local/ops-secrets.json", help="ops secrets 文件路径")
    parser.add_argument("--provider", required=True, help="provider 名称，例如 anyrouter / ccll")
    parser.add_argument("--name", help="账号显示名称，默认 <provider>-linuxdo")
    parser.add_argument("--origin", help="自定义 provider 的站点地址，例如 https://ccll.xyz")
    parser.add_argument("--linuxdo-username", help="Linux.do 用户名")
    parser.add_argument("--linuxdo-password", help="Linux.do 密码")
    args = parser.parse_args()

    ops_file = Path(args.ops_file)
    if not ops_file.exists():
        print(f"❌ 文件不存在: {ops_file}")
        print("ℹ️ 请先初始化模板：")
        print(
            "uv run python skills/site-config-sync/scripts/init_ops_secrets.py "
            f"--ops-file {args.ops_file}"
        )
        return 2

    try:
        with ops_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        print(f"ℹ️ 请检查文件格式: {ops_file}")
        return 2

    try:
        linuxdo_accounts = pick_linuxdo_accounts(data, args.linuxdo_username, args.linuxdo_password)
    except ValueError as e:
        print(f"❌ {e}")
        print("ℹ️ 可通过参数显式传入：--linuxdo-username 和 --linuxdo-password")
        return 2

    upsert_account(data, args.provider, args.name, linuxdo_accounts)

    if args.origin:
        upsert_provider(data, args.provider, args.origin)

    with ops_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    providers = [a.get("provider", "") for a in data.get("accounts", [])]
    print(f"✅ 已更新: {ops_file}")
    print(f"ℹ️ 账号总数: {len(data.get('accounts', []))}")
    print(f"ℹ️ provider 列表: {providers}")
    if args.origin:
        print(f"ℹ️ 已写入自定义 provider: {args.provider} -> {args.origin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
