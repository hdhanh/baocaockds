# ════════════════════════════════════════════════════════════════════
#  CONFIG.PY — Cấu hình SharePoint Lists
#  ✅ Chỉ cần chỉnh file này, KHÔNG cần sửa app.py hay graph_api.py
# ════════════════════════════════════════════════════════════════════

import os

CLIENT_ID           = os.environ.get("CLIENT_ID")
CLIENT_SECRET       = os.environ.get("CLIENT_SECRET")
TENANT_ID           = os.environ.get("TENANT_ID")
SITE_ID             = os.environ.get("SITE_ID")
SHAREPOINT_SITE_URL = os.environ.get("SHAREPOINT_SITE_URL", "")
SECRET_KEY          = os.environ.get("SECRET_KEY", "doi-trong-render-env")

LISTS = {
    "xuat": {
        "list_name":    "xuat",
        "display_name": "Phiếu Xuất",
        "has_image":    True,
        "has_todoi":    False,
        "color":        "#10522d",
        "color_light":  "#e8f5ee",
        "columns": {
            "sophieu":     "sophieu",
            "date":        "date",
            "code":        "code",
            "description": "description",
            "qty":         "qty",
            "note":        "note",
        }
    },
    "nhap": {
        "list_name":    "nhap",
        "display_name": "Phiếu Nhập",
        "has_image":    False,
        "has_todoi":    True,
        "color":        "#1a2744",
        "color_light":  "#eaecf5",
        "columns": {
            "sophieu":     "stt",
            "date":        "date",
            "todoi":       "todoi",
            "fullname":    "fullname",
            "code":        "code",
            "description": "description",
            "qty":         "qty",
            "note":        "note",
        }
    }
}

LIST_HANGMUC = {
    "list_name": "hangmuc",
    "col_code":  "code",
    "col_desc":  "description",
}

LIST_TODOI = {
    "list_name":    "todoi",
    "col_title":    "Title",
    "col_fullname": "fullname",
}

LIST_USERS = {
    "list_name": "users",
    "col_user":  "Title",
    "col_pass":  "pass",
    "col_name":  "full_name",
    "col_pos":   "position",
}
