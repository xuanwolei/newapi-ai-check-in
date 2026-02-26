#!/usr/bin/env python3
"""
将 .local/ops-secrets.json 中的关键配置同步到 GitHub environment secrets。
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

def request(token: str, method: str, url: str, data: dict | None = None) -> tuple[int, dict | str | None]:
    """发送 GitHub API 请求。"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "site-config-sync",
    }
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return e.code, parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="同步 ACCOUNTS/PROVIDERS 到 GitHub Environment Secrets")
    parser.add_argument("--ops-file", default=".local/ops-secrets.json", help="ops secrets 文件路径")
    parser.add_argument(
        "--skip-dingtalk",
        action="store_true",
        help="跳过 DINGDING_WEBHOOK 同步",
    )
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
            ops = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        print(f"ℹ️ 请检查文件格式: {ops_file}")
        return 2

    repo = ops.get("repo", "")
    env_name = ops.get("environment", "production")
    # 优先环境变量，避免 token 长期明文落盘
    token = os.getenv("GITHUB_PAT", "").strip() or ops.get("github_pat", "").strip()

    if not repo:
        print("❌ 缺少 repo 配置（应为 owner/repo）")
        print("ℹ️ 可在 ops-secrets.json 中填写，例如: xuanwolei/newapi-ai-check-in")
        return 2

    if not token:
        print("❌ 缺少 GitHub Token")
        print("ℹ️ 请配置以下任一方式：")
        print("1) 环境变量 GITHUB_PAT")
        print("2) ops-secrets.json 字段 github_pat")
        print("ℹ️ Token 类型应为 GitHub PAT（非 GitLab Token），至少包含 scope: repo, workflow")
        return 2

    accounts = ops.get("accounts", [])
    if not isinstance(accounts, list) or len(accounts) == 0:
        print("❌ accounts 不能为空，且必须为数组")
        return 2

    providers = ops.get("providers", {})
    if not isinstance(providers, dict):
        print("❌ providers 必须为对象（JSON object）")
        return 2

    try:
        from nacl.public import PublicKey, SealedBox
    except ModuleNotFoundError:
        print("❌ 缺少依赖: pynacl")
        print("ℹ️ 请使用以下命令运行：")
        print("uv run --with pynacl python skills/site-config-sync/scripts/sync_env_secrets.py")
        return 2

    payloads = {
        "ACCOUNTS": json.dumps(accounts, ensure_ascii=False, separators=(",", ":")),
        "PROVIDERS": json.dumps(providers, ensure_ascii=False, separators=(",", ":")),
    }

    dingtalk = ops.get("dingtalk_webhook", "")
    if dingtalk and not args.skip_dingtalk:
        payloads["DINGDING_WEBHOOK"] = dingtalk

    base = "https://api.github.com"

    # 确保 environment 已存在
    ensure_url = f"{base}/repos/{repo}/environments/{env_name}"
    status, result = request(token, "PUT", ensure_url, {})
    if status not in (200, 201):
        raise RuntimeError(f"创建/检查 environment 失败: HTTP {status}, {result}")

    key_url = f"{base}/repos/{repo}/environments/{env_name}/secrets/public-key"
    status, key_resp = request(token, "GET", key_url)
    if status != 200 or not isinstance(key_resp, dict):
        raise RuntimeError(f"获取 public key 失败: HTTP {status}, {key_resp}")

    key_id = key_resp["key_id"]
    public_key = PublicKey(base64.b64decode(key_resp["key"]))
    box = SealedBox(public_key)

    for name, value in payloads.items():
        encrypted_value = base64.b64encode(box.encrypt(value.encode("utf-8"))).decode("utf-8")
        put_url = f"{base}/repos/{repo}/environments/{env_name}/secrets/{name}"
        status, result = request(
            token,
            "PUT",
            put_url,
            {"encrypted_value": encrypted_value, "key_id": key_id},
        )
        if status not in (201, 204):
            raise RuntimeError(f"写入 secret 失败: {name}, HTTP {status}, {result}")
        print(f"✅ 已同步 secret: {name}")

    print(f"🎉 同步完成: repo={repo}, environment={env_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
