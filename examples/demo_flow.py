import requests
import json

BASE_URL = "http://localhost:8000"
ADMIN_TOKEN = "admin-token-change-me"

admin_headers = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Content-Type": "application/json",
}


def divider(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def step(name: str):
    print(f"---> {name}")


def main():
    divider("Step 0: Health Check")
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    print(f"status={r.status_code} body={r.json()}")
    assert r.status_code == 200

    divider("Step 1: 创建应用")
    payload = {"name": "Demo Order Service", "owner": "team-order", "description": "订单服务对接用"}
    step("POST /api/v1/admin/applications")
    r = requests.post(f"{BASE_URL}/api/v1/admin/applications", headers=admin_headers, json=payload)
    print(f"status={r.status_code} body={json.dumps(r.json(), indent=2, ensure_ascii=False)}")
    assert r.status_code == 201
    app = r.json()
    app_id = app["app_id"]
    print(f"Got app_id = {app_id}")

    divider("Step 2: 为应用发放访问凭证 (API Key / Secret)")
    payload = {"name": "production-key-01"}
    step("POST /api/v1/admin/applications/{app_id}/credentials")
    r = requests.post(
        f"{BASE_URL}/api/v1/admin/applications/{app_id}/credentials",
        headers=admin_headers,
        json=payload,
    )
    print(f"status={r.status_code} body={json.dumps(r.json(), indent=2, ensure_ascii=False)}")
    assert r.status_code == 201
    cred = r.json()
    api_key = cred["api_key"]
    api_secret = cred["api_secret"]
    print(f"保存好：api_key={api_key}")
    print(f"保存好：api_secret={api_secret}")
    print(f"指纹（数据库里只存这个和 hash）：{cred['secret_fingerprint']}")

    divider("Step 3: 使用 API Key 调用受保护的 Demo 接口")
    api_headers = {"X-API-Key": api_key, "X-API-Secret": api_secret}

    step("GET /api/v1/demo/hello")
    r = requests.get(f"{BASE_URL}/api/v1/demo/hello", headers=api_headers)
    print(f"status={r.status_code} body={json.dumps(r.json(), indent=2, ensure_ascii=False)}")
    assert r.status_code == 200

    step("POST /api/v1/demo/echo")
    r = requests.post(
        f"{BASE_URL}/api/v1/demo/echo",
        headers={**api_headers, "Content-Type": "application/json"},
        json={"message": "hello audit", "extra": {"trace": "abc123"}},
    )
    print(f"status={r.status_code} body={json.dumps(r.json(), indent=2, ensure_ascii=False)}")
    assert r.status_code == 200
    request_id_1 = r.headers.get("X-Request-ID")
    print(f"X-Request-ID = {request_id_1}")

    step("GET /api/v1/demo/whoami")
    r = requests.get(f"{BASE_URL}/api/v1/demo/whoami", headers={"Authorization": f"Bearer {api_key}"})
    print(f"status={r.status_code} body={json.dumps(r.json(), indent=2, ensure_ascii=False)}")
    assert r.status_code == 200

    divider("Step 4: 无凭证 / 错误凭证调用应该被拒绝")
    step("GET /api/v1/demo/hello (no auth)")
    r = requests.get(f"{BASE_URL}/api/v1/demo/hello")
    print(f"status={r.status_code} body={r.json()}")
    assert r.status_code == 401

    step("GET /api/v1/demo/hello (wrong key)")
    r = requests.get(f"{BASE_URL}/api/v1/demo/hello", headers={"X-API-Key": "ak_wrong"})
    print(f"status={r.status_code} body={r.json()}")
    assert r.status_code == 401

    divider("Step 5: 按应用、路径、时间范围查询审计日志")
    step("GET /api/v1/admin/audit?app_id=...")
    r = requests.get(f"{BASE_URL}/api/v1/admin/audit", headers=admin_headers, params={"app_id": app_id})
    print(f"status={r.status_code} body={json.dumps(r.json(), indent=2, ensure_ascii=False)}")
    assert r.status_code == 200
    logs = r.json()["items"]
    print(f"共 {r.json()['total']} 条日志，当前页 {len(logs)} 条")
    assert len(logs) >= 3

    step("GET /api/v1/admin/audit?path=/demo/echo")
    r = requests.get(f"{BASE_URL}/api/v1/admin/audit", headers=admin_headers, params={"path": "/demo/echo"})
    print(f"status={r.status_code} total={r.json()['total']}")

    if request_id_1:
        step(f"GET /api/v1/admin/audit/request/{request_id_1}  (查看完整请求/响应体)")
        r = requests.get(f"{BASE_URL}/api/v1/admin/audit/request/{request_id_1}", headers=admin_headers)
        print(f"status={r.status_code} body={json.dumps(r.json(), indent=2, ensure_ascii=False)}")

    divider("Step 6: 禁用凭证，验证立即失效")
    cred_id = cred["id"]
    step(f"POST /api/v1/admin/applications/{app_id}/credentials/{cred_id}/disable")
    r = requests.post(
        f"{BASE_URL}/api/v1/admin/applications/{app_id}/credentials/{cred_id}/disable",
        headers=admin_headers,
    )
    print(f"status={r.status_code} body={json.dumps(r.json(), indent=2, ensure_ascii=False)}")
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    step("GET /api/v1/demo/hello (same key, should be 403 now)")
    r = requests.get(f"{BASE_URL}/api/v1/demo/hello", headers=api_headers)
    print(f"status={r.status_code} body={r.json()}")
    assert r.status_code == 403

    divider("Step 7: 恢复凭证")
    step(f"POST /api/v1/admin/applications/{app_id}/credentials/{cred_id}/enable")
    r = requests.post(
        f"{BASE_URL}/api/v1/admin/applications/{app_id}/credentials/{cred_id}/enable",
        headers=admin_headers,
    )
    print(f"status={r.status_code} is_active={r.json()['is_active']}")
    assert r.status_code == 200

    step("GET /api/v1/demo/hello (should be 200 again)")
    r = requests.get(f"{BASE_URL}/api/v1/demo/hello", headers=api_headers)
    print(f"status={r.status_code}")
    assert r.status_code == 200

    divider("全部验证通过 ✅")


if __name__ == "__main__":
    main()
