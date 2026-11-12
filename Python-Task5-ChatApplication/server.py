"""Chat server with accounts, rooms and stored message history.

Start it first:  python server.py
Protocol details are in protocol.py.
"""

import re
import socket
import threading
from datetime import datetime

import db
from protocol import LineReader, send

HOST = "127.0.0.1"
PORT = 5000
DEFAULT_ROOM = "general"
MAX_MESSAGE_LENGTH = 500
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
ROOM_PATTERN = re.compile(r"^[a-z0-9_-]{1,30}$")
EMOJI = {
    ":smile:": "😄",
    ":laughing:": "😂",
    ":thumbsup:": "👍",
    ":heart:": "❤️",
    ":fire:": "🔥",
    ":rocket:": "🚀",
}

# RLock so a handler can hold the lock and still call broadcast().
lock = threading.RLock()
sessions = {}  # conn -> {"user": str or None, "room": str or None}


def now():
    return datetime.now().strftime("%H:%M")


def expand_emoji(text):
    for code, emoji in EMOJI.items():
        text = text.replace(code, emoji)
    return text


def send_to(conn, obj):
    with lock:
        try:
            send(conn, obj)
        except OSError:
            pass


def get_session(conn):
    with lock:
        return dict(sessions[conn])


def broadcast(room, obj):
    with lock:
        for conn, session in list(sessions.items()):
            if session["room"] == room:
                send_to(conn, obj)


def join_room(conn, room):
    with lock:
        session = sessions[conn]
        previous, user = session["room"], session["user"]
        if previous and previous != room:
            broadcast(previous, {"type": "system", "text": f"{user} left #{previous}"})
        session["room"] = room
        send_to(conn, {"type": "ok", "event": "joined", "room": room, "msg": f"Joined #{room}"})
        for row in db.recent_messages(room):
            send_to(conn, {
                "type": "msg",
                "user": row["username"],
                "text": row["text"],
                "time": row["created_at"][11:16],
                "history": True,
            })
        broadcast(room, {"type": "system", "text": f"{user} joined #{room}"})


def do_auth(conn, cmd, msg):
    if get_session(conn)["user"]:
        return send_to(conn, {"type": "error", "event": "login", "msg": "You are already logged in"})

    username = str(msg.get("username", "")).strip()
    password = str(msg.get("password", ""))
    error = None
    if cmd == "register":
        if not USERNAME_PATTERN.match(username):
            error = "Usernames use 3-20 letters, numbers or underscores"
        elif len(password) < 8 or not any(ch.isdigit() for ch in password):
            error = "Password must be at least 8 characters and include a number"
        elif not db.create_user(username, password):
            error = "That username is taken"
    elif not db.check_login(username, password):
        # Same message for wrong username and wrong password, so it doesn't reveal which was wrong.
        error = "Invalid username or password"

    if error:
        return send_to(conn, {"type": "error", "event": "login", "msg": error})

    with lock:
        sessions[conn]["user"] = username
    send_to(conn, {"type": "ok", "event": "login", "msg": f"Welcome, {username}!"})
    join_room(conn, DEFAULT_ROOM)


def say(conn, text):
    session = get_session(conn)
    text = expand_emoji(text.strip())[:MAX_MESSAGE_LENGTH]
    if not text:
        return
    db.save_message(session["room"], session["user"], text)
    broadcast(session["room"], {
        "type": "msg",
        "user": session["user"],
        "text": text,
        "time": now(),
        "history": False,
    })


def handle(conn, msg):
    """Process one command. Returns "quit" when the client asks to leave."""
    cmd = msg.get("cmd")
    if cmd in ("register", "login"):
        do_auth(conn, cmd, msg)
        return None
    if cmd == "quit":
        return "quit"

    if not get_session(conn)["user"]:
        send_to(conn, {"type": "error", "event": "auth", "msg": "Log in first"})
        return None

    if cmd == "rooms":
        names = ", ".join(db.list_rooms()) or "none yet"
        send_to(conn, {"type": "ok", "event": "rooms", "msg": f"Rooms: {names}"})
    elif cmd == "join":
        room = str(msg.get("room", "")).strip().lower()
        if ROOM_PATTERN.match(room):
            join_room(conn, room)
        else:
            send_to(conn, {"type": "error", "event": "join",
                           "msg": "Room names use 1-30 letters, numbers, - or _"})
    elif cmd == "say":
        say(conn, str(msg.get("text", "")))
    else:
        send_to(conn, {"type": "error", "event": "command", "msg": "Unknown command"})
    return None


def leave(conn):
    with lock:
        session = sessions.pop(conn, None)
    if session and session["user"] and session["room"]:
        broadcast(session["room"], {"type": "system",
                                    "text": f"{session['user']} left #{session['room']}"})


def handle_client(conn, addr):
    with lock:
        sessions[conn] = {"user": None, "room": None}
    reader = LineReader(conn)
    try:
        while True:
            msg = reader.read()
            if msg is None or handle(conn, msg) == "quit":
                break
    except (OSError, ValueError, AttributeError):
        pass
    finally:
        leave(conn)
        conn.close()
        print(f"[server] connection closed from {addr}")


def main():
    db.init_db()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[server] listening on {HOST}:{PORT}")
    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[server] shutting down")
    finally:
        server.close()


if __name__ == "__main__":
    main()
