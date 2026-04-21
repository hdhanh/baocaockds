# Hướng Dẫn Chạy Webapp Báo Cáo Công Trường

## Cấu trúc thư mục

```
baocao_app/
├── app.py              ← Flask chính (routes)
├── graph_api.py        ← Kết nối SharePoint
├── requirements.txt    ← Thư viện cần cài
└── templates/
    ├── login.html      ← Trang đăng nhập
    └── dashboard.html  ← Trang danh sách & báo cáo
```

---

## Bước 1 — Cài Python và thư viện

```bash
# Cài Python 3.11+ nếu chưa có: https://www.python.org/downloads/

# Mở CMD trong thư mục baocao_app, chạy:
pip install -r requirements.txt
```

---

## Bước 2 — Điền thông tin vào graph_api.py

Mở file `graph_api.py`, tìm phần CẤU HÌNH và điền vào:

```python
CLIENT_ID     = "xxxx-xxxx-xxxx"   # Từ Azure App Registration
CLIENT_SECRET = "xxxx~xxxx"         # Secret vừa tạo
TENANT_ID     = "xxxx-xxxx-xxxx"   # Tenant ID của tổ chức
SITE_ID       = "..."               # Xem Bước 3
```

---

## Bước 3 — Lấy SITE_ID của SharePoint

Mở `graph_api.py`, bỏ comment đoạn cuối file:

```python
if __name__ == "__main__":
    ten_site = "quanlycongtruong"   # Tên site SharePoint
    tenant   = "hoahiep"            # Tên tenant
    ...
```

Chỉnh lại tên site và tenant của bạn, rồi chạy:

```bash
python graph_api.py
```

Copy giá trị `id` in ra, dán vào `SITE_ID` ở trên.

---

## Bước 4 — Chạy ứng dụng

```bash
python app.py
```

Mở trình duyệt: `http://localhost:5000`

---

## Bước 5 — Cho người khác truy cập (Cloudflare Tunnel)

```bash
# Tải cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/
cloudflared tunnel --url http://localhost:5000
```

Cloudflare sẽ in ra một URL dạng `https://xxxxx.trycloudflare.com` — gửi link này cho công nhân.

---

## Lưu ý bảo mật

- Không commit file `graph_api.py` chứa secrets lên GitHub.
- Thay `app.secret_key` trong `app.py` bằng một chuỗi ngẫu nhiên dài.
- Mật khẩu nhân viên phải được lưu dạng **hash SHA-256** trong SharePoint, không phải plain text.
