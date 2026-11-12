# Chat Application (Python, Advanced Tier)

Part of the Oasis Infobyte internship, Python track, Task 5.

## Features

- Accounts: register and log in. Passwords are hashed with PBKDF2-SHA256 and a per-user salt.
- Rooms: join any room by name. Rooms are created on first use.
- Message history: the last 50 messages in a room are sent when you join it.
- Real-time chat between any number of clients, with timestamps and join/leave notices.
- Emoji shortcodes such as `:smile:`, `:fire:` and `:rocket:` are converted to emoji.
- Notifications: the GUI flashes its title and beeps when a message arrives while the window is in the background.
- Two clients: a tkinter window (`gui_client.py`) and a terminal client (`client.py`).

## Files

| File | Purpose |
|---|---|
| `server.py` | Accepts connections, handles accounts, rooms and messages |
| `db.py` | SQLite storage: users, rooms, messages, and password hashing |
| `protocol.py` | Message format shared by the server and both clients |
| `gui_client.py` | tkinter window client |
| `client.py` | Terminal client |

## Running it

Open a terminal for the server and one for each user. All commands run from this folder.

```bash
python server.py        # start first; creates chat.db on first run
python gui_client.py    # window client, one per user
python client.py        # or the terminal client
```

The GUI shows a login window. Choose **Register** to create an account, or **Log in** if you already have one. Use the room box and **Join** to switch rooms.

Terminal client commands:

- `/join <room>` switches rooms
- `/rooms` lists rooms
- `/quit` leaves

Passwords must be at least 8 characters and include a number. Usernames are 3 to 20 letters, numbers, or underscores.

## Protocol

Messages are one JSON object per line over TCP. `protocol.py` documents each command and event. The server sends the same events to every client, so a new client can be added without changing the server.

## Storage and security

**Stored in `chat.db` (SQLite, in this folder):**

- `users`: username, a random 16-byte salt, and the PBKDF2-SHA256 hash of the password (200,000 iterations). Passwords are never stored.
- `rooms`: room names.
- `messages`: room, sender, text, and timestamp.

Usernames are case-insensitive, so `Alice` and `alice` are the same account.

**Not encrypted:**

- Messages are stored as plain text in `chat.db`. Anyone with access to the file can read every message.
- Traffic between the clients and the server is plain text over TCP. The server listens on `127.0.0.1` only, so the traffic stays on this machine. It is still unencrypted, so it would be readable by other software on the same machine.
- There is no TLS and no end-to-end encryption. Only the passwords are protected, by hashing.
- Login has no rate limiting, so it doesn't protect against password guessing.

For real use, you'd need TLS on the connection, encryption at rest for messages, and rate limiting on login.

## Ethics and privacy

Run this on your own machine or network. Do not use it to intercept or read other people's traffic.
