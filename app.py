import json
import traceback
from functools import wraps
from datetime import date
from flask import (Flask, render_template, request,
                   redirect, url_for, session, flash,
                   jsonify, Response, abort)
import graph_api, config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# ── Global error handler — hiện traceback thật ra màn hình để debug ─
@app.errorhandler(500)
def internal_error(e):
    tb = traceback.format_exc()
    print("=== 500 TRACEBACK ===")
    print(tb)
    return (
        f"<pre style='font-size:13px;padding:20px;'>"
        f"<b>500 — Chi tiết lỗi (debug mode):</b>\n\n{tb}</pre>"
    ), 500

@app.errorhandler(Exception)
def unhandled(e):
    tb = traceback.format_exc()
    print("=== UNHANDLED EXCEPTION ===")
    print(tb)
    return (
        f"<pre style='font-size:13px;padding:20px;'>"
        f"<b>Lỗi chưa xử lý:</b>\n\n{tb}</pre>"
    ), 500


def login_required(f):
    @wraps(f)
    def d(*a, **kw):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*a, **kw)
    return d


def _norm_sophieu(s: str) -> str:
    """Chuẩn hóa số phiếu từ URL: '111.0' → '111'."""
    try:
        f = float(s)
        return str(int(f)) if f == int(f) else s
    except:
        return s


def _parse_rows() -> list:
    """Parse rows_json từ form POST. Trả về [] nếu lỗi."""
    raw = request.form.get("rows_json", "[]")
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[PARSE_ROWS] JSON error: {e}, raw={raw[:200]}")
        return []


def _safe_float(val) -> float:
    """Chuyển đổi an toàn sang float."""
    try:
        return float(str(val).replace(",", ".")) if val not in (None, "", " ") else 0.0
    except (ValueError, TypeError):
        return 0.0


# ════════════════════════════════════════════════════════════════════
#  AUTH
# ════════════════════════════════════════════════════════════════════

@app.route("/", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect(url_for("hub"))
    if request.method == "POST":
        u  = request.form.get("username", "").strip()
        p  = request.form.get("password", "").strip()
        try:
            nv = graph_api.authenticate(u, p)
        except Exception as e:
            flash(f"Lỗi kết nối SharePoint: {e}", "danger")
            return render_template("login.html")
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
    session.clear()
    return redirect(url_for("login"))


# ════════════════════════════════════════════════════════════════════
#  HUB
# ════════════════════════════════════════════════════════════════════

@app.route("/hub")
@login_required
def hub():
    return render_template("hub.html",
        full_name=session.get("full_name", ""),
        position=session.get("position", ""))


# ════════════════════════════════════════════════════════════════════
#  AJAX API
# ════════════════════════════════════════════════════════════════════

@app.route("/api/caukien")
@login_required
def api_caukien():
    try:
        return jsonify(graph_api.lay_hangmuc())
    except Exception as e:
        print(f"[API_CAUKIEN] {e}")
        return jsonify([])


@app.route("/api/todoi")
@login_required
def api_todoi():
    try:
        return jsonify(graph_api.lay_todoi())
    except Exception as e:
        print(f"[API_TODOI] {e}")
        return jsonify([])


# ════════════════════════════════════════════════════════════════════
#  TỔNG QUAN
# ════════════════════════════════════════════════════════════════════

@app.route("/tongquan")
@login_required
def tongquan():
    try:
        rows = graph_api.lay_tong_quan()
    except Exception as e:
        flash(f"Lỗi tải tổng quan: {e}", "danger")
        rows = []
    return render_template("tongquan.html", rows=rows)


# ════════════════════════════════════════════════════════════════════
#  PHIẾU XUẤT — danh sách
# ════════════════════════════════════════════════════════════════════

@app.route("/xuat")
@login_required
def danhsach_xuat():
    try:
        phieu = graph_api.lay_danh_sach_phieu("xuat")
    except Exception as e:
        flash(f"Lỗi tải danh sách: {e}", "danger")
        phieu = []
    return render_template("xuat/danhsach.html",
        phieu=phieu, cfg=config.LISTS["xuat"])


# ════════════════════════════════════════════════════════════════════
#  PHIẾU XUẤT — tạo mới
# ════════════════════════════════════════════════════════════════════

@app.route("/xuat/moi", methods=["GET", "POST"])
@login_required
def tao_xuat():
    cfg = config.LISTS["xuat"]

    if request.method == "GET":
        try:
            sophieu = graph_api.lay_so_phieu_moi("xuat")
        except Exception as e:
            print(f"[TAO_XUAT GET] {e}")
            sophieu = 1
        return render_template("xuat/form.html",
            mode="create", sophieu=sophieu,
            today=date.today().isoformat(),
            rows=[], attachment=None, cfg=cfg)

    # ── POST ────────────────────────────────────────────────────────
    sophieu = request.form.get("sophieu", "").strip()
    ngay    = request.form.get("date", "")
    note    = request.form.get("note", "")
    rows    = _parse_rows()

    print(f"[TAO_XUAT POST] sophieu={sophieu}, ngay={ngay}, rows_count={len(rows)}")

    if not sophieu:
        flash("Thiếu số phiếu!", "warning")
        return redirect(url_for("tao_xuat"))
    if not rows:
        flash("Vui lòng thêm ít nhất 1 dòng cấu kiện!", "warning")
        return redirect(url_for("tao_xuat"))

    first_id = None
    errors   = []
    for i, row in enumerate(rows):
        try:
            iid = graph_api.tao_dong("xuat", {
                "sophieu":     sophieu,
                "date":        ngay,
                "note":        note,
                "code":        str(row.get("code", "")),
                "description": str(row.get("description", "")),
                "qty":         _safe_float(row.get("qty", 0)),
            })
            if i == 0:
                first_id = iid
            if not iid:
                errors.append(f"Dòng {i+1}: không lưu được vào SharePoint")
        except Exception as e:
            errors.append(f"Dòng {i+1}: {e}")
            print(f"[TAO_XUAT POST row {i}] {traceback.format_exc()}")

    if errors:
        flash("Lỗi khi lưu: " + "; ".join(errors), "danger")
        return redirect(url_for("tao_xuat"))

    # Upload ảnh đính kèm (chỉ xuất)
    img = request.files.get("image")
    if img and img.filename and first_id:
        try:
            graph_api.upload_attachment(
                "xuat", first_id,
                img.filename, img.read(), img.content_type)
        except Exception as e:
            flash(f"⚠️ Lưu phiếu OK nhưng upload ảnh lỗi: {e}", "warning")

    flash(f"✅ Đã lưu Phiếu Xuất số {sophieu}!", "success")
    return redirect(url_for("danhsach_xuat"))


# ════════════════════════════════════════════════════════════════════
#  PHIẾU XUẤT — chi tiết
# ════════════════════════════════════════════════════════════════════

@app.route("/xuat/<sophieu>")
@login_required
def chitiet_xuat(sophieu):
    sophieu = _norm_sophieu(sophieu)
    rows = graph_api.lay_chi_tiet_phieu("xuat", sophieu)
    if not rows:
        flash("Không tìm thấy phiếu.", "warning")
        return redirect(url_for("danhsach_xuat"))
    try:
        att = graph_api.lay_attachment("xuat", rows[0]["item_id"])
    except Exception:
        att = None
    return render_template("xuat/chitiet.html",
        rows=rows, sophieu=sophieu,
        attachment=att, cfg=config.LISTS["xuat"])


# ════════════════════════════════════════════════════════════════════
#  PHIẾU XUẤT — sửa
# ════════════════════════════════════════════════════════════════════

@app.route("/xuat/<sophieu>/sua", methods=["GET", "POST"])
@login_required
def sua_xuat(sophieu):
    sophieu = _norm_sophieu(sophieu)
    rows = graph_api.lay_chi_tiet_phieu("xuat", sophieu)
    if not rows:
        flash("Không tìm thấy phiếu.", "warning")
        return redirect(url_for("danhsach_xuat"))
    try:
        att = graph_api.lay_attachment("xuat", rows[0]["item_id"])
    except Exception:
        att = None

    if request.method == "GET":
        return render_template("xuat/form.html",
            mode="edit", sophieu=sophieu,
            today=rows[0]["date"],
            rows=rows, attachment=att,
            cfg=config.LISTS["xuat"])

    ngay     = request.form.get("date", "")
    note     = request.form.get("note", "")
    new_rows = _parse_rows()

    if not new_rows:
        flash("Vui lòng thêm ít nhất 1 dòng!", "warning")
        return redirect(url_for("sua_xuat", sophieu=sophieu))

    old_ids    = {str(r["item_id"]) for r in rows}
    new_ids    = {str(r.get("item_id", "")) for r in new_rows if r.get("item_id")}
    first_id   = rows[0]["item_id"]

    for oid in old_ids - new_ids:
        graph_api.xoa_dong("xuat", oid)

    for row in new_rows:
        data = {
            "sophieu":     sophieu,
            "date":        ngay,
            "note":        note,
            "code":        str(row.get("code", "")),
            "description": str(row.get("description", "")),
            "qty":         _safe_float(row.get("qty", 0)),
        }
        iid = str(row.get("item_id", ""))
        if iid and iid in old_ids:
            graph_api.cap_nhat_dong("xuat", iid, data)
        else:
            graph_api.tao_dong("xuat", data)

    img = request.files.get("image")
    if img and img.filename:
        try:
            if att:
                graph_api.xoa_attachment("xuat", first_id, att["name"])
            graph_api.upload_attachment(
                "xuat", first_id,
                img.filename, img.read(), img.content_type)
        except Exception as e:
            flash(f"⚠️ Cập nhật OK nhưng ảnh lỗi: {e}", "warning")

    flash(f"✅ Đã cập nhật Phiếu Xuất số {sophieu}!", "success")
    return redirect(url_for("danhsach_xuat"))


@app.route("/xuat/dong/<item_id>/xoa", methods=["POST"])
@login_required
def xoa_dong_xuat(item_id):
    sophieu = _norm_sophieu(request.form.get("sophieu", ""))
    graph_api.xoa_dong("xuat", item_id)
    flash("Đã xóa dòng.", "success")
    return redirect(url_for("chitiet_xuat", sophieu=sophieu))


@app.route("/xuat/<sophieu>/anh")
@login_required
def anh_xuat(sophieu):
    rows = graph_api.lay_chi_tiet_phieu("xuat", sophieu)
    if not rows:
        abort(404)
    att = graph_api.lay_attachment("xuat", rows[0]["item_id"])
    if not att:
        abort(404)
    data, ct = graph_api.download_attachment("xuat", rows[0]["item_id"], att["name"])
    if not data:
        abort(404)
    return Response(data, content_type=ct,
        headers={"Content-Disposition": f"inline; filename={att['name']}"})


# ════════════════════════════════════════════════════════════════════
#  PHIẾU NHẬP — danh sách
# ════════════════════════════════════════════════════════════════════

@app.route("/nhap")
@login_required
def danhsach_nhap():
    try:
        phieu = graph_api.lay_danh_sach_phieu("nhap")
    except Exception as e:
        flash(f"Lỗi tải danh sách: {e}", "danger")
        phieu = []
    return render_template("nhap/danhsach.html",
        phieu=phieu, cfg=config.LISTS["nhap"])


# ════════════════════════════════════════════════════════════════════
#  PHIẾU NHẬP — tạo mới
# ════════════════════════════════════════════════════════════════════

@app.route("/nhap/moi", methods=["GET", "POST"])
@login_required
def tao_nhap():
    cfg = config.LISTS["nhap"]

    if request.method == "GET":
        try:
            sophieu = graph_api.lay_so_phieu_moi("nhap")
        except Exception as e:
            print(f"[TAO_NHAP GET] {e}")
            sophieu = 1
        return render_template("nhap/form.html",
            mode="create", sophieu=sophieu,
            today=date.today().isoformat(),
            rows=[], todoi_val="", fullname_val="", cfg=cfg)

    # ── POST ────────────────────────────────────────────────────────
    sophieu  = request.form.get("sophieu", "").strip()
    ngay     = request.form.get("date", "")
    note     = request.form.get("note", "")
    todoi    = request.form.get("todoi", "").strip()
    fullname = request.form.get("fullname", "").strip()
    rows     = _parse_rows()

    print(f"[TAO_NHAP POST] sophieu={sophieu}, todoi={todoi}, rows_count={len(rows)}")

    if not sophieu:
        flash("Thiếu số phiếu!", "warning")
        return redirect(url_for("tao_nhap"))
    if not todoi:
        flash("Vui lòng chọn Tổ Đội!", "warning")
        return redirect(url_for("tao_nhap"))
    if not rows:
        flash("Vui lòng thêm ít nhất 1 dòng cấu kiện!", "warning")
        return redirect(url_for("tao_nhap"))

    errors = []
    for i, row in enumerate(rows):
        try:
            iid = graph_api.tao_dong("nhap", {
                "sophieu":     sophieu,
                "date":        ngay,
                "note":        note,
                "todoi":       todoi,
                "fullname":    fullname,
                "code":        str(row.get("code", "")),
                "description": str(row.get("description", "")),
                "qty":         _safe_float(row.get("qty", 0)),
            })
            if not iid:
                errors.append(f"Dòng {i+1}: không lưu được vào SharePoint")
        except Exception as e:
            errors.append(f"Dòng {i+1}: {e}")
            print(f"[TAO_NHAP POST row {i}] {traceback.format_exc()}")

    if errors:
        flash("Lỗi khi lưu: " + "; ".join(errors), "danger")
        return redirect(url_for("tao_nhap"))

    flash(f"✅ Đã lưu Phiếu Nhập số {sophieu}!", "success")
    return redirect(url_for("danhsach_nhap"))


# ════════════════════════════════════════════════════════════════════
#  PHIẾU NHẬP — chi tiết
# ════════════════════════════════════════════════════════════════════

@app.route("/nhap/<sophieu>")
@login_required
def chitiet_nhap(sophieu):
    sophieu = _norm_sophieu(sophieu)
    rows = graph_api.lay_chi_tiet_phieu("nhap", sophieu)
    if not rows:
        flash("Không tìm thấy phiếu.", "warning")
        return redirect(url_for("danhsach_nhap"))
    return render_template("nhap/chitiet.html",
        rows=rows, sophieu=sophieu, cfg=config.LISTS["nhap"])


# ════════════════════════════════════════════════════════════════════
#  PHIẾU NHẬP — sửa
# ════════════════════════════════════════════════════════════════════

@app.route("/nhap/<sophieu>/sua", methods=["GET", "POST"])
@login_required
def sua_nhap(sophieu):
    sophieu = _norm_sophieu(sophieu)
    rows = graph_api.lay_chi_tiet_phieu("nhap", sophieu)
    if not rows:
        flash("Không tìm thấy phiếu.", "warning")
        return redirect(url_for("danhsach_nhap"))

    if request.method == "GET":
        return render_template("nhap/form.html",
            mode="edit", sophieu=sophieu,
            today=rows[0]["date"],
            rows=rows,
            todoi_val=rows[0].get("todoi", ""),
            fullname_val=rows[0].get("fullname", ""),
            cfg=config.LISTS["nhap"])

    ngay     = request.form.get("date", "")
    note     = request.form.get("note", "")
    todoi    = request.form.get("todoi", "").strip()
    fullname = request.form.get("fullname", "").strip()
    new_rows = _parse_rows()

    if not new_rows:
        flash("Vui lòng thêm ít nhất 1 dòng!", "warning")
        return redirect(url_for("sua_nhap", sophieu=sophieu))

    old_ids = {str(r["item_id"]) for r in rows}
    new_ids = {str(r.get("item_id", "")) for r in new_rows if r.get("item_id")}

    for oid in old_ids - new_ids:
        graph_api.xoa_dong("nhap", oid)

    for row in new_rows:
        data = {
            "sophieu":     sophieu,
            "date":        ngay,
            "note":        note,
            "todoi":       todoi,
            "fullname":    fullname,
            "code":        str(row.get("code", "")),
            "description": str(row.get("description", "")),
            "qty":         _safe_float(row.get("qty", 0)),
        }
        iid = str(row.get("item_id", ""))
        if iid and iid in old_ids:
            graph_api.cap_nhat_dong("nhap", iid, data)
        else:
            graph_api.tao_dong("nhap", data)

    flash(f"✅ Đã cập nhật Phiếu Nhập số {sophieu}!", "success")
    return redirect(url_for("danhsach_nhap"))


@app.route("/nhap/dong/<item_id>/xoa", methods=["POST"])
@login_required
def xoa_dong_nhap(item_id):
    sophieu = _norm_sophieu(request.form.get("sophieu", ""))
    graph_api.xoa_dong("nhap", item_id)
    flash("Đã xóa dòng.", "success")
    return redirect(url_for("chitiet_nhap", sophieu=sophieu))


# ════════════════════════════════════════════════════════════════════
#  MISC
# ════════════════════════════════════════════════════════════════════

@app.route("/health")
def health():
    return {"status": "ok"}, 200


# ════════════════════════════════════════════════════════════════════
#  DEBUG — xem tên cột thật của SharePoint (xóa sau khi dùng xong)
# ════════════════════════════════════════════════════════════════════

@app.route("/debug/columns")
@login_required
def debug_columns():
    result = {}
    for key in ["xuat", "nhap"]:
        list_name = config.LISTS[key]["list_name"]
        result[list_name] = graph_api.lay_ten_cot(list_name)
    for list_name in [config.LIST_HANGMUC["list_name"],
                      config.LIST_TODOI["list_name"],
                      config.LIST_USERS["list_name"]]:
        result[list_name] = graph_api.lay_ten_cot(list_name)

    html = "<h2 style='font-family:monospace'>Debug: Internal Field Names của SharePoint</h2>"
    for lst, cols in result.items():
        html += f"<h3 style='font-family:monospace;color:#1a2744'>List: <u>{lst}</u></h3>"
        html += "<table border=1 cellpadding=6 style='font-family:monospace;border-collapse:collapse'>"
        html += "<tr style='background:#eee'><th>internal name (dùng trong API)</th><th>displayName</th></tr>"
        for c in cols:
            if "error" in c:
                html += f"<tr><td colspan=2 style='color:red'>{c}</td></tr>"
            else:
                html += f"<tr><td><b>{c['name']}</b></td><td>{c['displayName']}</td></tr>"
        html += "</table><br>"
    return html


if __name__ == "__main__":
    app.run(debug=True)
