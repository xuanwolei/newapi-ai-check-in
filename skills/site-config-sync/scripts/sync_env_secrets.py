#!/usr/bin/env python3
"""
将 .local/ops-secrets.json 中的关键配置同步到 GitHub environment secrets。
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import urllib.error
import urllib.request

from nacl.public import PublicKey, SealedBox


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
        raise FileNotFoundError(f"文件不存在: {ops_file}")

    with ops_file.open("r", encoding="utf-8") as f:
        ops = json.load(f)

    repo = ops.get("repo", "")
    env_name = ops.get("environment", "production")
    token = ops.get("github_pat", "")
    if not repo or not token:
        raise ValueError("ops-secrets.json 缺少 repo 或 github_pat")

    payloads = {
        "ACCOUNTS": json.dumps(ops.get("accounts", []), ensure_ascii=False, separators=(",", ":")),
        "PROVIDERS": json.dumps(ops.get("providers", {}), ensure_ascii=False, separators=(",", ":")),
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
