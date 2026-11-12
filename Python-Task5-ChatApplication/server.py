"""Chat server: accepts multiple clients, relays timestamped messages, and
announces joins and disconnects."""

import socket
import threading
from datetime import datetime

HOST = "127.0.0.1"
PORT = 5000

clients = {}  # socket -> username
clients_lock = threading.Lock()


def timestamp():
    return datetime.now().strftime("%H:%M")


def broadcast(message, sender=None):
    """Send a message to every connected client except the sender."""
    with clients_lock:
        targets = [c for c in clients if c is not sender]
    for conn in targets:
        try:
            conn.sendall(message.encode("utf-8"))
        except OSError:
            remove_client(conn)


def remove_client(conn):
    with clients_lock:
        name = clients.pop(conn, None)
    try:
        conn.close()
    except OSError:
        pass
    if name:
        broadcast(f"[{timestamp()}] * {name} has left the chat\n")
        print(f"[server] {name} disconnected")


def handle_client(conn, addr):
    try:
        name = conn.recv(1024).decode("utf-8").strip() or f"{addr[0]}:{addr[1]}"
        with clients_lock:
            clients[conn] = name
        print(f"[server] {name} joined from {addr}")
        broadcast(f"[{timestamp()}] * {name} has joined the chat\n")

        while True:
            data = conn.recv(1024)
            if not data:
                break
            text = data.decode("utf-8").strip()
            if text:
                line = f"[{timestamp()}] {name}: {text}\n"
                print(line, end="")
                broadcast(line, sender=conn)
    except (ConnectionResetError, OSError):
        pass
    finally:
        remove_client(conn)


def main():
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
