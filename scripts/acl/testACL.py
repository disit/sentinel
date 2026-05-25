#!/usr/bin/env python3

"""
ACL Integration Tester
Tests the full ACL lifecycle in a fresh Docker Compose environment.

Usage:
  python testACL.py [rootuser rootpass areamanageruser areamanagerpass]
  (falls back to data/testACLconf.json if args are omitted)

Test plan:
  1. RootAdmin creates an AccessDefinition for all orgs, dashboard_id=777
  2. AreaManager checks access to dashboard 777 → expects NO
  3. RootAdmin assigns the ACL to AreaManager
  4. AreaManager checks access to dashboard 777 → expects YES
  5. RootAdmin deletes the AccessDefinition
  6. AreaManager checks access to dashboard 777 → expects NO
"""

import json
import sys
import time
import requests

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG_PATH = "testACLconf.json"
TEST_DASHBOARD_ID = f"{int(time.time())}"
TEST_AUTH_NAME = f"test_acl_dashboard_{TEST_DASHBOARD_ID}_T{int(time.time())}"

config = {}
try:
    with open(CONFIG_PATH) as f:
        config = json.load(f)
except Exception as e:
    print(f"[WARN] Could not load {CONFIG_PATH}: {e}")

rootusername        = ""
rootpassword        = ""
areamanagerusername = ""
areamanagerpassword = ""

try:
    rootusername        = sys.argv[1]
    rootpassword        = sys.argv[2]
    areamanagerusername = sys.argv[3]
    areamanagerpassword = sys.argv[4]
except (IndexError, Exception) as e:
    print(f"[INFO] Using config file credentials ({e})")
    rootusername        = config.get("rootusername", "")
    rootpassword        = config.get("rootpassword", "")
    areamanagerusername = config.get("areamanagerusername", "")
    areamanagerpassword = config.get("areamanagerpassword", "")

BASE_URL    = config.get("base-url", "http://localhost")
TOKEN_URL   = f"{BASE_URL}/auth/realms/master/protocol/openid-connect/token"
CLIENT_ID   = config.get("client_id", "js-kpi-client")
EDIT_ACL    = f"{BASE_URL}/dashboardSmartCity/management/editACL.php"
ACLAPI      = f"{BASE_URL}/dashboardSmartCity/api/ACLAPI.php"

# ── Helpers ───────────────────────────────────────────────────────────────────

PASS = "\033[92m✔ PASS\033[0m"
FAIL = "\033[91m✘ FAIL\033[0m"

def result(label: str, ok: bool, detail: str = ""):
    status = PASS if ok else FAIL
    msg = f"  {status}  {label}"
    if detail:
        msg += f"\n         {detail}"
    print(msg)
    return ok


def abort(reason: str):
    print(f"\n\033[91m[ABORT]\033[0m {reason}\n")
    sys.exit(1)


def get_token(username: str, password: str) -> str:
    """Fetch a Bearer token via Resource Owner Password Credentials grant."""
    payload = {
        "client_id":  CLIENT_ID,
        "grant_type": "password",
        "username":   username,
        "password":   password,
        "scope":      "openid",
    }
    try:
        r = requests.post(TOKEN_URL, data=payload,
                          headers={"Content-Type": "application/x-www-form-urlencoded"},
                          timeout=15)
        r.raise_for_status()
        token = r.json().get("access_token")
        if not token:
            abort(f"No access_token in response for '{username}': {r.text[:300]}")
        return token
    except requests.RequestException as e:
        abort(f"Token request failed for '{username}': {e}")


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def post(url: str, token: str, data: dict) -> dict:
    try:
        r = requests.post(url, data=data, headers=auth_header(token), timeout=15)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ── Test steps ────────────────────────────────────────────────────────────────

def step_get_tokens():
    print("\n[Setup] Fetching tokens …")
    rt = get_token(rootusername, rootpassword)
    print(f"  Root token obtained for '{rootusername}'")
    at = get_token(areamanagerusername, areamanagerpassword)
    print(f"  AreaManager token obtained for '{areamanagerusername}'")
    return rt, at


def test1_create_acl(root_token: str) -> int:
    """RootAdmin creates an AccessDefinition for all orgs, dashboard {TEST_DASHBOARD_ID}."""
    print(f"\n[Test 1] RootAdmin creates AccessDefinition for dashboard {TEST_DASHBOARD_ID} …")

    res = post(EDIT_ACL, root_token, {
        "action":       "add_AD",
        "name":         TEST_AUTH_NAME,
        "orgs[]":       "*",          # all orgs
        "dashboard_id": TEST_DASHBOARD_ID,
    })

    ok  = res.get("result") == "added" and "id" in res
    ad_id = res.get("id")
    detail = f"response: {res}"
    if not result("AccessDefinition created", ok, detail):
        abort("Cannot continue without a valid AccessDefinition.")
    print(f"  → AccessDefinition ID = {ad_id}")
    return ad_id


def test2_user_no_access(area_token: str):
    """AreaManager should NOT have access to dashboard {TEST_DASHBOARD_ID} yet."""
    print(f"\n[Test 2] AreaManager checks dashboard {TEST_DASHBOARD_ID} (expects: NO access) …")

    res = post(ACLAPI, area_token, {
        "action":       "check_dashboard",
        "dashboard_id": TEST_DASHBOARD_ID,
    })

    # authorized == false  OR  authorized field absent/false-y
    authorized = str(res.get("authorized", "false")).lower()
    no_access  = authorized != "true"
    result("AreaManager has NO access (correct)", no_access, f"response: {res}")
    return no_access


def test3_grant_and_verify(root_token: str, area_token: str, ad_id: int):
    """RootAdmin grants the ACL to AreaManager; AreaManager should then have access."""
    print(f"\n[Test 3] RootAdmin grants ACL → AreaManager checks dashboard {TEST_DASHBOARD_ID} …")

    # fetch current defs for the user (should be empty)
    current = post(EDIT_ACL, root_token, {
        "action":   "get_user_ACL",
        "username": areamanagerusername,
    })
    original_defs = [row["defID"] for row in current] if isinstance(current, list) else []

    # grant
    grant_res = post(EDIT_ACL, root_token, {
        "action":           "update_ACL",
        "username":         areamanagerusername,
        "original_defs[]":  original_defs,
        "new_defs[]":       original_defs + [ad_id],
    })

    granted = ad_id in grant_res.get("added", [])
    result("ACL granted to AreaManager", granted, f"response: {grant_res}")

    if not granted:
        abort("Grant step failed; skipping access check.")

    # verify access
    check = post(ACLAPI, area_token, {
        "action":       "check_dashboard",
        "dashboard_id": TEST_DASHBOARD_ID,
    })
    authorized = str(check.get("authorized", "false")).lower() == "true"
    result("AreaManager NOW has access (correct)", authorized, f"response: {check}")
    return authorized


def test4_delete_and_verify(root_token: str, area_token: str, ad_id: int):
    """RootAdmin deletes the AccessDefinition; AreaManager should lose access."""
    print("\n[Test 4] RootAdmin deletes AccessDefinition → AreaManager checks …")

    del_res = post(EDIT_ACL, root_token, {
        "action": "delete_AD",
        "id":     ad_id,
    })
    deleted = del_res.get("result") == "deleted"
    result("AccessDefinition deleted", deleted, f"response: {del_res}")

    if not deleted:
        abort("Delete step failed; skipping final access check.")

    check = post(ACLAPI, area_token, {
        "action":       "check_dashboard",
        "dashboard_id": TEST_DASHBOARD_ID,
    })
    authorized = str(check.get("authorized", "false")).lower()
    no_access  = authorized != "true"
    result("AreaManager has NO access again (correct)", no_access, f"response: {check}")
    return no_access


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  ACL Integration Test Suite")
    print(f"  Base URL : {BASE_URL}")
    print(f"  Root     : {rootusername}")
    print(f"  Manager  : {areamanagerusername}")
    print("=" * 60)

    root_token, area_token = step_get_tokens()

    ad_id   = test1_create_acl(root_token)
    t2      = test2_user_no_access(area_token)
    t3      = test3_grant_and_verify(root_token, area_token, ad_id)
    t4      = test4_delete_and_verify(root_token, area_token, ad_id)

    print("\n" + "=" * 60)
    all_passed = all([ad_id, t2, t3, t4])
    if all_passed:
        print("\033[92m  ALL TESTS PASSED ✔\033[0m")
    else:
        print("\033[91m  SOME TESTS FAILED ✘\033[0m")
        sys.exit(1)
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()