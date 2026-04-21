"""
graph_api.py
<<<<<<< HEAD
Kết nối Microsoft Graph API — khớp với cấu trúc SharePoint thực tế.

Lists:
  users         : Title(mã NV), pass, full_name, position
  ckds_hangmuc  : Code(mã CV), description, Total_No(KL thiết kế)
  ckds_klgiao   : user, congviec(mã CV), kl_giao, ngaygiao
  ckds_baocao   : Title, User, ngaybc, congviec, khoiluong, img1-img9, note
"""

import os
=======
Tầng giao tiếp với Microsoft Graph API (SharePoint + OneDrive)
"""

import hashlib
>>>>>>> d284c49f2a5268e703abd17147c48602678053ac
import requests
import msal
from datetime import datetime, timezone

# -------------------------------------------------------
<<<<<<< HEAD
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
=======
# CẤU HÌNH — Điền thông tin từ Azure App Registration
# -------------------------------------------------------
CLIENT_ID     = "PASTE_CLIENT_ID_CUA_BAN"
CLIENT_SECRET = "PASTE_CLIENT_SECRET_CUA_BAN"
TENANT_ID     = "PASTE_TENANT_ID_CUA_BAN"
SITE_ID       = "PASTE_SHAREPOINT_SITE_ID"   # Xem hướng dẫn lấy bên dưới

# Tên các SharePoint Lists (phải khớp với tên bạn đã tạo)
LIST_NHAN_VIEN  = "Danh_Muc_Nhan_Vien"
LIST_CONG_VIEC  = "Danh_Muc_Cong_Viec"
LIST_NHAT_KY    = "Nhat_Ky_Bao_Cao"

BASE_URL = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}"

# -------------------------------------------------------
# LẤY TOKEN (tự động làm mới khi hết hạn)
# -------------------------------------------------------
_token_cache = {"token": None, "expires_at": 0}

def _get_headers() -> dict:
    now = datetime.now(timezone.utc).timestamp()
    if not _token_cache["token"] or now >= _token_cache["expires_at"] - 60:
>>>>>>> d284c49f2a5268e703abd17147c48602678053ac
        app = msal.ConfidentialClientApplication(
            CLIENT_ID, CLIENT_SECRET,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}"
        )
<<<<<<< HEAD
        r = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" not in r:
            raise RuntimeError(f"Lỗi token: {r.get('error_description')}")
        _cache["token"] = r["access_token"]
        _cache["exp"]   = now + r.get("expires_in", 3600)
    return {
        "Authorization": f"Bearer {_cache['token']}",
=======
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        _token_cache["token"]      = result["access_token"]
        _token_cache["expires_at"] = now + result.get("expires_in", 3600)

    return {
        "Authorization": f"Bearer {_token_cache['token']}",
>>>>>>> d284c49f2a5268e703abd17147c48602678053ac
        "Content-Type":  "application/json"
    }


# -------------------------------------------------------
<<<<<<< HEAD
# XÁC THỰC ĐĂNG NHẬP
# plain text — so khớp trực tiếp với cột pass
# -------------------------------------------------------
def authenticate(username: str, password: str) -> dict | None:
    url = (
        f"{BASE_URL}/lists/{LIST_USERS}/items"
        f"?$filter=fields/Title eq '{username}'"
        f"&$select=fields/Title,fields/pass,fields/full_name,fields/position"
        f"&$expand=fields"
    )
    try:
        items = requests.get(url, headers=_headers(), timeout=10).json().get("value", [])
    except Exception:
        return None
=======
# HÀM TIỆN ÍCH
# -------------------------------------------------------
def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# -------------------------------------------------------
# XÁC THỰC ĐĂNG NHẬP
# -------------------------------------------------------
def authenticate(ma_nv: str, mat_khau: str) -> dict | None:
    """
    Trả về dict thông tin nhân viên nếu đúng, None nếu sai.
    """
    url = (
        f"{BASE_URL}/lists/{LIST_NHAN_VIEN}/items"
        f"?$filter=fields/Title eq '{ma_nv}'"
        f"&$select=fields/Title,fields/Mat_Khau_Hash,fields/Ho_Ten,fields/To_Doi"
        f"&$expand=fields"
    )
    res   = requests.get(url, headers=_get_headers())
    items = res.json().get("value", [])
>>>>>>> d284c49f2a5268e703abd17147c48602678053ac

    if not items:
        return None

<<<<<<< HEAD
    f = items[0]["fields"]
    if str(f.get("pass", "")) == password:
        return f          # Trả về dict: Title, full_name, position
=======
    fields = items[0]["fields"]
    if fields.get("Mat_Khau_Hash") == _hash(mat_khau):
        return fields
>>>>>>> d284c49f2a5268e703abd17147c48602678053ac
    return None


# -------------------------------------------------------
<<<<<<< HEAD
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
=======
# LẤY DANH SÁCH CÔNG VIỆC ĐƯỢC GIAO
# -------------------------------------------------------
def lay_cong_viec(ma_nv: str) -> list[dict]:
    """
    Trả về danh sách công việc được giao cho nhân viên.
    """
    url = (
        f"{BASE_URL}/lists/{LIST_CONG_VIEC}/items"
        f"?$filter=fields/Nguoi_Duoc_Giao eq '{ma_nv}'"
        f"&$select=fields/Title,fields/Ten_Hang_Muc,fields/Khoi_Luong_Thiet_Ke,fields/Don_Vi"
        f"&$expand=fields"
    )
    res = requests.get(url, headers=_get_headers())
    return [item["fields"] for item in res.json().get("value", [])]


# -------------------------------------------------------
# TÍNH TIẾN ĐỘ (KHỐI LƯỢNG ĐÃ BÁO CÁO)
# -------------------------------------------------------
def tinh_tien_do(ma_nv: str) -> dict[str, float]:
    """
    Trả về dict {Ma_CV: tổng_khối_lượng_đã_báo_cáo}.
    """
    url = (
        f"{BASE_URL}/lists/{LIST_NHAT_KY}/items"
        f"?$filter=fields/Ma_NV eq '{ma_nv}'"
        f"&$select=fields/Ma_CV,fields/Khoi_Luong_Thuc_Hien"
        f"&$expand=fields"
        f"&$top=500"
    )
    res   = requests.get(url, headers=_get_headers())
    items = res.json().get("value", [])

    tong = {}
    for item in items:
        f = item["fields"]
        ma = f.get("Ma_CV", "")
        kl = float(f.get("Khoi_Luong_Thuc_Hien", 0) or 0)
        tong[ma] = tong.get(ma, 0) + kl
>>>>>>> d284c49f2a5268e703abd17147c48602678053ac
    return tong


# -------------------------------------------------------
# UPLOAD ẢNH LÊN SHAREPOINT
# -------------------------------------------------------
<<<<<<< HEAD
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
=======
def upload_anh(ma_nv: str, file_obj) -> str:
    """
    Upload file ảnh, trả về URL public của ảnh.
    """
    ngay      = datetime.now().strftime("%Y%m%d")
    ten_file  = f"{ma_nv}_{ngay}_{file_obj.filename}"
    drive_url = (
        f"{BASE_URL}/drive/root:/Hinh_Anh_Cong_Truong"
        f"/{ma_nv}/{ngay}/{ten_file}:/content"
    )

    headers = _get_headers()
    headers["Content-Type"] = file_obj.content_type or "application/octet-stream"
    del headers["Content-Type"]   # Graph tự nhận diện từ nội dung

    res  = requests.put(drive_url, headers=_get_headers(),
                        data=file_obj.read(),
                        params={"@microsoft.graph.conflictBehavior": "rename"})

    if res.status_code in (200, 201):
        return res.json().get("webUrl", "")
>>>>>>> d284c49f2a5268e703abd17147c48602678053ac
    return ""


# -------------------------------------------------------
<<<<<<< HEAD
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
=======
# GỬI BÁO CÁO VÀO SHAREPOINT LIST
# -------------------------------------------------------
def gui_bao_cao(ma_nv: str, ma_cv: str, khoi_luong: float,
                ghi_chu: str, hinh_anh_url: str) -> bool:
    """
    Tạo bản ghi mới trong Nhat_Ky_Bao_Cao.
    Trả về True nếu thành công.
    """
    url    = f"{BASE_URL}/lists/{LIST_NHAT_KY}/items"
    ngay   = datetime.now().strftime("%Y%m%d_%H%M")
    body   = {
        "fields": {
            "Title":                  f"BC_{ngay}_{ma_nv}",
            "Ma_NV":                  ma_nv,
            "Ma_CV":                  ma_cv,
            "Khoi_Luong_Thuc_Hien":   khoi_luong,
            "Ghi_Chu":                ghi_chu,
            "Hinh_Anh_URL":           hinh_anh_url,
            "Ngay_Bao_Cao":           datetime.utcnow().isoformat() + "Z",
        }
    }
    res = requests.post(url, headers=_get_headers(), json=body)
    return res.status_code == 201


# -------------------------------------------------------
# CÁCH LẤY SITE_ID (chạy 1 lần để biết)
# -------------------------------------------------------
# Bỏ comment đoạn dưới, chạy file này một lần, copy giá trị id
# if __name__ == "__main__":
#     ten_site = "quanlycongtruong"     # Tên site SharePoint của bạn
#     tenant   = "hoahiep"              # Tên tenant (phần trước .sharepoint.com)
#     url = f"https://graph.microsoft.com/v1.0/sites/{tenant}.sharepoint.com:/sites/{ten_site}"
#     res = requests.get(url, headers=_get_headers())
#     print("SITE_ID =", res.json().get("id"))
>>>>>>> d284c49f2a5268e703abd17147c48602678053ac
