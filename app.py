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

    return render_template("login.html")


# -------------------------------------------------------
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


# -------------------------------------------------------
# GỬI BÁO CÁO
# -------------------------------------------------------
@app.route("/gui_bao_cao", methods=["POST"])
def gui_bao_cao():
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


# Health check cho Render
@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(debug=False)
