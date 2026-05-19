#!/usr/bin/env python3
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

import server


class ForMyDJDesktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ForMyDJ")
        self.geometry("920x560")
        self.minsize(820, 480)

        self.output_dir = tk.StringVar(value=str(server.DEFAULT_OUTPUT))
        self.format_var = tk.StringVar(value="wav")
        self.link_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")

        self.configure(bg="#111313")
        self.build_ui()
        self.refresh_jobs()

    def build_ui(self):
        root = ttk.Frame(self, padding=16)
        root.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(root)
        header.pack(fill=tk.X)

        title_block = ttk.Frame(header)
        title_block.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(title_block, text="ForMyDJ", font=("SF Pro Display", 24, "bold")).pack(anchor=tk.W)
        ttk.Label(title_block, text="Local DJ audio intake").pack(anchor=tk.W)

        ttk.Button(header, text="Clear Cache", command=self.clear_cache).pack(side=tk.RIGHT)

        form = ttk.Frame(root, padding=(0, 18, 0, 10))
        form.pack(fill=tk.X)

        self.link_entry = ttk.Entry(form, textvariable=self.link_var)
        self.link_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.link_entry.bind("<Return>", lambda _: self.submit_link())

        format_picker = ttk.Combobox(
            form,
            textvariable=self.format_var,
            values=("wav", "aiff", "mp3"),
            width=8,
            state="readonly",
        )
        format_picker.grid(row=0, column=1, padx=(0, 8))
        ttk.Button(form, text="Download", command=self.submit_link).grid(row=0, column=2)
        form.columnconfigure(0, weight=1)

        output = ttk.Frame(root)
        output.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(output, text="Output folder").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(output, textvariable=self.output_dir).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(output, text="Choose", command=self.choose_output).pack(side=tk.LEFT)

        actions = ttk.Frame(root)
        actions.pack(fill=tk.X, pady=(0, 12))
        ttk.Button(actions, text="Add Audio Files", command=self.add_files).pack(side=tk.LEFT)
        ttk.Label(actions, text="3 active jobs, unlimited queue").pack(side=tk.RIGHT)

        columns = ("status", "title", "artist", "format", "key", "progress", "output")
        self.tree = ttk.Treeview(root, columns=columns, show="headings", height=16)
        headings = {
            "status": "Status",
            "title": "Title",
            "artist": "Artist",
            "format": "Format",
            "key": "Key",
            "progress": "Progress",
            "output": "Output",
        }
        widths = {
            "status": 90,
            "title": 180,
            "artist": 140,
            "format": 70,
            "key": 90,
            "progress": 120,
            "output": 300,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True)

        ttk.Label(root, textvariable=self.status_var).pack(fill=tk.X, pady=(10, 0))

    def submit_link(self):
        link = self.link_var.get().strip()
        if not link:
            return
        self.link_var.set("")
        server.enqueue("url", link, self.format_var.get(), self.output_dir.get())
        self.status_var.set("Queued link")
        self.refresh_jobs()

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="Choose audio files",
            filetypes=[
                ("Audio files", "*.wav *.aiff *.aif *.mp3 *.m4a *.flac *.ogg *.opus"),
                ("All files", "*.*"),
            ],
        )
        for path in paths:
            server.enqueue("file", path, self.format_var.get(), self.output_dir.get())
        if paths:
            self.status_var.set(f"Queued {len(paths)} file(s)")
            self.refresh_jobs()

    def choose_output(self):
        folder = filedialog.askdirectory(title="Choose output folder", initialdir=self.output_dir.get())
        if folder:
            self.output_dir.set(folder)

    def clear_cache(self):
        shutil.rmtree(server.CACHE_DIR, ignore_errors=True)
        self.status_var.set("Cache cleared")

    def refresh_jobs(self):
        existing = set(self.tree.get_children())
        seen = set()

        for job in server.public_jobs():
            job_id = job["id"]
            seen.add(job_id)
            values = (
                job.get("status", ""),
                job.get("title") or Path(job.get("input_value", "")).name,
                job.get("artist") or "Unknown artist",
                job.get("format", "").upper(),
                job.get("estimated_key") or "",
                job.get("progress", ""),
                job.get("output_path") or " ".join(job.get("warnings", [])) or job.get("error", ""),
            )
            if job_id in existing:
                self.tree.item(job_id, values=values)
            else:
                self.tree.insert("", tk.END, iid=job_id, values=values)

        for stale in existing - seen:
            self.tree.delete(stale)

        self.after(1500, self.refresh_jobs)


if __name__ == "__main__":
    app = ForMyDJDesktop()
    app.mainloop()

