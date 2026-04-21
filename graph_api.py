"""
graph_api.py
Kết nối Microsoft Graph API — khớp với cấu trúc SharePoint thực tế.

Lists:
  users         : Title(mã NV), pass, full_name, position
  ckds_hangmuc  : Code(mã CV), description, Total_No(KL thiết kế)
  ckds_klgiao   : user, congviec(mã CV), kl_giao, ngaygiao
  ckds_baocao   : Title, User, ngaybc, congviec, khoiluong, img1-img9, note
"""

import os
import requests
import msal
from datetime import datetime, timezone

# -------------------------------------------------------
# CẤU HÌNH — đọc từ Environment Variables (Render Dashboard)
# -------------------------------------------------------
CLIENT_ID     = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
TENANT_ID     = os.environ.get("TENANT_ID")
SITE_ID       = os.environ.get("SITE_ID")

LIST_USERS    = "users"
LIST_HANGMUC  = "ckds_hangmuc"
LIST_KLGIAO   = "ckds_klgiao"
LIST_BAOCAO   = "ckds_baocao"

IMG_COLS      = [f"img{i}" for i in range(1, 10)]   # img1 → img9

BASE_URL = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}"


# -------------------------------------------------------
# TOKEN — tự làm mới khi hết hạn
# -------------------------------------------------------
_cache = {"token": None, "exp": 0}

def _headers() -> dict:
    now = datetime.now(timezone.utc).timestamp()
    if not _cache["token"] or now >= _cache["exp"] - 60:
        app = msal.ConfidentialClientApplication(
            CLIENT_ID, CLIENT_SECRET,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}"
        )
        r = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" not in r:
            raise RuntimeError(f"Lỗi token: {r.get('error_description')}")
        _cache["token"] = r["access_token"]
        _cache["exp"]   = now + r.get("expires_in", 3600)
    return {
        "Authorization": f"Bearer {_cache['token']}",
        "Content-Type":  "application/json"
    }


# -------------------------------------------------------
# XÁC THỰC ĐĂNG NHẬP
# Lấy toàn bộ list users về rồi so sánh trong Python
# (tránh lỗi OData vì "pass" là từ khóa đặc biệt)
# -------------------------------------------------------
def authenticate(username: str, password: str) -> dict | None:
    url = (
        f"{BASE_URL}/lists/{LIST_USERS}/items"
        f"?$expand=fields"
        f"&$top=999"
    )
    try:
        res   = requests.get(url, headers=_headers(), timeout=10)
        items = res.json().get("value", [])
    except Exception as e:
        print(f"[AUTH ERROR] Gọi API thất bại: {e}")
        return None

    print(f"[AUTH] Tìm thấy {len(items)} user trong list")

    for item in items:
        f = item.get("fields", {})
        print(f"[AUTH] Kiểm tra user: {f.get('Title')} | fields keys: {list(f.keys())}")

        title = str(f.get("Title", "")).strip()
        # Thử cả "pass" và "pass0" (SharePoint đôi khi thêm số vào tên cột)
        mat_khau = str(f.get("pass") or f.get("pass0") or "").strip()

        if title.lower() == username.lower() and mat_khau == password:
            print(f"[AUTH] Đăng nhập thành công: {title}")
            return f

    print(f"[AUTH] Không khớp username='{username}'")
    return None


# -------------------------------------------------------
# LẤY TOÀN BỘ HẠNG MỤC (ckds_hangmuc)
# Trả về dict {Code: {description, Total_No}}
# -------------------------------------------------------
def _lay_hangmuc_all() -> dict:
    url = (
        f"{BASE_URL}/lists/{LIST_HANGMUC}/items"
        f"?$select=fields/Code,fields/description,fields/Total_No"
        f"&$expand=fields&$top=999"
    )
    try:
        items = requests.get(url, headers=_headers(), timeout=10).json().get("value", [])
    except Exception:
        return {}
    return {
        item["fields"]["Code"]: item["fields"]
        for item in items
        if "Code" in item.get("fields", {})
    }


# -------------------------------------------------------
# LẤY CÔNG VIỆC ĐƯỢC GIAO CHO USER (ckds_klgiao)
# -------------------------------------------------------
def lay_cong_viec(username: str) -> list:
    """
    Trả về list các công việc được giao, mỗi item gồm:
    congviec, kl_giao, ngaygiao, description, Total_No
    """
    url = (
        f"{BASE_URL}/lists/{LIST_KLGIAO}/items"
        f"?$filter=fields/user eq '{username}'"
        f"&$select=fields/user,fields/congviec,fields/kl_giao,fields/ngaygiao"
        f"&$expand=fields&$top=999"
    )
    try:
        items = requests.get(url, headers=_headers(), timeout=10).json().get("value", [])
    except Exception:
        return []

    hang_muc = _lay_hangmuc_all()

    result = []
    for item in items:
        f  = item["fields"]
        cv = f.get("congviec", "")
        hm = hang_muc.get(cv, {})
        result.append({
            "congviec":    cv,
            "kl_giao":     float(f.get("kl_giao") or 0),
            "ngaygiao":    f.get("ngaygiao", ""),
            "description": hm.get("description", cv),
            "Total_No":    float(hm.get("Total_No") or 0),
        })
    return result


# -------------------------------------------------------
# TÍNH TỔNG KL ĐÃ BÁO CÁO (ckds_baocao)
# Trả về dict {congviec: tổng_khoiluong}
# -------------------------------------------------------
def tinh_da_baocao(username: str) -> dict:
    url = (
        f"{BASE_URL}/lists/{LIST_BAOCAO}/items"
        f"?$filter=fields/User eq '{username}'"
        f"&$select=fields/congviec,fields/khoiluong"
        f"&$expand=fields&$top=999"
    )
    try:
        items = requests.get(url, headers=_headers(), timeout=10).json().get("value", [])
    except Exception:
        return {}

    tong = {}
    for item in items:
        f  = item["fields"]
        cv = f.get("congviec", "")
        kl = float(f.get("khoiluong") or 0)
        tong[cv] = tong.get(cv, 0) + kl
    return tong


# -------------------------------------------------------
# UPLOAD ẢNH LÊN SHAREPOINT
# -------------------------------------------------------
def upload_anh(username: str, file_obj) -> str:
    """Upload 1 file ảnh, trả về URL. Rỗng nếu lỗi."""
    ngay     = datetime.now().strftime("%Y%m%d")
    ten_file = f"{username}_{ngay}_{file_obj.filename}"
    url      = (
        f"{BASE_URL}/drive/root:"
        f"/Hinh_Anh_Bao_Cao/{username}/{ngay}/{ten_file}:/content"
    )
    h = _headers()
    h["Content-Type"] = file_obj.content_type or "application/octet-stream"
    try:
        res = requests.put(url, headers=h, data=file_obj.read(), timeout=30,
                           params={"@microsoft.graph.conflictBehavior": "rename"})
        if res.status_code in (200, 201):
            return res.json().get("webUrl", "")
    except Exception:
        pass
    return ""


# -------------------------------------------------------
# GỬI BÁO CÁO (POST vào ckds_baocao)
# -------------------------------------------------------
def gui_bao_cao(username: str, congviec: str, khoiluong: float,
                note: str, img_urls: list) -> bool:
    """
    img_urls: list tối đa 9 URL ảnh (có thể ít hơn).
    Trả về True nếu thành công.
    """
    url  = f"{BASE_URL}/lists/{LIST_BAOCAO}/items"
    ngay = datetime.now().strftime("%Y%m%d_%H%M")

    fields = {
        "Title":      f"BC_{ngay}_{username}",
        "User":       username,
        "ngaybc":     datetime.utcnow().isoformat() + "Z",
        "congviec":   congviec,
        "khoiluong":  khoiluong,
        "note":       note,
    }

    # Gán từng URL vào img1, img2,... (chỉ gán nếu có ảnh)
    for i, url_anh in enumerate(img_urls[:9]):
        if url_anh:
            fields[f"img{i+1}"] = url_anh

    try:
        res = requests.post(url, headers=_headers(),
                            json={"fields": fields}, timeout=15)
        return res.status_code == 201
    except Exception:
        return False


# -------------------------------------------------------
# TIỆN ÍCH — lấy SITE_ID (chạy 1 lần khi setup)
# -------------------------------------------------------
def get_site_id(tenant: str, site_name: str) -> str:
    url = f"https://graph.microsoft.com/v1.0/sites/{tenant}.sharepoint.com:/sites/{site_name}"
    return requests.get(url, headers=_headers()).json().get("id", "Không tìm thấy")


if __name__ == "__main__":
    # Bỏ comment để lấy SITE_ID:
    # print(get_site_id("7s1scs", "ql46"))
    pass
