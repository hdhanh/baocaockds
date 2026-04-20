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

    return render_template("login.html")


# -------------------------------------------------------
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


# -------------------------------------------------------
# GỬI BÁO CÁO
# -------------------------------------------------------
@app.route("/gui_bao_cao", methods=["POST"])
def gui_bao_cao():
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
