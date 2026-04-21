<<<<<<< HEAD
import os
from flask import (Flask, render_template, request,
                   redirect, url_for, session, flash)
import graph_api

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "doi-trong-render-env")


# -------------------------------------------------------
# ĐĂNG NHẬP
# -------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        nv       = graph_api.authenticate(username, password)

        if nv:
            session["username"]  = nv["Title"]
            session["full_name"] = nv.get("full_name", username)
            session["position"]  = nv.get("position", "")
            return redirect(url_for("dashboard"))
        else:
            flash("Sai tên đăng nhập hoặc mật khẩu.", "danger")
=======
from flask import Flask, render_template, request, redirect, url_for, session, flash
import graph_api
import os

app = Flask(__name__)
app.secret_key = "THAY_BANG_CHUOI_BÍ_MẬT_CUA_BAN"  # Đổi thành chuỗi ngẫu nhiên


# -------------------------------------------------------
# TRANG ĐĂNG NHẬP
# -------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ma_nv    = request.form.get("ma_nv", "").strip().upper()
        mat_khau = request.form.get("mat_khau", "").strip()

        nhan_vien = graph_api.authenticate(ma_nv, mat_khau)

        if nhan_vien:
            session["ma_nv"]  = nhan_vien["Title"]
            session["ho_ten"] = nhan_vien["Ho_Ten"]
            session["to_doi"] = nhan_vien["To_Doi"]
            return redirect(url_for("dashboard"))
        else:
            flash("Sai Mã NV hoặc Mật khẩu. Vui lòng thử lại.", "danger")
>>>>>>> d284c49f2a5268e703abd17147c48602678053ac

    return render_template("login.html")


# -------------------------------------------------------
<<<<<<< HEAD
# DASHBOARD — danh sách công việc + tiến độ
# -------------------------------------------------------
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    username  = session["username"]
    cong_viec = graph_api.lay_cong_viec(username)   # [{congviec, kl_giao, description, Total_No,...}]
    da_baocao = graph_api.tinh_da_baocao(username)  # {congviec: tong_kl_da_bc}

    # Gắn thêm thông tin tiến độ vào từng CV
    for cv in cong_viec:
        ma         = cv["congviec"]
        tong_giao  = cv["kl_giao"]
        tong_da_bc = da_baocao.get(ma, 0)
        cv["da_baocao"]  = tong_da_bc
        cv["con_lai"]    = max(tong_giao - tong_da_bc, 0)
        cv["phan_tram"]  = min(round(tong_da_bc / tong_giao * 100, 1)
                               if tong_giao > 0 else 0, 100)

    return render_template("dashboard.html",
                           full_name=session["full_name"],
                           position=session["position"],
                           cong_viec=cong_viec)
=======
# TRANG DASHBOARD (DANH SÁCH CÔNG VIỆC)
# -------------------------------------------------------
@app.route("/dashboard")
def dashboard():
    if "ma_nv" not in session:
        return redirect(url_for("login"))

    ma_nv        = session["ma_nv"]
    cong_viec    = graph_api.lay_cong_viec(ma_nv)        # Danh sách CV được giao
    tien_do      = graph_api.tinh_tien_do(ma_nv)          # Dict {Ma_CV: khối lượng đã báo}

    return render_template("dashboard.html",
                           ho_ten=session["ho_ten"],
                           to_doi=session["to_doi"],
                           cong_viec=cong_viec,
                           tien_do=tien_do)
>>>>>>> d284c49f2a5268e703abd17147c48602678053ac


# -------------------------------------------------------
# GỬI BÁO CÁO
# -------------------------------------------------------
@app.route("/gui_bao_cao", methods=["POST"])
def gui_bao_cao():
<<<<<<< HEAD
    if "username" not in session:
        return redirect(url_for("login"))

    username  = session["username"]
    congviec  = request.form.get("congviec", "")
    khoiluong = float(request.form.get("khoiluong") or 0)
    note      = request.form.get("note", "")

    # Upload tối đa 9 ảnh
    img_urls = []
    for i in range(1, 10):
        f = request.files.get(f"img{i}")
        if f and f.filename:
            url = graph_api.upload_anh(username, f)
            img_urls.append(url)
        else:
            img_urls.append("")

    ok = graph_api.gui_bao_cao(
        username=username,
        congviec=congviec,
        khoiluong=khoiluong,
        note=note,
        img_urls=img_urls
    )

    if ok:
        flash(f"✅ Đã gửi báo cáo cho công việc {congviec}!", "success")
=======
    if "ma_nv" not in session:
        return redirect(url_for("login"))

    ma_nv      = session["ma_nv"]
    ma_cv      = request.form.get("ma_cv")
    khoi_luong = float(request.form.get("khoi_luong", 0))
    ghi_chu    = request.form.get("ghi_chu", "")
    file_anh   = request.files.get("hinh_anh")

    # Upload ảnh lên SharePoint (nếu có)
    hinh_anh_url = ""
    if file_anh and file_anh.filename:
        hinh_anh_url = graph_api.upload_anh(ma_nv, file_anh)

    # Ghi bản ghi vào Nhat_Ky_Bao_Cao
    thanh_cong = graph_api.gui_bao_cao(
        ma_nv=ma_nv,
        ma_cv=ma_cv,
        khoi_luong=khoi_luong,
        ghi_chu=ghi_chu,
        hinh_anh_url=hinh_anh_url
    )

    if thanh_cong:
        flash(f"✅ Báo cáo công việc {ma_cv} gửi thành công!", "success")
>>>>>>> d284c49f2a5268e703abd17147c48602678053ac
    else:
        flash("❌ Gửi thất bại. Vui lòng thử lại.", "danger")

    return redirect(url_for("dashboard"))


# -------------------------------------------------------
# ĐĂNG XUẤT
# -------------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


<<<<<<< HEAD
# Health check cho Render
@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(debug=False)
=======
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
>>>>>>> d284c49f2a5268e703abd17147c48602678053ac
