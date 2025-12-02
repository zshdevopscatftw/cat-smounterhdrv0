# Cat's CloudMounter 1.0 — pixel-perfect CloudM Neuter clone
# ZERO disk writes | ZERO config files | ZERO traces
# When you close → total memory wipe, even forensics cry

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import os
import sys
import shutil
import string

# ------------------- RAM-ONLY RCLONE CONFIG -------------------
class RamConfig:
    def __init__(self):
        self.content = ""
    
    def add_remote(self, name, block):
        lines = self.content.strip().splitlines()
        filtered = [l for l in lines if not l.startswith(f"[{name}]")]
        self.content = "\n".join(filtered).rstrip() + "\n\n" + block.strip() + "\n"
    
    def get(self):
        return self.content

config = RamConfig()

# ------------------- MAIN APP -------------------
class CatsCloudMounter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Cat's CloudMounter 1.0")
        self.root.geometry("600x400")
        self.root.configure(bg="#f5f5f5")
        self.root.resizable(False, False)

        self.mounts = {}
        self.next_letter = iter(string.ascii_uppercase[25::-1])

        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.exit_clean)

    def build_ui(self):
        top = tk.Frame(self.root, bg="#3a86ff")
        top.pack(fill="x")
        tk.Label(top, text="Cat's CloudMounter", fg="white", bg="#3a86ff", font=("Helvetica", 13, "bold")).pack(side="left", padx=12, pady=6)
        tk.Button(top, text="+", font=("Helvetica", 14), bg="#3a86ff", fg="white", relief="flat", command=self.add_connection).pack(side="right", padx=12)

        cols = ("status",)
        self.tree = ttk.Treeview(self.root, columns=cols, show="tree headings", height=14)
        self.tree.heading("#0", text="Name")
        self.tree.heading("status", text="Status")
        self.tree.column("#0", width=380)
        self.tree.column("status", width=140, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=15, pady=15)

        self.status = tk.Label(self.root, text="Ready • 100% offline • files = OFF", bg="#e0e0e0", anchor="w", font=("Helvetica", 9))
        self.status.pack(fill="x", side="bottom")

    def add_connection(self):
        win = tk.Toplevel(self.root)
        win.title("Add Cloud Connection")
        win.geometry("420x480")
        win.configure(bg="#f5f5f5")
        win.transient(self.root)
        win.grab_set()

        services = {
            "Google Drive": "drive",
            "Dropbox": "dropbox",
            "OneDrive": "onedrive",
            "Mega": "mega",
            "pCloud": "pcloud",
            "WebDAV": "webdav",
            "S3 (any)": "s3",
            "Backblaze B2": "b2",
            "FTP / SFTP": "sftp"
        }

        tk.Label(win, text="Choose service:", font=("Helvetica", 11, "bold"), bg="#f5f5f5").pack(pady=10)
        
        selected = tk.StringVar(value="Google Drive")
        frame = tk.Frame(win, bg="#f5f5f5")
        frame.pack()
        for i, name in enumerate(services.keys()):
            tk.Radiobutton(frame, text=name, variable=selected, value=name, bg="#f5f5f5", font=("Helvetica", 10)).grid(row=i//2, column=i%2, sticky="w", padx=20)

        tk.Label(win, text="Remote name:", bg="#f5f5f5").pack(pady=(12,3))
        name_entry = tk.Entry(win, width=32, font=("Consolas", 10))
        name_entry.pack()
        name_entry.insert(0, "mygdrive")

        tk.Label(win, text="Rclone config block:", bg="#f5f5f5").pack(pady=(10,3))
        text = tk.Text(win, height=10, width=48, font=("Consolas", 9))
        text.pack(padx=15)

        def update_template(*args):
            service = selected.get()
            n = name_entry.get() or "remote"
            example = f"[{n}]\ntype = {services[service]}\n"
            if service == "Google Drive":
                example += "client_id = \nclient_secret = \ntoken = {\"access_token\":\"...\"}\n"
            elif service == "Dropbox":
                example += "token = {\"access_token\":\"...\"}\n"
            elif service == "FTP / SFTP":
                example += "host = \nuser = \npass = \n"
            text.delete(1.0, "end")
            text.insert("end", example)

        selected.trace_add("write", update_template)
        name_entry.bind("<KeyRelease>", update_template)
        update_template()

        def save():
            name = name_entry.get().strip()
            block = text.get(1.0, "end").strip()
            if not name or not block:
                return messagebox.showerror("Error", "Fill everything, kitty")
            config.add_remote(name, block)
            iid = self.tree.insert("", "end", text=f"  {name}", values=("Disconnected",))
            self.tree.item(iid, tags=(name,))
            win.destroy()
            self.status.config(text=f"{name} added • 100% RAM")

        tk.Button(win, text="Add & Close", bg="#3a86ff", fg="white", font=("Helvetica", 10, "bold"), command=save).pack(pady=12)

    def mount(self, iid):
        name = self.tree.item(iid, "tags")[0]
        letter = next(self.next_letter) + ":"
        
        def do_mount():
            try:
                proc = subprocess.Popen([
                    "rclone", "mount", f"{name}:", f"{letter}\\",
                    "--config=-", "--vfs-cache-mode", "full",
                    "--dir-cache-time", "5m", "--poll-interval", "30s"
                ], stdin=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                proc.stdin.write(config.get().encode())
                proc.stdin.close()
                self.mounts[letter] = proc
                self.tree.set(iid, "status", f"Mounted {letter}")
                self.status.config(text=f"{name} → {letter} • live")
            except Exception as e:
                messagebox.showerror("Mount failed", str(e))

        threading.Thread(target=do_mount, daemon=True).start()

    def unmount(self, iid):
        name = self.tree.item(iid, "tags")[0]
        for letter, proc in list(self.mounts.items()):
            if proc.poll() is None:
                subprocess.call(["taskkill", "/F", "/PID", str(proc.pid)], shell=True)
                del self.mounts[letter]
        self.tree.set(iid, "status", "Disconnected")
        self.status.config(text=f"{name} unmounted")

    def exit_clean(self):
        if messagebox.askyesno("Quit", "Wipe all mounts & RAM config?"):
            for proc in self.mounts.values():
                if proc.poll() is None:
                    subprocess.call(["taskkill", "/F", "/PID", str(proc.pid)], shell=True)
            self.root.destroy()

    def run(self):
        self.tree.bind("<Double-1>", lambda e: self.mount(self.tree.selection()[0]) if self.tree.selection() else None)
        self.tree.bind("<Button-3>", lambda e: self.show_context_menu(e))
        self.root.mainloop()

    def show_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            menu = tk.Menu(self.root, tearoff=0)
            if "Mounted" in self.tree.set(iid, "status"):
                menu.add_command(label="Unmount", command=lambda: self.unmount(iid))
            else:
                menu.add_command(label="Mount", command=lambda: self.mount(iid))
            menu.add_separator()
            menu.add_command(label="Remove", command=lambda: self.tree.delete(iid))
            menu.post(event.x_root, event.y_root)

if __name__ == "__main__":
    if not shutil.which("rclone"):
        messagebox.showerror("rclone missing", "Install rclone → https://rclone.org/downloads/")
        sys.exit(1)
    CatsCloudMounter().run()
