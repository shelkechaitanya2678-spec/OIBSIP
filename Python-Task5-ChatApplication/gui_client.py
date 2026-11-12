"""Tkinter chat client. Connects to server.py and shows messages in a window.

Run server.py first, then:  python gui_client.py
"""

import queue
import socket
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext

HOST = "127.0.0.1"
PORT = 5000


class ChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat")
        self.root.geometry("460x520")
        self.incoming = queue.Queue()
        self.sock = None

        self.log = scrolledtext.ScrolledText(root, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=8, pady=(8, 4))
        self.log.tag_config("system", foreground="gray")

        bottom = tk.Frame(root)
        bottom.pack(fill="x", padx=8, pady=(0, 8))
        self.entry = tk.Entry(bottom)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda _e: self.send())
        self.send_btn = tk.Button(bottom, text="Send", command=self.send, width=8)
        self.send_btn.pack(side="right", padx=(6, 0))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.poll_incoming)
        self.root.after(100, self.connect)

    def connect(self):
        name = simpledialog.askstring("Name", "Enter your name:", parent=self.root)
        if not name or not name.strip():
            name = "anonymous"
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))
        except OSError:
            messagebox.showerror("Connection failed", "Could not reach the server. Is server.py running?")
            self.root.destroy()
            return
        self.sock.sendall(name.strip().encode("utf-8"))
        self.append("Connected to chat.", system=True)
        threading.Thread(target=self.receive, daemon=True).start()

    def receive(self):
        """Runs in a background thread. Hands data to the UI via a queue."""
        try:
            while True:
                data = self.sock.recv(1024)
                if not data:
                    self.incoming.put(("[Disconnected from server]\n", True))
                    break
                self.incoming.put((data.decode("utf-8"), False))
        except OSError:
            self.incoming.put(("[Lost connection to server]\n", True))

    def poll_incoming(self):
        """Runs on the Tk main thread. Drains the queue into the log."""
        try:
            while True:
                text, is_system = self.incoming.get_nowait()
                self.append(text, system=is_system)
        except queue.Empty:
            pass
        self.root.after(100, self.poll_incoming)

    def send(self):
        text = self.entry.get().strip()
        if not text or self.sock is None:
            return
        try:
            self.sock.sendall(text.encode("utf-8"))
        except OSError:
            self.append("[Could not send message]", system=True)
            return
        self.entry.delete(0, "end")

    def append(self, text, system=False):
        self.log.config(state="normal")
        self.log.insert("end", text if text.endswith("\n") else text + "\n",
                        "system" if system else ())
        self.log.see("end")
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
