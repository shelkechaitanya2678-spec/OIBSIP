# Chat Application (Python, Advanced Tier)

Part of the Oasis Infobyte internship, Python track, Task 5.

## Status

- [x] Socket server that accepts multiple clients (`server.py`)
- [x] Client that connects and exchanges messages in real time (`client.py`)
- [x] Timestamped messages (`[HH:MM] Name: text`)
- [x] Join and disconnect notifications
- [ ] Graphical interface (tkinter or Flask)
- [ ] User registration and login stored in SQLite
- [ ] Multiple chat rooms (create and join)
- [ ] Message history loaded on join (SQLite)
- [ ] New-message notifications when the window is unfocused
- [ ] Emoji shortcode rendering (for example `:smile:`)
- [ ] Storage and encryption documentation (below)

## Running it

Open two terminals in this folder.

```bash
python server.py
python client.py   # run in each terminal, one per user
```

Type a message and press Enter. Type `/quit` to leave.

## Design notes

- The server uses one thread per client. A lock protects the shared client list.
- Messages are plain UTF-8 lines sent over TCP. Each client gets a copy of every message except its own.
- The server binds to `127.0.0.1` only, so the chat is reachable from this machine alone.

## Storage and security (to be completed)

This section will describe how messages and accounts are stored once SQLite is added, and what is not encrypted. The current version stores nothing and sends everything in plain text over localhost.

## Ethics and privacy

Run this on your own machine or network. Do not use it to intercept or read other people's traffic.
