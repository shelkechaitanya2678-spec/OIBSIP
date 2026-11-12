"""Chat client: connects to the server, sends typed messages, and prints
incoming messages as they arrive."""

import socket
import sys
import threading

HOST = "127.0.0.1"
PORT = 5000


def receive(sock):
    """Print anything the server sends until the connection closes."""
    try:
        while True:
            data = sock.recv(1024)
            if not data:
                print("\n[client] server closed the connection")
                break
            print(data.decode("utf-8"), end="")
    except OSError:
        print("\n[client] lost connection to server")
    finally:
        sock.close()


def main():
    name = input("Enter your name: ").strip() or "anonymous"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
    except ConnectionRefusedError:
        sys.exit("Could not connect. Is server.py running?")

    sock.sendall(name.encode("utf-8"))
    threading.Thread(target=receive, args=(sock,), daemon=True).start()

    try:
        while True:
            text = input()
            if text.lower() in ("/quit", "/exit"):
                break
            if text.strip():
                sock.sendall(text.encode("utf-8"))
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        sock.close()
        print("[client] disconnected")


if __name__ == "__main__":
    main()
