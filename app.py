import os
from flask import (Flask, render_template, request,
                   redirect, url_for, session, flash, jsonify)
from datetime import date
import graph_api

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "doi-trong-render-env")


@app.route("/", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        nv = graph_api.authenticate(username, password)
        if nv:
            session["username"]  = nv["Title"]
            session["full_name"] = nv.get("full_name", username)
            session["position"]  = nv.get("position", "")
            return redirect(url_for("dashboard"))
        flash("Sai tên đăng nhập hoặc mật khẩu.", "danger")
    return render_template("login.html")


# -------------------------------------------------------
# DASHBOARD — tổng quan tiến độ
# -------------------------------------------------------
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    username  = session["username"]
    cong_viec = graph_api.lay_cong_viec(username)
    da_baocao = graph_api.tinh_da_baocao(username)
    for cv in cong_viec:
        ma              = cv["congviec"]
        tg              = cv["kl_giao"]
        da              = da_baocao.get(ma, 0)
        cv["da_baocao"] = round(da, 2)
        cv["con_lai"]   = round(max(tg - da, 0), 2)
        cv["phan_tram"] = min(round(da / tg * 100, 1) if tg > 0 else 0, 100)
    return render_template("dashboard.html",
                           full_name=session["full_name"],
                           position=session["position"],
                           cong_viec=cong_viec)


# -------------------------------------------------------
# TRANG BÁO CÁO
# -------------------------------------------------------
@app.route("/baocao")
def baocao():
    if "username" not in session:
        return redirect(url_for("login"))
    username  = session["username"]
    cong_viec = graph_api.lay_cong_viec(username)
    da_baocao = graph_api.tinh_da_baocao(username)
    for cv in cong_viec:
        tg = cv["kl_giao"]
        da = da_baocao.get(cv["congviec"], 0)
        cv["phan_tram"] = min(round(da / tg * 100, 1) if tg > 0 else 0, 100)
    # Chỉ hiện CV chưa hoàn thành
    active = [cv for cv in cong_viec if cv["phan_tram"] < 100]
    today  = date.today().strftime("%Y-%m-%d")
    return render_template("baocao.html",
                           full_name=session["full_name"],
                           position=session["position"],
                           cong_viec=active,
                           today=today)


# -------------------------------------------------------
# AJAX: kiểm tra ngày đã có báo cáo chưa
# -------------------------------------------------------
@app.route("/api/check_ngay")
def api_check_ngay():
    if "username" not in session:
        return jsonify({}), 401
    ngay   = request.args.get("ngay", "")
    result = graph_api.kiem_tra_bao_cao_ngay(session["username"], ngay)
    return jsonify(result)   # {congviec: item_id}


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
    ngay      = request.form.get("ngay", date.today().strftime("%Y-%m-%d"))
    note      = request.form.get("note", "")
    item_id   = request.form.get("item_id") or None

    img_urls = []
    for i in range(1, 10):
        f = request.files.get(f"img{i}")
        img_urls.append(graph_api.upload_anh(username, f) if f and f.filename else "")

    ok = graph_api.gui_bao_cao(
        username=username, congviec=congviec,
        khoiluong=khoiluong, ngay=ngay,
        note=note, img_urls=img_urls, item_id=item_id
    )
    action = "Cập nhật" if item_id else "Gửi mới"
    if ok:
        flash(f"✅ {action} thành công — {congviec} ngày {ngay}: {khoiluong}", "success")
    else:
        flash("❌ Gửi thất bại. Vui lòng thử lại.", "danger")
    return redirect(url_for("baocao"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(debug=False)
