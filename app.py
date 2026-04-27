import json
from functools import wraps
from datetime import date
from flask import (Flask, render_template, request,
                   redirect, url_for, session, flash,
                   jsonify, Response, abort)
import graph_api, config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

def login_required(f):
    @wraps(f)
    def d(*a, **kw):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*a, **kw)
    return d

# ── Auth ──────────────────────────────────────────────────────────────
@app.route("/", methods=["GET","POST"])
def login():
    if "username" in session: return redirect(url_for("hub"))
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","").strip()
        nv = graph_api.authenticate(u, p)
        if nv:
            cu = config.LIST_USERS
            session["username"]  = nv.get(cu["col_user"], u)
            session["full_name"] = nv.get(cu["col_name"], u)
            session["position"]  = nv.get(cu["col_pos"], "")
            return redirect(url_for("hub"))
        flash("Sai tên đăng nhập hoặc mật khẩu.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("login"))

# ── Hub ───────────────────────────────────────────────────────────────
@app.route("/hub")
@login_required
def hub():
    return render_template("hub.html",
        full_name=session["full_name"], position=session["position"])

# ── AJAX ──────────────────────────────────────────────────────────────
@app.route("/api/caukien")
@login_required
def api_caukien():
    return jsonify(graph_api.lay_hangmuc())

@app.route("/api/todoi")
@login_required
def api_todoi():
    return jsonify(graph_api.lay_todoi())

# ════════════════════════════════════════════════════════════════════
#  PHIẾU XUẤT
# ════════════════════════════════════════════════════════════════════

@app.route("/xuat")
@login_required
def danhsach_xuat():
    return render_template("xuat/danhsach.html",
        phieu=graph_api.lay_danh_sach_phieu("xuat"),
        cfg=config.LISTS["xuat"])

@app.route("/xuat/moi", methods=["GET","POST"])
@login_required
def tao_xuat():
    if request.method == "GET":
        return render_template("xuat/form.html", mode="create",
            sophieu=graph_api.lay_so_phieu_moi("xuat"),
            today=date.today().isoformat(),
            rows=[], attachment=None, cfg=config.LISTS["xuat"])

    sophieu   = request.form.get("sophieu","").strip()
    ngay      = request.form.get("date","")
    note      = request.form.get("note","")
    rows      = _parse_rows()
    if not rows:
        flash("Vui lòng thêm ít nhất 1 dòng cấu kiện!", "warning")
        return redirect(url_for("tao_xuat"))

    first_id = None
    for i, row in enumerate(rows):
        iid = graph_api.tao_dong("xuat", {**row, "sophieu": sophieu, "date": ngay, "note": note})
        if i == 0: first_id = iid

    img = request.files.get("image")
    if img and img.filename and first_id:
        graph_api.upload_attachment("xuat", first_id, img.filename, img.read(), img.content_type)

    flash(f"✅ Đã lưu Phiếu Xuất số {sophieu}!", "success")
    return redirect(url_for("danhsach_xuat"))

@app.route("/xuat/<sophieu>")
@login_required
def chitiet_xuat(sophieu):
    rows = graph_api.lay_chi_tiet_phieu("xuat", sophieu)
    if not rows:
        flash("Không tìm thấy phiếu.", "warning")
        return redirect(url_for("danhsach_xuat"))
    att = graph_api.lay_attachment("xuat", rows[0]["item_id"])
    return render_template("xuat/chitiet.html",
        rows=rows, sophieu=sophieu, attachment=att, cfg=config.LISTS["xuat"])

@app.route("/xuat/<sophieu>/sua", methods=["GET","POST"])
@login_required
def sua_xuat(sophieu):
    rows = graph_api.lay_chi_tiet_phieu("xuat", sophieu)
    if not rows:
        flash("Không tìm thấy phiếu.", "warning")
        return redirect(url_for("danhsach_xuat"))
    att = graph_api.lay_attachment("xuat", rows[0]["item_id"])

    if request.method == "GET":
        return render_template("xuat/form.html", mode="edit",
            sophieu=sophieu, today=rows[0]["date"],
            rows=rows, attachment=att, cfg=config.LISTS["xuat"])

    ngay     = request.form.get("date","")
    note     = request.form.get("note","")
    new_rows = _parse_rows()
    if not new_rows:
        flash("Vui lòng thêm ít nhất 1 dòng!", "warning")
        return redirect(url_for("sua_xuat", sophieu=sophieu))

    old_ids = {str(r["item_id"]) for r in rows}
    new_ids = {str(r.get("item_id","")) for r in new_rows if r.get("item_id")}
    first_id = rows[0]["item_id"]

    for oid in old_ids - new_ids:
        graph_api.xoa_dong("xuat", oid)
    for row in new_rows:
        data = {**row, "sophieu": sophieu, "date": ngay, "note": note}
        iid  = str(row.get("item_id",""))
        if iid and iid in old_ids: graph_api.cap_nhat_dong("xuat", iid, data)
        else:                       graph_api.tao_dong("xuat", data)

    img = request.files.get("image")
    if img and img.filename:
        if att: graph_api.xoa_attachment("xuat", first_id, att["name"])
        graph_api.upload_attachment("xuat", first_id, img.filename, img.read(), img.content_type)

    flash(f"✅ Đã cập nhật Phiếu Xuất số {sophieu}!", "success")
    return redirect(url_for("chitiet_xuat", sophieu=sophieu))

@app.route("/xuat/dong/<item_id>/xoa", methods=["POST"])
@login_required
def xoa_dong_xuat(item_id):
    sophieu = request.form.get("sophieu","")
    graph_api.xoa_dong("xuat", item_id)
    flash("Đã xóa dòng.", "success")
    return redirect(url_for("chitiet_xuat", sophieu=sophieu))

@app.route("/xuat/<sophieu>/anh")
@login_required
def anh_xuat(sophieu):
    rows = graph_api.lay_chi_tiet_phieu("xuat", sophieu)
    if not rows: abort(404)
    att = graph_api.lay_attachment("xuat", rows[0]["item_id"])
    if not att: abort(404)
    data, ct = graph_api.download_attachment("xuat", rows[0]["item_id"], att["name"])
    if not data: abort(404)
    return Response(data, content_type=ct,
        headers={"Content-Disposition": f"inline; filename={att['name']}"})

# ════════════════════════════════════════════════════════════════════
#  PHIẾU NHẬP
# ════════════════════════════════════════════════════════════════════

@app.route("/nhap")
@login_required
def danhsach_nhap():
    return render_template("nhap/danhsach.html",
        phieu=graph_api.lay_danh_sach_phieu("nhap"),
        cfg=config.LISTS["nhap"])

@app.route("/nhap/moi", methods=["GET","POST"])
@login_required
def tao_nhap():
    if request.method == "GET":
        return render_template("nhap/form.html", mode="create",
            sophieu=graph_api.lay_so_phieu_moi("nhap"),
            today=date.today().isoformat(),
            rows=[], todoi_val="", fullname_val="",
            cfg=config.LISTS["nhap"])

    sophieu  = request.form.get("sophieu","").strip()
    ngay     = request.form.get("date","")
    note     = request.form.get("note","")
    todoi    = request.form.get("todoi","").strip()
    fullname = request.form.get("fullname","").strip()
    rows     = _parse_rows()

    if not rows:
        flash("Vui lòng thêm ít nhất 1 dòng cấu kiện!", "warning")
        return redirect(url_for("tao_nhap"))
    if not todoi:
        flash("Vui lòng chọn Tổ Đội!", "warning")
        return redirect(url_for("tao_nhap"))

    for row in rows:
        graph_api.tao_dong("nhap", {
            **row, "sophieu": sophieu, "date": ngay,
            "note": note, "todoi": todoi, "fullname": fullname
        })

    flash(f"✅ Đã lưu Phiếu Nhập số {sophieu}!", "success")
    return redirect(url_for("danhsach_nhap"))

@app.route("/nhap/<sophieu>")
@login_required
def chitiet_nhap(sophieu):
    rows = graph_api.lay_chi_tiet_phieu("nhap", sophieu)
    if not rows:
        flash("Không tìm thấy phiếu.", "warning")
        return redirect(url_for("danhsach_nhap"))
    return render_template("nhap/chitiet.html",
        rows=rows, sophieu=sophieu, cfg=config.LISTS["nhap"])

@app.route("/nhap/<sophieu>/sua", methods=["GET","POST"])
@login_required
def sua_nhap(sophieu):
    rows = graph_api.lay_chi_tiet_phieu("nhap", sophieu)
    if not rows:
        flash("Không tìm thấy phiếu.", "warning")
        return redirect(url_for("danhsach_nhap"))

    if request.method == "GET":
        return render_template("nhap/form.html", mode="edit",
            sophieu=sophieu, today=rows[0]["date"],
            rows=rows,
            todoi_val=rows[0].get("todoi",""),
            fullname_val=rows[0].get("fullname",""),
            cfg=config.LISTS["nhap"])

    ngay     = request.form.get("date","")
    note     = request.form.get("note","")
    todoi    = request.form.get("todoi","").strip()
    fullname = request.form.get("fullname","").strip()
    new_rows = _parse_rows()

    if not new_rows:
        flash("Vui lòng thêm ít nhất 1 dòng!", "warning")
        return redirect(url_for("sua_nhap", sophieu=sophieu))

    old_ids = {str(r["item_id"]) for r in rows}
    new_ids = {str(r.get("item_id","")) for r in new_rows if r.get("item_id")}

    for oid in old_ids - new_ids:
        graph_api.xoa_dong("nhap", oid)
    for row in new_rows:
        data = {**row, "sophieu": sophieu, "date": ngay,
                "note": note, "todoi": todoi, "fullname": fullname}
        iid  = str(row.get("item_id",""))
        if iid and iid in old_ids: graph_api.cap_nhat_dong("nhap", iid, data)
        else:                       graph_api.tao_dong("nhap", data)

    flash(f"✅ Đã cập nhật Phiếu Nhập số {sophieu}!", "success")
    return redirect(url_for("chitiet_nhap", sophieu=sophieu))

@app.route("/nhap/dong/<item_id>/xoa", methods=["POST"])
@login_required
def xoa_dong_nhap(item_id):
    sophieu = request.form.get("sophieu","")
    graph_api.xoa_dong("nhap", item_id)
    flash("Đã xóa dòng.", "success")
    return redirect(url_for("chitiet_nhap", sophieu=sophieu))

# ── Helper ────────────────────────────────────────────────────────────
def _parse_rows() -> list:
    try: return json.loads(request.form.get("rows_json","[]"))
    except: return []

@app.route("/health")
def health(): return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(debug=False)
