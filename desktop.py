#!/usr/bin/env python3
"""Desktop edition by Abdallah22s; no discovery or account reads at startup."""
from __future__ import annotations

import os
from pathlib import Path
import queue
import threading
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from desktop_support import APP_ID, APP_NAME, APP_VERSION, APP_AUTHOR, APP_URL, error_report


class Desktop:
    def __init__(self, root):
        self.root, self.busy, self.dialog = root, False, None
        self.events = queue.Queue()
        self.report, self.apps, self.manual, self.folder = '', [], {}, None
        self.action = 'patch'
        root.title(APP_NAME)
        root.geometry('620x510')
        root.minsize(560, 470)
        root.configure(bg='#eef2f6')
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.report_callback_exception = self.callback_error
        icon = Path(__file__).resolve().parent / 'assets' / 'app.ico'
        if os.name == 'nt' and icon.is_file():
            root.iconbitmap(str(icon))
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TFrame', background='#eef2f6')
        style.configure('Surface.TFrame', background='#ffffff')
        style.configure('TLabel', background='#eef2f6', foreground='#182638', font=('Segoe UI', 10))
        style.configure('Title.TLabel', font=('Segoe UI', 19, 'bold'))
        style.configure('Heading.TLabel', background='#ffffff', font=('Segoe UI', 17, 'bold'))
        style.configure('Muted.TLabel', foreground='#5d6b7c')
        style.configure('Surface.TLabel', background='#ffffff', foreground='#5d6b7c')
        style.configure('Status.TLabel', background='#e7f3ed', foreground='#18724a', font=('Segoe UI', 9, 'bold'), padding=(10, 5))
        style.configure('Attention.Status.TLabel', background='#fff1d6', foreground='#875600')
        style.configure('Working.Status.TLabel', background='#e7effb', foreground='#1769bd')
        style.configure('TButton', padding=(10, 7))
        style.configure('Activate.TButton', font=('Segoe UI', 12, 'bold'), padding=(20, 14), borderwidth=0,
                        background='#1769bd', foreground='white')
        style.map('Activate.TButton', background=[('disabled', '#dce3ec'), ('active', '#12569c')],
                  foreground=[('disabled', '#64748b')])
        style.configure('Link.TButton', background='#eef2f6', foreground='#1769bd', borderwidth=0, padding=(0, 6))
        style.map('Link.TButton', background=[('active', '#e2e9f2')])
        style.configure('Options.TMenubutton', background='#eef2f6', foreground='#5d6b7c', borderwidth=0, padding=(0, 6))
        style.configure('Treeview', rowheight=32, font=('Segoe UI', 10), borderwidth=0,
                        background='#ffffff', fieldbackground='#ffffff', foreground='#182638')
        style.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'), background='#e9eef4', foreground='#5d6b7c', padding=(10, 8))
        style.configure('Work.Horizontal.TProgressbar', background='#1769bd', troughcolor='#eaf0f6', borderwidth=0, thickness=4)
        body = ttk.Frame(root, padding=28)
        body.pack(fill='both', expand=True)
        header = ttk.Frame(body)
        header.pack(fill='x')
        png = icon.with_suffix('.png')
        if png.is_file():
            self.logo = tk.PhotoImage(file=str(png)).subsample(8, 8)
            ttk.Label(header, image=self.logo).pack(side='left', padx=(0, 10))
        ttk.Label(header, text=APP_NAME, style='Title.TLabel').pack(side='left')
        ttk.Label(header, text='v' + APP_VERSION, style='Muted.TLabel').pack(side='right')
        ttk.Label(body, text='A lighter way to get ready.', style='Muted.TLabel').pack(anchor='w', pady=(6, 24))
        surface = tk.Frame(body, bg='#ffffff', highlightbackground='#dce4ed', highlightthickness=1)
        surface.pack(fill='x')
        content = ttk.Frame(surface, style='Surface.TFrame', padding=24)
        content.pack(fill='both', expand=True)
        self.status = tk.StringVar(value='Ready')
        self.status_label = ttk.Label(content, textvariable=self.status, style='Status.TLabel')
        self.status_label.pack(anchor='w', pady=(0, 18))
        self.heading = tk.StringVar(value='Ready to activate')
        self.description = tk.StringVar(value='Close Antigravity and its background processes, then click Activate. '
                                      'Your installation will be located and checked automatically.')
        ttk.Label(content, textvariable=self.heading, style='Heading.TLabel').pack(anchor='w')
        ttk.Label(content, textvariable=self.description, wraplength=460, style='Surface.TLabel').pack(fill='x', pady=(12, 22))
        self.activate = ttk.Button(content, text='Activate', style='Activate.TButton', command=self.start)
        self.activate.pack(fill='x')
        self.progress = ttk.Progressbar(content, mode='indeterminate', style='Work.Horizontal.TProgressbar')
        self.result_area = ttk.Frame(body)
        ttk.Label(self.result_area, text='Installation results', style='Muted.TLabel').pack(anchor='w', pady=(18, 8))
        self.results = ttk.Treeview(self.result_area, columns=('component', 'state'), show='headings', height=4, selectmode='none')
        for column, title, width in [('component', 'Component', 250), ('state', 'Status', 210)]:
            self.results.heading(column, text=title)
            self.results.column(column, width=width, stretch=column == 'component')
        self.results.pack(fill='x')
        self.footer = ttk.Frame(body)
        self.footer.pack(fill='x', pady=(16, 0))
        self.options = ttk.Menubutton(self.footer, text='Additional options', style='Options.TMenubutton')
        menu = tk.Menu(self.options, tearoff=False)
        menu.add_command(label='Restore originals', command=self.restore)
        menu.add_command(label='Choose installation location…', command=self.choose_folder)
        menu.add_command(label='View last error report', command=self.show_report)
        self.options.configure(menu=menu)
        self.options.pack(side='left')
        ttk.Button(self.footer, text='GitHub / ' + APP_AUTHOR, style='Link.TButton',
                   command=lambda: webbrowser.open(APP_URL)).pack(side='right')
        ttk.Label(body, text='Originals are backed up automatically. Your subscription stays unchanged.',
                  wraplength=500, style='Muted.TLabel').pack(anchor='w', pady=(18, 0))
        self.fit_window()
        root.after(80, self.poll)

    def fit_window(self):
        root = self.root
        root.update_idletasks()
        # Font metrics vary with Windows scaling; keep all controls visible.
        width, height = max(560, root.winfo_reqwidth()), max(470, root.winfo_reqheight() + 16)
        root.minsize(width, height)
        root.geometry(f'{max(620, width, root.winfo_width())}x{max(510, height, root.winfo_height())}')

    def _busy(self, value):
        self.busy = value
        for control in (self.activate, self.options):
            control.configure(state='disabled' if value else 'normal')
        if value:
            self.status.set('Working')
            self.status_label.configure(style='Working.Status.TLabel')
            self.progress.pack(fill='x', pady=(16, 0))
            self.progress.start(12)
            self.fit_window()
        else:
            self.progress.stop()
            self.progress.pack_forget()

    def worker(self, phase, callback):
        self._busy(True)
        def run():
            try:
                self.events.put((phase, callback()))
            except Exception as exc:
                self.events.put(('error', error_report('check' if phase == 'discovery' else phase,
                                                      self.apps, exception=exc)))
        threading.Thread(target=run, daemon=True).start()

    def poll(self):
        try:
            while True:
                phase, result = self.events.get_nowait()
                self._busy(False)
                if phase == 'discovery':
                    self.discovered(result)
                elif phase == 'error':
                    self.report = result
                    self.heading.set('Operation stopped')
                    self.status.set('Needs attention')
                    self.status_label.configure(style='Attention.Status.TLabel')
                    self.description.set('The operation could not be completed. Copy the report for support.')
                    self.show_report()
                else:
                    self.completed(result)
        except queue.Empty:
            pass
        finally:
            self.root.after(80, self.poll)

    def start(self, action='patch'):
        if self.busy or self.dialog:
            return
        import desktop_workflow as workflow
        self.action = action
        self.heading.set('Locating installations…')
        self.description.set('Checking known locations. Multiple installations will be presented for selection.')
        self.worker('discovery', lambda: workflow.discover(self.manual, self.folder))

    def discovered(self, discovery):
        choices = {g: c for g, c in discovery.groups.items() if c}
        targets = [t for candidates in choices.values() for c in candidates for t in c.paths]
        overlap = len(targets) != len(set(targets))
        if not choices or discovery.issues or overlap or any(len(c) > 1 for c in choices.values()):
            self.select_location(discovery)
        else:
            self.operate({t: p for candidates in choices.values() for t, p in candidates[0].paths.items()})

    def operate(self, paths):
        import desktop_workflow as workflow
        self.heading.set('Activating…' if self.action == 'patch' else 'Restoring originals…')
        self.description.set('Checking the selected files, backups and final results. Please wait.')
        self.worker(self.action, lambda: workflow.execute(self.action, workflow.inspect(paths)))

    def select_location(self, discovery):
        import desktop_workflow as workflow
        self.status.set('Choose location')
        self.status_label.configure(style='Working.Status.TLabel')
        window = tk.Toplevel(self.root)
        self.dialog = window
        window.title('Choose installation')
        window.geometry('780x530')
        window.minsize(740, 500)
        window.transient(self.root)
        window.grab_set()
        frame = ttk.Frame(window, padding=20)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Choose the installation you use', style='Heading.TLabel').pack(anchor='w')
        hint = ('No installation found. Choose its folder, or choose a component file below.'
                if not any(discovery.groups.values()) else
                'Choose one location per component. Unselected installations will remain unchanged.')
        if discovery.issues:
            hint += '\n' + '\n'.join(discovery.issues)
        ttk.Label(frame, text=hint, wraplength=700, style='Muted.TLabel').pack(fill='x', pady=(8, 14))
        controls = []
        for group, candidates in discovery.groups.items():
            if not candidates:
                continue
            ttk.Label(frame, text=workflow.GROUP_NAMES[group]).pack(anchor='w', pady=(4, 3))
            labels = ['Skip this component'] + [f'{next(iter(c.paths.values()))}  [{c.source}]' for c in candidates]
            box = ttk.Combobox(frame, values=labels, state='readonly', width=90)
            box.pack(fill='x')
            if len(candidates) == 1:
                box.current(1)
            controls.append((box, candidates))
        buttons = ttk.Frame(frame)
        buttons.pack(side='bottom', fill='x', pady=(16, 0))
        def dismiss():
            self.dialog = None
            window.destroy()
        def cancel():
            dismiss()
            self.heading.set('Ready to activate')
            self.status.set('Ready')
            self.status_label.configure(style='Status.TLabel')
            self.description.set('No changes were made. Click Activate to try again.')
        def browse_folder():
            folder = filedialog.askdirectory(parent=window, title='Choose Antigravity installation folder')
            if folder:
                self.folder = folder
                dismiss()
                self.start(self.action)
        def browse_file():
            target = target_box.get()
            path = filedialog.askopenfilename(parent=window, title='Choose ' + workflow.NAMES[target])
            if path:
                self.manual[target] = path
                dismiss()
                self.start(self.action)
        def accept():
            paths = {}
            for box, candidates in controls:
                index = box.current()
                if index < 0:
                    messagebox.showinfo(APP_NAME, 'Choose a location or Skip for each component.', parent=window)
                    return
                if index == 0:
                    continue
                for target, path in candidates[index - 1].paths.items():
                    if target in paths and paths[target] != path:
                        messagebox.showinfo(APP_NAME, 'Two selected installations provide the same component. '
                                            'Choose Skip for one of them.', parent=window)
                        return
                    paths[target] = path
            if not paths:
                messagebox.showinfo(APP_NAME, 'Select an installation folder or component file first.', parent=window)
                return
            dismiss()
            self.operate(paths)
        ttk.Button(buttons, text='Choose folder…', command=browse_folder).pack(side='left')
        target_box = ttk.Combobox(buttons, values=list(workflow.NAMES), state='readonly', width=10)
        target_box.set('ide')
        target_box.pack(side='left', padx=(10, 4))
        ttk.Button(buttons, text='Choose file…', command=browse_file).pack(side='left')
        ttk.Button(buttons, text='Continue', command=accept).pack(side='right')
        ttk.Button(buttons, text='Cancel', command=cancel).pack(side='right', padx=6)
        window.protocol('WM_DELETE_WINDOW', cancel)
        window.update_idletasks()
        window.minsize(max(740, window.winfo_reqwidth()), max(500, window.winfo_reqheight() + 16))

    def completed(self, result):
        self.apps = result['apps']
        self.results.delete(*self.results.get_children())
        labels = {'patched': 'Active', 'unpatched': 'Original', 'unknown': 'Unsupported / ambiguous', 'error': 'Unavailable'}
        for app in self.apps:
            self.results.insert('', 'end', values=(app['name'], labels.get(app['state'], app['state'])))
        self.result_area.pack(fill='x', before=self.footer)
        self.fit_window()
        if result['ok']:
            self.status.set('Verified')
            self.status_label.configure(style='Status.TLabel')
            self.heading.set('Active' if self.action == 'patch' else 'Originals restored')
            self.description.set('All selected components were verified. You can now reopen Antigravity.')
        else:
            self.status.set('Needs attention')
            self.status_label.configure(style='Attention.Status.TLabel')
            self.heading.set('Some components need attention')
            self.description.set('Some components could not be completed. Verified results are shown below; '
                                 'close Antigravity, check access permissions, or select another supported installation and retry.')
            self.report = result['report']
            self.show_report()

    def restore(self):
        if not self.busy and messagebox.askokcancel('Restore originals',
                'Close Antigravity first. Restore selected components from verified original backups?', parent=self.root):
            self.start('restore')

    def choose_folder(self):
        if self.busy:
            return
        folder = filedialog.askdirectory(parent=self.root, title='Choose Antigravity installation folder')
        if folder:
            self.folder = folder
            self.description.set('Location added for this session. Click Activate to inspect and activate it.')

    def show_report(self):
        if not self.report:
            messagebox.showinfo(APP_NAME, 'No error report is available.', parent=self.root)
            return
        window = tk.Toplevel(self.root)
        window.title('Operation report')
        window.geometry('650x480')
        window.transient(self.root)
        frame = ttk.Frame(window, padding=18)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Copy this report for support. It contains no account data or personal paths.',
                  wraplength=610).pack(anchor='w', pady=(0, 12))
        text = tk.Text(frame, wrap='word', font=('Consolas', 10))
        text.insert('1.0', self.report)
        text.configure(state='disabled')
        text.pack(fill='both', expand=True)
        def copy():
            self.root.clipboard_clear()
            self.root.clipboard_append(text.get('1.0', 'end-1c'))
            copied.configure(text='Copied')
        copied = ttk.Button(frame, text='Copy report', command=copy)
        copied.pack(side='left', pady=(12, 0))
        ttk.Button(frame, text='Close', command=window.destroy).pack(side='right', pady=(12, 0))

    def callback_error(self, exception_type, exception, traceback):
        self.report = error_report('interface', self.apps, exception=exception)
        self.show_report()

    def close(self):
        if self.busy:
            messagebox.showinfo(APP_NAME, 'Wait for the operation to finish before closing.', parent=self.root)
        else:
            self.root.destroy()


class InstanceLock:
    """OS-released lock; retain the legacy mutex name for upgrade compatibility."""
    def __init__(self):
        self.handle, self.stream = None, None

    def acquire(self):
        if os.name == 'nt':
            import ctypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
            kernel.CreateMutexW.restype = ctypes.c_void_p
            self.handle = kernel.CreateMutexW(None, False, 'Local\\QNIXDev.AntigravityDesktop.Instance')
            code = ctypes.get_last_error()
            if not self.handle:
                raise ctypes.WinError(code)
            return code != 183
        import fcntl
        folder = Path.home() / '.cache' / 'antigravity-desktop'
        folder.mkdir(parents=True, exist_ok=True)
        self.stream = open(folder / 'desktop.lock', 'a')
        try:
            fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False

    def close(self):
        if self.handle:
            import ctypes
            close = ctypes.windll.kernel32.CloseHandle
            close.argtypes = [ctypes.c_void_p]
            close(self.handle)
            self.handle = None
        if self.stream:
            self.stream.close()
            self.stream = None


def main():
    lock = InstanceLock()
    try:
        if not lock.acquire():
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(APP_NAME, 'Antigravity Desktop is already open. Use the existing window.', parent=root)
            root.destroy()
            return 0
        if os.name == 'nt':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
            ctypes.windll.user32.SetProcessDPIAware()
        root = tk.Tk()
        Desktop(root)
        root.mainloop()
        return 0
    finally:
        lock.close()


if __name__ == '__main__':
    raise SystemExit(main())
