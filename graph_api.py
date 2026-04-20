"""
graph_api.py
Tầng giao tiếp với Microsoft Graph API (SharePoint + OneDrive)
"""

import hashlib
import requests
import msal
from datetime import datetime, timezone

# -------------------------------------------------------
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
        app = msal.ConfidentialClientApplication(
            CLIENT_ID, CLIENT_SECRET,
            authority=f"https://login.microsoftonline.com/{TENANT_ID}"
        )
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        _token_cache["token"]      = result["access_token"]
        _token_cache["expires_at"] = now + result.get("expires_in", 3600)

    return {
        "Authorization": f"Bearer {_token_cache['token']}",
        "Content-Type":  "application/json"
    }


# -------------------------------------------------------
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

    if not items:
        return None

    fields = items[0]["fields"]
    if fields.get("Mat_Khau_Hash") == _hash(mat_khau):
        return fields
    return None


# -------------------------------------------------------
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
    return tong


# -------------------------------------------------------
# UPLOAD ẢNH LÊN SHAREPOINT
# -------------------------------------------------------
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
    return ""


# -------------------------------------------------------
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
