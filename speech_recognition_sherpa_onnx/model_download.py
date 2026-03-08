import os
import sys
import yaml
import shutil
import tarfile
import zipfile
import threading
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests

try:
    import rclpy
    from ament_index_python.packages import get_package_share_directory
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False

class ModelManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sherpa-ONNX Model Manager (Triple Search)")
        self.root.geometry("1100x850")
        self.root.minsize(800, 400)

        self.base_dir = os.path.expanduser("~/.sherpa_onnx_asr_models")
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

        self.create_widgets()
        
        yaml_path = self.get_config_path()
        self.log(f"Loading YAML from: {yaml_path}")
        self.recommended_models = self.load_yaml(yaml_path)
        self.api_models = [] 

        self.refresh_all_tabs()
        self.log("System initialized.")

    def get_config_path(self):
        if ROS2_AVAILABLE:
            try:
                pkg_share = get_package_share_directory('speech_recognition_sherpa_onnx')
                path = os.path.join(pkg_share, 'config', 'model_list.yaml')
                if os.path.exists(path): return path
            except: pass
        local_path = os.path.join(os.getcwd(), 'config', 'model_list.yaml')
        return local_path

    def load_yaml(self, filename):
        if not os.path.exists(filename):
            self.log(f"Warning: YAML file not found at {filename}")
            return []
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data.get('models', [])
        except Exception as e:
            self.log(f"Error loading YAML: {e}")
            return []

    def detect_lang(self, name):
        name = name.lower()
        if any(x in name for x in ['-ja-', 'japanese']): return "Japanese"
        if any(x in name for x in ['-en-', 'english']): return "English"
        if any(x in name for x in ['-zh-', 'chinese']): return "Chinese"
        if any(x in name for x in ['-ko-', 'korean']): return "Korean"
        return "Other"

    def check_compatibility_by_name(self, name):
        name = name.lower()
        blocked_keywords = [
            "cann", "android", "ios",
            "aarch64", "arm64", "arm",
            "qnn", "rknn", "horizon", "coreml",
            "ncnn", "libtorch",
            "rk35", "rk33", "rockchip",
            "ascend"
        ]
        for k in blocked_keywords:
            if k in name:
                return True
        return False

    def create_widgets(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.tab_rec = tk.Frame(self.notebook)
        self.notebook.add(self.tab_rec, text=" Recommended ")
        self.tree_rec, _ = self.create_treeview_with_scroll(self.tab_rec)

        self.tab_search = tk.Frame(self.notebook)
        self.notebook.add(self.tab_search, text=" Search (GitHub) ")
        
        search_tool_frame = tk.Frame(self.tab_search, pady=10)
        search_tool_frame.pack(fill=tk.X)
        
        tk.Label(search_tool_frame, text="Keyword1:").pack(side=tk.LEFT, padx=2)
        self.search_entry1 = tk.Entry(search_tool_frame, width=12)
        self.search_entry1.pack(side=tk.LEFT, padx=5)
        
        tk.Label(search_tool_frame, text="Keyword2:").pack(side=tk.LEFT, padx=2)
        self.search_entry2 = tk.Entry(search_tool_frame, width=12)
        self.search_entry2.pack(side=tk.LEFT, padx=5)

        tk.Label(search_tool_frame, text="Keyword3:").pack(side=tk.LEFT, padx=2)
        self.search_entry3 = tk.Entry(search_tool_frame, width=12)
        self.search_entry3.pack(side=tk.LEFT, padx=5)

        self.btn_fetch = tk.Button(search_tool_frame, text="Search", command=self.start_api_fetch, bg="#e1f5fe", width=10)
        self.btn_fetch.pack(side=tk.LEFT, padx=10)
        
        self.tree_api, _ = self.create_treeview_with_scroll(self.tab_search)

        self.tab_installed = tk.Frame(self.notebook)
        self.notebook.add(self.tab_installed, text=" Installed Models ")
        inst_tool_frame = tk.Frame(self.tab_installed, pady=10)
        inst_tool_frame.pack(fill=tk.X)
        tk.Label(inst_tool_frame, text="Current installed models in: " + self.base_dir, fg="gray").pack(side=tk.LEFT, padx=5)
        tk.Button(inst_tool_frame, text="Refresh", command=self.refresh_installed_tab).pack(side=tk.RIGHT, padx=5)
        self.tree_inst, _ = self.create_treeview_with_scroll(self.tab_installed)

        footer = tk.Frame(self.root, padx=10, pady=5)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        btn_frame = tk.Frame(footer)
        btn_frame.pack(fill=tk.X, pady=5)
        self.btn_download = tk.Button(btn_frame, text="Download Selected", command=self.start_download, state=tk.DISABLED, width=20, bg="#e3f2fd")
        self.btn_download.pack(side=tk.LEFT, padx=5)
        self.btn_delete = tk.Button(btn_frame, text="Delete Selected", command=self.delete_model, state=tk.DISABLED, width=20, bg="#ffebee")
        self.btn_delete.pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Close", command=self.root.quit).pack(side=tk.RIGHT)

        self.log_area = scrolledtext.ScrolledText(footer, height=8, state='disabled', bg="#f0f0f0", font=("Courier New", 9))
        self.log_area.pack(fill=tk.X, pady=5)

        self.info_frame = tk.Frame(footer)
        self.info_frame.pack(fill=tk.X)
        self.status_label = tk.Label(self.info_frame, text="Ready", fg="blue")
        self.status_label.pack(side=tk.LEFT)
        self.progress = ttk.Progressbar(self.info_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=10)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
    
    def on_tab_changed(self, event):
        selected_tab = self.notebook.index(self.notebook.select())
        if selected_tab == 1 and not self.api_models:
            self.start_api_fetch()

    def create_treeview_with_scroll(self, parent):
        container = tk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)
        columns = ("name", "lang", "size", "date", "status")
        tree = ttk.Treeview(container, columns=columns, show="headings")
        tree.heading("name", text="Model Name"); tree.heading("lang", text="Lang")
        tree.heading("size", text="Size (MB)"); tree.heading("date", text="Last Updated")
        tree.heading("status", text="Status")
        tree.column("name", width=450); tree.column("lang", width=80, anchor="center")
        tree.column("size", width=80, anchor="e"); tree.column("date", width=150, anchor="center")
        tree.column("status", width=100, anchor="center")
        tree.tag_configure("suspicious", background="#ffcccc")

        vsb = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); vsb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.bind("<<TreeviewSelect>>", self.on_select)
        return tree, vsb

    def log(self, msg):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, f"[{now}] {msg}\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state='disabled')

    def refresh_all_tabs(self):
        self.refresh_recommended_list()
        self.refresh_installed_tab()
        self.update_api_tree()

    def refresh_recommended_list(self):
        self.tree_rec.delete(*self.tree_rec.get_children())
        for m in self.recommended_models:
            folder = m.get('folder_name', '')
            installed = os.path.exists(os.path.join(self.base_dir, folder))
            self.tree_rec.insert("", tk.END, values=(m.get('name', folder), self.detect_lang(folder), "-", "-", "Installed" if installed else "Missing"))

    def refresh_installed_tab(self):
        self.tree_inst.delete(*self.tree_inst.get_children())
        if not os.path.exists(self.base_dir): return
        for item in os.listdir(self.base_dir):
            item_path = os.path.join(self.base_dir, item)
            if os.path.isdir(item_path):
                stats = os.stat(item_path)
                mtime = datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M')
                total_size = sum(os.path.getsize(os.path.join(dp, f)) for dp, dn, filenames in os.walk(item_path) for f in filenames)
                self.tree_inst.insert("", tk.END, values=(item, self.detect_lang(item), f"{total_size / (1024*1024):.2f}", mtime, "Installed"))

    def start_api_fetch(self):
        k1, k2, k3 = self.search_entry1.get().lower(), self.search_entry2.get().lower(), self.search_entry3.get().lower()
        self.btn_fetch.config(state=tk.DISABLED)
        threading.Thread(target=self.api_fetch_worker, args=(k1, k2, k3), daemon=True).start()

    def api_fetch_worker(self, k1, k2, k3):
        url = "https://api.github.com/repos/k2-fsa/sherpa-onnx/releases/tags/asr-models"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            assets = r.json().get('assets', [])
            self.api_models = []
            for a in assets:
                name = a['name']
                if name.endswith(('.tar.bz2', '.tar.gz', '.zip')):
                    if all(k in name.lower() for k in [k1, k2, k3] if k):
                        dt = datetime.datetime.strptime(a['updated_at'], "%Y-%m-%dT%H:%M:%SZ")
                        is_suspicious = self.check_compatibility_by_name(name)
                        self.api_models.append({
                            'name': name, 
                            'url': a['browser_download_url'],
                            'folder_name': name.replace('.tar.bz2', '').replace('.tar.gz', '').replace('.zip', ''),
                            'size_mb': f"{a['size'] / (1024*1024):.2f}", 
                            'date': dt.strftime("%Y-%m-%d %H:%M"),
                            'is_suspicious': is_suspicious
                        })
            self.root.after(0, self.update_api_tree)
        except Exception as e: self.log(f"API Error: {e}")
        finally: self.root.after(0, lambda: self.btn_fetch.config(state=tk.NORMAL))

    def update_api_tree(self):
        self.tree_api.delete(*self.tree_api.get_children())
        for m in self.api_models:
            installed = os.path.exists(os.path.join(self.base_dir, m['folder_name']))
            tags = ("suspicious",) if m.get('is_suspicious') else ()
            self.tree_api.insert("", tk.END, values=(m['name'], self.detect_lang(m['name']), m['size_mb'], m['date'], "Installed" if installed else "Missing"), tags=tags)
    
    def get_selected_info(self):
        try:
            tab_index = self.notebook.index(self.notebook.select())
            tree = [self.tree_rec, self.tree_api, self.tree_inst][tab_index]
            sel = tree.selection()
            if not sel: return None
            list_idx = tree.index(sel[0])
            
            if tab_index == 0: 
                m = self.recommended_models[list_idx]
                return {
                    'name': m.get('name'),
                    'folder_name': m.get('folder_name'),
                    'url': m.get('url')
                }
            
            elif tab_index == 1:
                m = self.api_models[list_idx]
                return {
                    'name': m['name'],
                    'folder_name': m['folder_name'],
                    'url': m['url']
                }
            
            elif tab_index == 2: 
                vals = tree.item(sel[0])['values']
                return {
                    'name': vals[0],
                    'folder_name': vals[0],
                    'url': None
                }

        except Exception as e:
            self.log(f"Selection error: {e}")
            return None

    def _get_folder_name_from_tree(self, tab_idx, list_idx):
        if tab_idx == 0: return self.recommended_models[list_idx].get('folder_name', '')
        if tab_idx == 1: return self.api_models[list_idx].get('folder_name', '')
        return ""

    def on_select(self, event):
        tree = event.widget
        sel = tree.selection()
        if not sel: return
        status = tree.item(sel[0])['values'][-1]
        self.btn_download.config(state=tk.NORMAL if status == "Missing" else tk.DISABLED)
        self.btn_delete.config(state=tk.NORMAL if status == "Installed" else tk.DISABLED)

    def start_download(self):
        info = self.get_selected_info()
        if not info or not info.get('url'): return
        self.btn_download.config(state=tk.DISABLED)
        threading.Thread(target=self.download_worker, args=(info,), daemon=True).start()

    def download_worker(self, info):
        url = info['url']
        archive_path = os.path.join(self.base_dir, url.split('/')[-1])
        try:
            self.safe_update_status(f"Downloading...")
            self.root.after(0, lambda: self.progress.configure(mode='determinate'))
            with requests.get(url, stream=True, timeout=15) as r:
                r.raise_for_status()
                total = int(r.headers.get('content-length', 0))
                with open(archive_path, 'wb') as f:
                    curr = 0
                    for chunk in r.iter_content(chunk_size=128*1024):
                        f.write(chunk); curr += len(chunk)
                        if total > 0: self.safe_update_progress((curr/total)*100)
            
            self.safe_update_status("Extracting... (Moving files)")
            self.root.after(0, self.start_indeterminate_progress)
            
            if archive_path.endswith((".tar.bz2", ".tar.gz")):
                with tarfile.open(archive_path, "r:*") as tar: tar.extractall(path=self.base_dir)
            elif archive_path.endswith(".zip"):
                with zipfile.ZipFile(archive_path, 'r') as z: z.extractall(self.base_dir)
            
            self.log(f"Successfully installed: {info['folder_name']}")
        except Exception as e: self.log(f"Failed: {e}")
        finally:
            if os.path.exists(archive_path): os.remove(archive_path)
            self.root.after(0, self.stop_indeterminate_progress) 
            self.root.after(0, self.refresh_all_tabs)
            self.safe_update_status("Ready")

    def start_indeterminate_progress(self):
        self.progress.configure(mode='indeterminate')
        self.progress.start(10) 

    def stop_indeterminate_progress(self):
        self.progress.stop()
        self.progress.configure(mode='determinate', value=0)

    def delete_model(self):
        info = self.get_selected_info()
        if not info: return
        path = os.path.join(self.base_dir, info['folder_name'])
        if messagebox.askyesno("Confirm", f"Delete {info['folder_name']}?"):
            shutil.rmtree(path, ignore_errors=True)
            self.log(f"Deleted: {info['folder_name']}")
            self.refresh_all_tabs()

    def safe_update_progress(self, v): self.root.after(0, lambda: self.progress.configure(value=v))
    def safe_update_status(self, t): self.root.after(0, lambda: self.status_label.configure(text=t))

def main():
    root = tk.Tk()
    app = ModelManagerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()