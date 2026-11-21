# -*- coding: utf-8 -*-
"""坚果云 WebDAV：控件 + 上传/下载回调 + 界面区块。"""
import io

MAIN = r"C:\myapp\main.py"
t = io.open(MAIN, encoding="utf-8").read()

# ---------- 1) 工具函数 ----------
FN = r'''
DAV_CONFIG_FILE = os.path.join(DATA_DIR, "dav_config.json")
DAV_REMOTE_NAME = "chiyu_latest.zip"


def load_dav_config():
    try:
        if os.path.exists(DAV_CONFIG_FILE):
            with open(DAV_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except BaseException:
        pass
    return {"url": "https://dav.jianguoyun.com/dav/", "user": "", "pass": ""}


def save_dav_config(cfg):
    with open(DAV_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def make_backup_zip(dest_path=None):
    if dest_path is None:
        dest_path = os.path.join(DATA_DIR, "_backup_%s.zip" % time.strftime("%Y%m%d_%H%M%S"))
    with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(DATA_DIR):
            if "_restore_tmp" in root.split(os.sep):
                continue
            for f in files:
                if f.startswith("."):
                    continue
                full = os.path.join(root, f)
                zf.write(full, os.path.relpath(full, DATA_DIR))
    return dest_path


def dav_upload(zip_path, cfg):
    url = (cfg.get("url") or "").rstrip("/") + "/" + DAV_REMOTE_NAME
    with open(zip_path, "rb") as f:
        data = f.read()
    r = requests.put(url, data=data, auth=(cfg["user"], cfg["pass"]), timeout=90,
                     headers={"Content-Type": "application/zip"})
    return r.status_code in (200, 201, 204), r.status_code


def dav_download(cfg, dest_path):
    url = (cfg.get("url") or "").rstrip("/") + "/" + DAV_REMOTE_NAME
    r = requests.get(url, auth=(cfg["user"], cfg["pass"]), timeout=90)
    if r.status_code != 200 or len(r.content) < 500:
        return False, r.status_code
    with open(dest_path, "wb") as f:
        f.write(r.content)
    return True, len(r.content)


'''
anchor = "def build_study_export_md():"
if "DAV_CONFIG_FILE" not in t:
    t = t.replace(anchor, FN.lstrip("\n") + anchor, 1)

# ---------- 2) 控件与回调（放在 backup_status 定义之后） ----------
ANCHOR2 = '            backup_status = ft.Text("", size=13, color=ft.Colors.GREY_500)'
assert ANCHOR2 in t
BLOCK = ANCHOR2 + '''

            _dav = load_dav_config()
            dav_url_input = ft.TextField(label="WebDAV 地址",
                                         value=_dav.get("url") or "https://dav.jianguoyun.com/dav/",
                                         dense=True)
            dav_user_input = ft.TextField(label="坚果云账号（邮箱）", value=_dav.get("user") or "", dense=True)
            dav_pass_input = ft.TextField(label="应用密码", value=_dav.get("pass") or "",
                                          password=True, can_reveal_password=True, dense=True)
            dav_status = ft.Text("", size=12, color=C_TEXT2)

            def _dav_save_inputs():
                cfg = {"url": (dav_url_input.value or "").strip(),
                       "user": (dav_user_input.value or "").strip(),
                       "pass": (dav_pass_input.value or "").strip()}
                save_dav_config(cfg)
                return cfg

            def dav_do_upload(e):
                cfg = _dav_save_inputs()
                if not cfg["user"] or not cfg["pass"]:
                    show_toast("先填账号和应用密码", "red")
                    return
                dav_status.value = "⏳ 正在打包并上传..."
                dav_status.color = C_TEXT2
                page.update()

                def _job():
                    try:
                        zp = make_backup_zip()
                        ok, code = dav_upload(zp, cfg)
                        dav_status.value = ("✅ 已上传到坚果云" if ok else f"❌ 上传失败（HTTP {code}）")
                        dav_status.color = "#81C784" if ok else "#EF5350"
                        try:
                            os.remove(zp)
                        except BaseException:
                            pass
                    except Exception as ex:
                        dav_status.value = f"❌ 上传异常：{str(ex)[:60]}"
                        dav_status.color = "#EF5350"
                    try:
                        page.update()
                    except BaseException:
                        pass

                threading.Thread(target=_job, daemon=True).start()

            def dav_do_download(e):
                cfg = _dav_save_inputs()
                if not cfg["user"] or not cfg["pass"]:
                    show_toast("先填账号和应用密码", "red")
                    return
                dav_status.value = "⏳ 正在从坚果云下载..."
                dav_status.color = C_TEXT2
                page.update()

                def _job():
                    try:
                        dest = os.path.join(DATA_DIR, "网盘下载备份.zip")
                        ok, info = dav_download(cfg, dest)
                        if ok:
                            dav_status.value = (f"✅ 已下载 {int(info/1024)}KB 到 data 目录，"
                                                f"再用上面的「覆盖恢复」选择它")
                            dav_status.color = "#81C784"
                        else:
                            dav_status.value = f"❌ 下载失败（HTTP {info}）"
                            dav_status.color = "#EF5350"
                    except Exception as ex:
                        dav_status.value = f"❌ 下载异常：{str(ex)[:60]}"
                        dav_status.color = "#EF5350"
                    try:
                        page.update()
                    except BaseException:
                        pass

                threading.Thread(target=_job, daemon=True).start()'''
t = t.replace(ANCHOR2, BLOCK, 1)

# ---------- 3) 界面区块 ----------
OLD = '''                backup_status,
                ft.Container(height=20),'''
NEW = '''                backup_status,
                ft.Divider(),
                ft.Text("☁️ 坚果云同步（WebDAV）", size=16, weight=ft.FontWeight.W_600),
                ft.Text("坚果云「账户信息 → 安全选项 → 添加应用」生成应用密码，别用登录密码",
                        size=11, color=C_TEXT2),
                dav_url_input, dav_user_input, dav_pass_input,
                ft.Row([
                    ft.ElevatedButton("☁️ 上传到网盘", icon=ft.Icons.CLOUD_UPLOAD,
                                      on_click=lambda e: dav_do_upload(e)),
                    ft.ElevatedButton("⬇️ 从网盘拉取", icon=ft.Icons.CLOUD_DOWNLOAD,
                                      on_click=lambda e: dav_do_download(e)),
                ], spacing=10, wrap=True),
                dav_status,
                ft.Container(height=20),'''
assert OLD in t
t = t.replace(OLD, NEW, 1)

io.open(MAIN, "w", encoding="utf-8", newline="\n").write(t)
print("WebDAV 已接入")
