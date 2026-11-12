"""Shared wire format. Every message is one JSON object followed by a newline.

Client -> server commands:
    {"cmd": "register", "username": ..., "password": ...}
    {"cmd": "login", "username": ..., "password": ...}
    {"cmd": "join", "room": ...}
    {"cmd": "say", "text": ...}
    {"cmd": "rooms"}
    {"cmd": "quit"}

Server -> client events:
    {"type": "ok", "event": "login" | "joined" | "rooms", "msg": ...}
    {"type": "error", "event": ..., "msg": ...}
    {"type": "msg", "user": ..., "text": ..., "time": "HH:MM", "history": bool}
    {"type": "system", "text": ...}
"""

import json


def send(sock, obj):
    sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))


class LineReader:
    """Reads newline-separated JSON objects from a socket."""

    def __init__(self, sock):
        self.sock = sock
        self.buffer = b""

    def read(self):
        """Return the next message as a dict, or None once the connection closes."""
        while b"\n" not in self.buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                return None
            self.buffer += chunk
        line, self.buffer = self.buffer.split(b"\n", 1)
        return json.loads(line.decode("utf-8"))


def render(obj):
    """Turn an event into a line of text for display."""
    kind = obj.get("type")
    if kind == "msg":
        suffix = " (earlier)" if obj.get("history") else ""
        return f"[{obj['time']}] {obj['user']}: {obj['text']}{suffix}"
    if kind == "system":
        return f"* {obj['text']}"
    if kind == "error":
        return f"! {obj['msg']}"
    if kind == "ok":
        return obj.get("msg", "")
    return str(obj)
