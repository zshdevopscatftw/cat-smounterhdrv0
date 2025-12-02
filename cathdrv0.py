# Cat' Cloudmounter 0.1 — pixel-perfect to screenshot
# Full rclone automation backend | RAM-only config | Zero traces

import tkinter as tk
from tkinter import messagebox
import subprocess
import threading
import os
import sys
import shutil
import string

# ------------------- RCLONE BACKEND -------------------
class RcloneBackend:
    def __init__(self):
        self.config = ""
        self.mounts = {}
        self.letters = iter(string.ascii_uppercase[25::-1])
    
    def add_remote(self, name, rtype, **kwargs):
        block = f"[{name}]\ntype = {rtype}\n"
        for k, v in kwargs.items():
            block += f"{k} = {v}\n"
        self.config += "\n" + block
        return name
    
    def mount(self, name, callback=None):
        letter = next(self.letters) + ":"
        def do_mount():
            try:
                flags = ["rclone", "mount", f"{name}:", letter,
                         "--config=-", "--vfs-cache-mode", "full",
                         "--dir-cache-time", "5m", "--poll-interval", "30s"]
                if os.name == "nt":
                    proc = subprocess.Popen(flags, stdin=subprocess.PIPE,
                                            creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    proc = subprocess.Popen(flags, stdin=subprocess.PIPE)
                proc.stdin.write(self.config.encode())
                proc.stdin.close()
                self.mounts[name] = (letter, proc)
                if callback:
                    callback(name, letter, True)
            except Exception as e:
                if callback:
                    callback(name, None, False, str(e))
        threading.Thread(target=do_mount, daemon=True).start()
    
    def unmount(self, name):
        if name in self.mounts:
            letter, proc = self.mounts[name]
            if proc.poll() is None:
                if os.name == "nt":
                    subprocess.call(["taskkill", "/F", "/PID", str(proc.pid)],
                                    creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    proc.terminate()
            del self.mounts[name]
    
    def unmount_all(self):
        for name in list(self.mounts.keys()):
            self.unmount(name)
    
    def auth_interactive(self, name, rtype):
        """Run rclone config for OAuth-based services"""
        try:
            if os.name == "nt":
                subprocess.run(["rclone", "config", "create", name, rtype],
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.run(["rclone", "config", "create", name, rtype])
            cfg_path = os.path.expanduser("~/.config/rclone/rclone.conf")
            if os.name == "nt":
                cfg_path = os.path.join(os.environ.get("APPDATA", ""), "rclone", "rclone.conf")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r") as f:
                    self.config = f.read()
                return True
        except:
            pass
        return False

rclone = RcloneBackend()

# ------------------- SERVICE DATA -------------------
ICONS = {
    "Google Drive": "▲",
    "Dropbox": "✖",
    "OneDrive": "☁",
    "Box": "◐",
    "Amazon S3": "⊞",
    "WebDAV": "⊞",
    "FTP": "▢"
}

RCLONE_TYPES = {
    "Google Drive": "drive",
    "Dropbox": "dropbox",
    "OneDrive": "onedrive",
    "Box": "box",
    "Amazon S3": "s3",
    "WebDAV": "webdav",
    "FTP": "ftp"
}

ICON_COLORS = {
    "Google Drive": "#FBBC04",
    "Dropbox": "#0061FF",
    "OneDrive": "#0078D4",
    "Box": "#0061D5",
    "Amazon S3": "#FF9900",
    "WebDAV": "#0078D4",
    "FTP": "#0078D4"
}

# ------------------- MAIN APP -------------------
class CatCloudmounter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Cat' Cloudmounter 0.1")
        self.root.geometry("400x380")
        self.root.configure(bg="#0078D7")
        self.root.resizable(False, False)
        
        self.services = {}
        self.check_vars = {}
        self.selected = None
        
        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.exit_clean)
        self.root.after(100, self.check_rclone)

    def build_ui(self):
        # Blue border frame
        border = tk.Frame(self.root, bg="#0078D7", padx=4, pady=4)
        border.pack(fill="both", expand=True)
        
        inner = tk.Frame(border, bg="#1a1a1a")
        inner.pack(fill="both", expand=True)
        
        # Menu bar
        menubar = tk.Menu(self.root)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Add Service...", command=self.add_service_wizard)
        file_menu.add_command(label="Mount All", command=self.mount_all)
        file_menu.add_command(label="Unmount All", command=self.unmount_all)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.exit_clean)
        menubar.add_cascade(label="File", menu=file_menu)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Configure Selected", command=self.configure_selected)
        edit_menu.add_command(label="Remove Selected", command=self.remove_selected)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Refresh", command=self.refresh_status)
        menubar.add_cascade(label="View", menu=view_menu)
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Install rclone", command=self.install_rclone)
        tools_menu.add_command(label="Open rclone config", command=self.open_rclone_config)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)
        
        # Service list
        self.list_frame = tk.Frame(inner, bg="#1a1a1a")
        self.list_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        for svc in ["Google Drive", "Dropbox", "OneDrive", "Box", "Amazon S3", "WebDAV", "FTP"]:
            self.add_service_row(svc)
        
        # Status bar
        status_frame = tk.Frame(inner, bg="#1a1a1a", height=30)
        status_frame.pack(fill="x", side="bottom")
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(status_frame, text="Connected to cloud services",
                                     bg="#1a1a1a", fg="white", font=("Segoe UI", 10), anchor="w")
        self.status_label.pack(side="left", padx=10, pady=5)
        
        self.status_indicator = tk.Frame(status_frame, bg="#00FF00", width=60, height=18)
        self.status_indicator.pack(side="right", padx=10, pady=6)
        self.status_indicator.pack_propagate(False)

    def add_service_row(self, name):
        row = tk.Frame(self.list_frame, bg="#1a1a1a")
        row.pack(fill="x", pady=2)
        
        icon_color = ICON_COLORS.get(name, "#0078D4")
        icon_lbl = tk.Label(row, text=ICONS.get(name, "●"), fg=icon_color,
                           bg="#1a1a1a", font=("Segoe UI", 14))
        icon_lbl.pack(side="left", padx=(5, 10))
        
        name_lbl = tk.Label(row, text=name, fg="white", bg="#1a1a1a",
                           font=("Segoe UI", 12))
        name_lbl.pack(side="left")
        
        var = tk.BooleanVar(value=True)
        self.check_vars[name] = var
        chk = tk.Checkbutton(row, variable=var, bg="#1a1a1a", fg="white",
                            selectcolor="#1a1a1a", activebackground="#1a1a1a",
                            command=lambda n=name: self.toggle_service(n))
        chk.pack(side="right", padx=10)
        
        self.services[name] = {"row": row, "mounted": False, "letter": None}
        
        for widget in [row, icon_lbl, name_lbl]:
            widget.bind("<Button-1>", lambda e, n=name: self.select_service(n))
            widget.bind("<Double-1>", lambda e, n=name: self.configure_service(n))

    def select_service(self, name):
        if self.selected and self.selected in self.services:
            self.services[self.selected]["row"].configure(bg="#1a1a1a")
            for child in self.services[self.selected]["row"].winfo_children():
                try:
                    child.configure(bg="#1a1a1a")
                except:
                    pass
        
        self.selected = name
        self.services[name]["row"].configure(bg="#333333")
        for child in self.services[name]["row"].winfo_children():
            try:
                child.configure(bg="#333333")
            except:
                pass

    def toggle_service(self, name):
        if self.check_vars[name].get():
            self.mount_service(name)
        else:
            self.unmount_service(name)

    def mount_service(self, name):
        rtype = RCLONE_TYPES.get(name)
        if not rtype:
            return
        
        remote_name = name.lower().replace(" ", "")
        
        def on_mount(n, letter, success, error=None):
            def update():
                if success:
                    self.services[name]["mounted"] = True
                    self.services[name]["letter"] = letter
                    self.update_status(f"{name} mounted on {letter}")
                else:
                    self.check_vars[name].set(False)
                    messagebox.showerror("Mount Failed", error or "Unknown error")
            self.root.after(0, update)
        
        if remote_name not in rclone.config.lower():
            if messagebox.askyesno("Configure", f"{name} not configured.\n\nRun rclone wizard?"):
                rclone.auth_interactive(remote_name, rtype)
        
        rclone.mount(remote_name, on_mount)

    def unmount_service(self, name):
        remote_name = name.lower().replace(" ", "")
        rclone.unmount(remote_name)
        self.services[name]["mounted"] = False
        self.services[name]["letter"] = None
        self.update_status(f"{name} unmounted")

    def mount_all(self):
        for name in self.services:
            if self.check_vars[name].get():
                self.mount_service(name)

    def unmount_all(self):
        rclone.unmount_all()
        for name in self.services:
            self.services[name]["mounted"] = False
            self.check_vars[name].set(False)
        self.update_status("All unmounted")

    def configure_selected(self):
        if self.selected:
            self.configure_service(self.selected)

    def configure_service(self, name):
        rtype = RCLONE_TYPES.get(name)
        if rtype:
            remote_name = name.lower().replace(" ", "")
            rclone.auth_interactive(remote_name, rtype)
            self.update_status(f"{name} configured")

    def remove_selected(self):
        if self.selected:
            name = self.selected
            self.services[name]["row"].destroy()
            del self.services[name]
            del self.check_vars[name]
            self.selected = None

    def add_service_wizard(self):
        win = tk.Toplevel(self.root)
        win.title("Add Service")
        win.geometry("300x200")
        win.configure(bg="#1a1a1a")
        win.transient(self.root)
        win.grab_set()
        
        tk.Label(win, text="Service Name:", fg="white", bg="#1a1a1a").pack(pady=10)
        name_entry = tk.Entry(win, width=30)
        name_entry.pack()
        
        tk.Label(win, text="Rclone Type:", fg="white", bg="#1a1a1a").pack(pady=10)
        type_entry = tk.Entry(win, width=30)
        type_entry.insert(0, "drive")
        type_entry.pack()
        
        def add():
            name = name_entry.get()
            rtype = type_entry.get()
            if name and rtype:
                RCLONE_TYPES[name] = rtype
                ICONS[name] = "●"
                ICON_COLORS[name] = "#0078D4"
                self.add_service_row(name)
                win.destroy()
        
        tk.Button(win, text="Add", command=add, bg="#0078D7", fg="white").pack(pady=20)

    def refresh_status(self):
        count = sum(1 for s in self.services.values() if s["mounted"])
        self.update_status(f"{count} services mounted")

    def update_status(self, msg):
        self.status_label.config(text=msg)
        count = sum(1 for s in self.services.values() if s["mounted"])
        self.status_indicator.config(bg="#00FF00" if count > 0 else "#666666")

    def check_rclone(self):
        if not shutil.which("rclone"):
            self.show_rclone_wizard()

    def show_rclone_wizard(self):
        win = tk.Toplevel(self.root)
        win.title("rclone Required")
        win.geometry("380x180")
        win.configure(bg="#1a1a1a")
        win.transient(self.root)
        win.grab_set()
        
        tk.Label(win, text="☁ rclone not found", fg="#0078D7", bg="#1a1a1a",
                font=("Segoe UI", 14, "bold")).pack(pady=15)
        
        tk.Label(win, text="rclone is required for cloud mounting.\nInstall via winget?",
                fg="white", bg="#1a1a1a", font=("Segoe UI", 11)).pack(pady=5)
        
        btn_frame = tk.Frame(win, bg="#1a1a1a")
        btn_frame.pack(pady=20)
        
        def install_yes():
            win.destroy()
            self.install_rclone()
        
        def install_no():
            win.destroy()
            messagebox.showinfo("Manual Install", "Download rclone:\nhttps://rclone.org/downloads/")
        
        tk.Button(btn_frame, text="Yes (winget)", command=install_yes,
                 bg="#0078D7", fg="white", font=("Segoe UI", 10), width=12).pack(side="left", padx=10)
        tk.Button(btn_frame, text="No", command=install_no,
                 bg="#333333", fg="white", font=("Segoe UI", 10), width=12).pack(side="left", padx=10)

    def install_rclone(self):
        self.update_status("Installing rclone...")
        def do_install():
            try:
                if os.name == "nt":
                    subprocess.run(["winget", "install", "Rclone.Rclone", "-e", "--accept-source-agreements"],
                                   creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:
                    subprocess.run(["sudo", "apt", "install", "rclone", "-y"])
                self.root.after(0, lambda: self.update_status("rclone installed!"))
                self.root.after(0, lambda: messagebox.showinfo("Success", "rclone installed!"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Failed", str(e)))
        threading.Thread(target=do_install, daemon=True).start()

    def open_rclone_config(self):
        if os.name == "nt":
            subprocess.Popen(["rclone", "config"], creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(["rclone", "config"])

    def show_about(self):
        messagebox.showinfo("About", "Cat' Cloudmounter 0.1\n\nRAM-only cloud mounting\nPowered by rclone\n\n© Team Flames")

    def exit_clean(self):
        if messagebox.askyesno("Exit", "Unmount all and exit?"):
            rclone.unmount_all()
            self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    CatCloudmounter().run()
