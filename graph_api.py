"""
graph_api.py — tất cả gọi Microsoft Graph API + SharePoint REST API.
Tên list/cột đọc từ config.py.
"""

import re
import requests
import msal
from datetime import datetime, timezone
import config

BASE_URL = f"https://graph.microsoft.com/v1.0/sites/{config.SITE_ID}"

_cache: dict = {"token": None, "exp": 0}


def _get_token() -> str:
    now = datetime.now(timezone.utc).timestamp()
    if not _cache["token"] or now >= _cache["exp"] - 60:
        app = msal.ConfidentialClientApplication(
            config.CLIENT_ID, config.CLIENT_SECRET,
            authority=f"https://login.microsoftonline.com/{config.TENANT_ID}"
        )
        r = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" not in r:
            raise RuntimeError(f"Token error: {r.get('error_description')}")
        _cache["token"] = r["access_token"]
        _cache["exp"] = now + r.get("expires_in", 3600)
    return _cache["token"]


def _headers(ct="application/json"):
    return {"Authorization": f"Bearer {_get_token()}", "Content-Type": ct}

def _sp_headers(ct="application/json;odata=nometadata"):
    return {"Authorization": f"Bearer {_get_token()}",
            "Accept": "application/json;odata=nometadata",
            "Content-Type": ct}

def _sp_list_url(list_name):
    base = (config.SHAREPOINT_SITE_URL or "").rstrip("/")
    if not base or not base.startswith("http"):
        raise ValueError(
            "SHAREPOINT_SITE_URL chưa được cấu hình hoặc sai định dạng. "
            f"Giá trị hiện tại: '{config.SHAREPOINT_SITE_URL}'. "
            "Vui lòng set biến môi trường đúng dạng: https://tenant.sharepoint.com/sites/sitename"
        )
    return f"{base}/_api/web/lists/getByTitle('{list_name}')"

def _safe_int(v):
    try: return int(float(str(v)))
    except: return 0

def _fmt_sophieu(v) -> str:
    """SharePoint lưu number field → tránh '111.0', trả về '111'."""
    try:
        f = float(str(v))
        return str(int(f)) if f == int(f) else str(v)
    except:
        return str(v)

def _fmt_date(raw):
    return str(raw or "")[:10]

def _safe_filename(name):
    return re.sub(r"[^a-zA-Z0-9._-]", "_", name)


# ── Tổng quan hangmuc ────────────────────────────────────────────────

def lay_tong_quan() -> list:
    """Đọc thẳng các cột từ list hangmuc — Power Automate lo tính toán."""
    cfg = config.LIST_HANGMUC
    url = f"{BASE_URL}/lists/{cfg['list_name']}/items?$expand=fields&$top=999"
    try:
        items = requests.get(url, headers=_headers(), timeout=10).json().get("value", [])
    except Exception:
        return []
    result = []
    for item in items:
        f    = item.get("fields", {})
        mack = str(f.get(cfg["col_code"], "")).strip()
        if not mack:
            continue
        result.append({
            "mack":     mack,
            "mota":     str(f.get(cfg["col_desc"], "")).strip(),
            "soluong":  float(f.get("soluong",  0) or 0),
            "tongnhap": float(f.get("tongnhap", 0) or 0),
            "tongxuat": float(f.get("tongxuat", 0) or 0),
            "ton":      float(f.get("ton",      0) or 0),
            "canduc":   float(f.get("canduc",   0) or 0),
        })
    return sorted(result, key=lambda x: x["mack"])


# ── Debug: lấy tên cột thật từ SharePoint ────────────────────────────

def lay_ten_cot(list_name: str) -> list:
    """Trả về [{name, displayName, type}, ...] — dùng để debug internal names."""
    url = f"{BASE_URL}/lists/{list_name}/columns"
    try:
        items = requests.get(url, headers=_headers(), timeout=10).json().get("value", [])
    except Exception as e:
        return [{"error": str(e)}]
    result = []
    for col in items:
        result.append({
            "name":        col.get("name", ""),          # internal name (dùng trong API)
            "displayName": col.get("displayName", ""),   # tên hiển thị
            "type":        col.get("columnGroup", ""),
        })
    return sorted(result, key=lambda x: x["name"])


# ── Auth ─────────────────────────────────────────────────────────────

def authenticate(username, password):
    cfg = config.LIST_USERS
    url = f"{BASE_URL}/lists/{cfg['list_name']}/items?$expand=fields&$top=999"
    try:
        items = requests.get(url, headers=_headers(), timeout=10).json().get("value", [])
    except Exception as e:
        print(f"[AUTH ERROR] {e}"); return None
    for item in items:
        f = item.get("fields", {})
        u = str(f.get(cfg["col_user"], "")).strip()
        p = str(f.get(cfg["col_pass"]) or f.get(cfg["col_pass"]+"0") or "").strip()
        if u.lower() == username.lower() and p == password:
            return f
    return None


# ── Danh mục ─────────────────────────────────────────────────────────

def lay_hangmuc() -> list:
    """[{code, description}, ...] sắp xếp theo code."""
    cfg = config.LIST_HANGMUC
    url = f"{BASE_URL}/lists/{cfg['list_name']}/items?$expand=fields&$top=999"
    try:
        items = requests.get(url, headers=_headers(), timeout=10).json().get("value", [])
    except Exception: return []
    result = []
    for item in items:
        f = item.get("fields", {})
        code = str(f.get(cfg["col_code"], "")).strip()
        desc = str(f.get(cfg["col_desc"], "")).strip()
        if code:
            result.append({"code": code, "description": desc})
    return sorted(result, key=lambda x: x["code"])


def lay_todoi() -> list:
    """[{title}, ...] từ list tổ đội — dùng cho dropdown."""
    cfg = config.LIST_TODOI
    url = f"{BASE_URL}/lists/{cfg['list_name']}/items?$expand=fields&$top=999"
    try:
        items = requests.get(url, headers=_headers(), timeout=10).json().get("value", [])
    except Exception: return []
    result = []
    seen = set()
    for item in items:
        f = item.get("fields", {})
        title = str(f.get(cfg["col_title"], "")).strip()
        if title and title not in seen:
            seen.add(title)
            result.append({"title": title})
    return sorted(result, key=lambda x: x["title"])


# ── Số phiếu ─────────────────────────────────────────────────────────

def lay_so_phieu_moi(list_key: str) -> int:
    cfg = config.LISTS[list_key]
    col = cfg["columns"]["sophieu"]
    url = f"{BASE_URL}/lists/{cfg['list_name']}/items?$expand=fields&$top=999"
    try:
        items = requests.get(url, headers=_headers(), timeout=10).json().get("value", [])
    except Exception: return 1
    max_so = max((_safe_int(item["fields"].get(col, 0)) for item in items), default=0)
    return max_so + 1


# ── Danh sách phiếu ──────────────────────────────────────────────────

def lay_danh_sach_phieu(list_key: str) -> list:
    cfg  = config.LISTS[list_key]
    cols = cfg["columns"]
    url  = f"{BASE_URL}/lists/{cfg['list_name']}/items?$expand=fields&$top=999"
    try:
        items = requests.get(url, headers=_headers(), timeout=10).json().get("value", [])
    except Exception: return []

    groups = {}
    for item in items:
        f  = item.get("fields", {})
        sp = _fmt_sophieu(f.get(cols["sophieu"], "")).strip()
        if not sp: continue
        if sp not in groups:
            groups[sp] = {
                "sophieu": sp,
                "date":    _fmt_date(f.get(cols["date"], "")),
                "so_dong": 0,
                "todoi":   str(f.get(cols.get("todoi", ""), "")).strip()
                           if cfg["has_todoi"] else "",
            }
        groups[sp]["so_dong"] += 1

    result = list(groups.values())
    result.sort(key=lambda x: _safe_int(x["sophieu"]), reverse=True)
    return result


# ── Chi tiết phiếu ───────────────────────────────────────────────────

def lay_chi_tiet_phieu(list_key: str, sophieu: str) -> list:
    cfg  = config.LISTS[list_key]
    cols = cfg["columns"]
    url  = f"{BASE_URL}/lists/{cfg['list_name']}/items?$expand=fields&$top=999"
    try:
        items = requests.get(url, headers=_headers(), timeout=10).json().get("value", [])
    except Exception: return []

    rows = []
    for item in items:
        f  = item.get("fields", {})
        sp = _fmt_sophieu(f.get(cols["sophieu"], "")).strip()
        if sp != _fmt_sophieu(sophieu).strip(): continue
        row = {
            "item_id":     item["id"],
            "sophieu":     sp,
            "date":        _fmt_date(f.get(cols["date"], "")),
            "code":        str(f.get(cols["code"], "")).strip(),
            "description": "",
            "qty":         f.get(cols["qty"], 0),
            "note":        str(f.get(cols["note"], "")).strip(),
        }
        if cfg["has_todoi"]:
            row["todoi"] = str(f.get(cols.get("todoi", ""), "")).strip()
        rows.append(row)

    rows.sort(key=lambda x: _safe_int(x["item_id"]))
    if rows:
        rows[0]["is_first"] = True
    return rows


# ── CRUD ─────────────────────────────────────────────────────────────

def tao_dong(list_key: str, data: dict) -> str | None:
    cfg  = config.LISTS[list_key]
    cols = cfg["columns"]
    # Lưu sophieu là số nguyên để tránh SharePoint lưu dạng float "111.0"
    sp_val = data.get("sophieu", "")
    try: sp_val = int(float(str(sp_val)))
    except: pass
    fields = {
        cols["sophieu"]:     sp_val,
        cols["date"]:        data.get("date", ""),
        cols["code"]:        str(data.get("code", "")),
        cols["qty"]:         float(data.get("qty") or 0),
        cols["note"]:        str(data.get("note", "")),
    }
    if cfg["has_todoi"]:
        fields[cols["todoi"]]    = str(data.get("todoi", ""))

    url = f"{BASE_URL}/lists/{cfg['list_name']}/items"
    print(f"[TAO_DONG] Sending fields: {fields}")
    try:
        res = requests.post(url, headers=_headers(), json={"fields": fields}, timeout=15)
        if res.status_code == 201:
            return str(res.json()["id"])
        print(f"[TAO_DONG] HTTP {res.status_code}: {res.text[:200]}")
    except Exception as e:
        print(f"[TAO_DONG ERROR] {e}")
    return None


def cap_nhat_dong(list_key: str, item_id: str, data: dict) -> bool:
    cfg  = config.LISTS[list_key]
    cols = cfg["columns"]
    fields = {
        cols["date"]:        data.get("date", ""),
        cols["code"]:        str(data.get("code", "")),
        cols["qty"]:         float(data.get("qty") or 0),
        cols["note"]:        str(data.get("note", "")),
    }
    if cfg["has_todoi"]:
        fields[cols["todoi"]]    = str(data.get("todoi", ""))

    url = f"{BASE_URL}/lists/{cfg['list_name']}/items/{item_id}/fields"
    try:
        res = requests.patch(url, headers=_headers(), json=fields, timeout=15)
        return res.status_code == 200
    except Exception as e:
        print(f"[CAP_NHAT ERROR] {e}"); return False


def xoa_dong(list_key: str, item_id: str) -> bool:
    cfg = config.LISTS[list_key]
    url = f"{BASE_URL}/lists/{cfg['list_name']}/items/{item_id}"
    try:
        res = requests.delete(url, headers=_headers(), timeout=15)
        return res.status_code == 204
    except Exception as e:
        print(f"[XOA_DONG ERROR] {e}"); return False


# ── Attachment (SharePoint REST) ──────────────────────────────────────

def lay_attachment(list_key: str, item_id: str) -> dict | None:
    cfg = config.LISTS[list_key]
    url = f"{_sp_list_url(cfg['list_name'])}/items({item_id})/AttachmentFiles"
    try:
        items = requests.get(url, headers=_sp_headers(), timeout=10).json().get("value", [])
        if items:
            att = items[0]
            return {"name": att.get("FileName", ""), "server_url": att.get("ServerRelativeUrl", "")}
    except Exception as e:
        print(f"[LAY_ATT ERROR] {e}")
    return None


def upload_attachment(list_key, item_id, filename, data, content_type) -> bool:
    cfg  = config.LISTS[list_key]
    safe = _safe_filename(filename)
    url  = f"{_sp_list_url(cfg['list_name'])}/items({item_id})/AttachmentFiles/add(FileName='{safe}')"
    try:
        res = requests.post(url, headers=_sp_headers(content_type or "application/octet-stream"),
                            data=data, timeout=30)
        return res.status_code in (200, 201)
    except Exception as e:
        print(f"[UPLOAD_ATT ERROR] {e}"); return False


def xoa_attachment(list_key, item_id, filename) -> bool:
    cfg  = config.LISTS[list_key]
    safe = _safe_filename(filename)
    url  = f"{_sp_list_url(cfg['list_name'])}/items({item_id})/AttachmentFiles('{safe}')"
    try:
        res = requests.delete(url, headers=_sp_headers(), timeout=15)
        return res.status_code in (200, 204)
    except Exception as e:
        print(f"[XOA_ATT ERROR] {e}"); return False


def download_attachment(list_key, item_id, filename):
    cfg  = config.LISTS[list_key]
    safe = _safe_filename(filename)
    url  = f"{_sp_list_url(cfg['list_name'])}/items({item_id})/AttachmentFiles('{safe}')/$value"
    try:
        res = requests.get(url, headers={"Authorization": f"Bearer {_get_token()}"}, timeout=30)
        if res.ok:
            return res.content, res.headers.get("Content-Type", "application/octet-stream")
    except Exception as e:
        print(f"[DOWNLOAD_ATT ERROR] {e}")
    return None, None
