"""Tkinter chat client with accounts, rooms, history and notifications.

Start server.py first, then run:  python gui_client.py
"""

import queue
import socket
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from protocol import LineReader, render, send

HOST = "127.0.0.1"
PORT = 5000


class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat")
        self.root.geometry("520x560")
        self.root.withdraw()  # hidden until the user logs in

        self.incoming = queue.Queue()
        self.sock = None
        self.reader = None
        self.login_dialog = None

        self.build_main_window()
        self.root.bind("<FocusIn>", lambda _e: self.root.title("Chat"))
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.poll)
        self.connect()

    # ----- layout ---------------------------------------------------------

    def build_main_window(self):
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=8, pady=(8, 0))
        self.room_label = tk.Label(top, text="Room: -", anchor="w")
        self.room_label.pack(side="left")
        tk.Button(top, text="Rooms", command=lambda: self.send_obj({"cmd": "rooms"})).pack(side="right")
        self.room_entry = tk.Entry(top, width=14)
        self.room_entry.pack(side="right", padx=4)
        self.room_entry.bind("<Return>", lambda _e: self.join_room())
        tk.Button(top, text="Join", command=self.join_room).pack(side="right")

        self.log = scrolledtext.ScrolledText(self.root, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=8, pady=8)
        self.log.tag_config("system", foreground="gray")

        bottom = tk.Frame(self.root)
        bottom.pack(fill="x", padx=8, pady=(0, 8))
        self.entry = tk.Entry(bottom)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda _e: self.send_text())
        tk.Button(bottom, text="Send", command=self.send_text, width=8).pack(side="right", padx=(6, 0))

    def show_login(self):
        d = tk.Toplevel(self.root)
        d.title("Log in")
        d.resizable(False, False)
        d.protocol("WM_DELETE_WINDOW", self.on_close)
        self.login_dialog = d

        tk.Label(d, text="Username").grid(row=0, column=0, sticky="w", padx=10, pady=(12, 0))
        self.user_entry = tk.Entry(d, width=24)
        self.user_entry.grid(row=0, column=1, padx=10, pady=(12, 0))
        tk.Label(d, text="Password").grid(row=1, column=0, sticky="w", padx=10, pady=6)
        self.pass_entry = tk.Entry(d, show="*", width=24)
        self.pass_entry.grid(row=1, column=1, padx=10, pady=6)
        self.pass_entry.bind("<Return>", lambda _e: self.submit_auth("login"))

        buttons = tk.Frame(d)
        buttons.grid(row=2, column=0, columnspan=2, pady=6)
        tk.Button(buttons, text="Log in", width=10, command=lambda: self.submit_auth("login")).pack(side="left", padx=4)
        tk.Button(buttons, text="Register", width=10, command=lambda: self.submit_auth("register")).pack(side="left", padx=4)

        self.dialog_msg = tk.Label(d, text="", fg="red", wraplength=260)
        self.dialog_msg.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 10))
        self.user_entry.focus_set()

    # ----- networking -----------------------------------------------------

    def connect(self):
        try:
            self.sock = socket.create_connection((HOST, PORT))
        except OSError:
            messagebox.showerror("Connection failed", "Could not reach the server. Is server.py running?")
            self.root.destroy()
            return
        self.reader = LineReader(self.sock)
        threading.Thread(target=self.listen, daemon=True).start()
        self.show_login()

    def listen(self):
        """Background thread: read events and pass them to the UI through a queue."""
        while True:
            try:
                msg = self.reader.read()
            except (OSError, ValueError):
                msg = None
            if msg is None:
                self.incoming.put({"type": "system", "text": "Disconnected from server"})
                break
            self.incoming.put(msg)

    def send_obj(self, obj):
        try:
            send(self.sock, obj)
        except OSError:
            self.append("Could not send. The connection may be closed.", system=True)

    # ----- actions --------------------------------------------------------

    def submit_auth(self, cmd):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get()
        if not username or not password:
            self.dialog_msg.config(text="Enter a username and password")
            return
        self.dialog_msg.config(text="")
        self.send_obj({"cmd": cmd, "username": username, "password": password})

    def join_room(self):
        room = self.room_entry.get().strip().lower()
        if room:
            self.send_obj({"cmd": "join", "room": room})
            self.room_entry.delete(0, "end")

    def send_text(self):
        text = self.entry.get().strip()
        if text:
            self.send_obj({"cmd": "say", "text": text})
            self.entry.delete(0, "end")

    # ----- incoming events ------------------------------------------------

    def poll(self):
        """Runs on the Tk thread. Applies queued events to the window."""
        try:
            while True:
                self.handle_event(self.incoming.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def handle_event(self, msg):
        kind, event = msg.get("type"), msg.get("event")

        if kind == "ok" and event == "login":
            if self.login_dialog:
                self.login_dialog.destroy()
                self.login_dialog = None
            self.root.deiconify()
            self.entry.focus_set()
        elif kind == "error" and event == "login":
            if self.login_dialog:
                self.dialog_msg.config(text=msg["msg"])
            else:
                self.append(render(msg), system=True)
        elif kind == "ok" and event == "joined":
            self.clear_log()
            self.room_label.config(text=f"Room: #{msg['room']}")
            self.append(render(msg), system=True)
        elif kind == "msg":
            self.append(render(msg))
            self.notify()
        else:
            self.append(render(msg), system=True)

    def notify(self):
        """Flash the title and beep if a message arrives while the window isn't focused."""
        if self.root.focus_displayof() is None:
            self.root.title("(new message) Chat")
            self.root.bell()

    # ----- log helpers ----------------------------------------------------

    def append(self, text, system=False):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n", "system" if system else ())
        self.log.see("end")
        self.log.config(state="disabled")

    def clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")

    def on_close(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    ChatGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
