"""Terminal chat client. Start server.py first, then run this in each terminal."""

import getpass
import os
import socket
import sys
import threading

from protocol import LineReader, render, send

HOST = "127.0.0.1"
PORT = 5000
HELP = "Commands: /join <room>   /rooms   /quit"


def listen(reader):
    """Print every event from the server. Exit if the connection drops or login fails."""
    while True:
        try:
            msg = reader.read()
        except (OSError, ValueError):
            msg = None
        if msg is None:
            print("\n[disconnected from server]", flush=True)
            os._exit(0)
        print(render(msg), flush=True)
        if msg.get("type") == "error" and msg.get("event") == "login":
            os._exit(1)


def main():
    try:
        sock = socket.create_connection((HOST, PORT))
    except OSError:
        sys.exit("Could not connect. Is server.py running?")

    reader = LineReader(sock)
    threading.Thread(target=listen, args=(reader,), daemon=True).start()

    choice = input("1) Log in   2) Register\n> ").strip()
    cmd = "register" if choice == "2" else "login"
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    send(sock, {"cmd": cmd, "username": username, "password": password})
    print(HELP)

    try:
        while True:
            line = input().strip()
            if not line:
                continue
            if line == "/quit":
                send(sock, {"cmd": "quit"})
                break
            if line == "/rooms":
                send(sock, {"cmd": "rooms"})
            elif line.startswith("/join "):
                send(sock, {"cmd": "join", "room": line[len("/join "):]})
            else:
                send(sock, {"cmd": "say", "text": line})
    except (EOFError, KeyboardInterrupt, OSError):
        pass
    finally:
        sock.close()


if __name__ == "__main__":
    main()
