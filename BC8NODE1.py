# ---------------- SAFE TKINTER IMPORT ----------------
try:
    import tkinter as tk
    from tkinter import messagebox, ttk
    GUI_AVAILABLE = True
except:
    GUI_AVAILABLE = False

import hashlib
import json
import time
import os
import threading
import requests
from flask import Flask, request, jsonify

# ---------------- NODE CONFIG ----------------
PORT = int(os.environ.get("PORT", 5000))

PEER_NODES = []

CHAIN_FILE = "bc7_chain_node1.json"
CONTACT_FILE = "contacts.json"

DIFFICULTY = 3
MASTER_PRIVATE_KEY = "1234"

blockchain = []
contacts = {}

# ---------------- HASH ----------------
def hash_block(block):
    block_string = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()

# ---------------- LOAD ----------------
def load_chain():
    global blockchain
    if os.path.exists(CHAIN_FILE):
        with open(CHAIN_FILE, "r") as f:
            blockchain = json.load(f)

def save_chain():
    with open(CHAIN_FILE, "w") as f:
        json.dump(blockchain, f, indent=4)

# ---------------- GENESIS ----------------
def create_genesis_block():
    if len(blockchain) == 0:
        block = {
            "index": 0,
            "timestamp": time.time(),
            "transactions": ["Genesis"],
            "previous_hash": "0",
            "nonce": 0
        }
        block["hash"] = hash_block(block)
        blockchain.append(block)
        save_chain()

# ---------------- BALANCE ----------------
def get_balance(name):
    balance = 0
    for block in blockchain:
        for tx in block["transactions"]:
            if isinstance(tx, dict):
                if tx["sender"] == name:
                    balance -= tx["amount"]
                if tx["receiver"] == name:
                    balance += tx["amount"]
    return max(balance, 0)

# ---------------- POW ----------------
def proof_of_work(block):
    block["nonce"] = 0
    while True:
        hash_val = hash_block(block)
        if hash_val.startswith("0" * DIFFICULTY):
            return hash_val
        block["nonce"] += 1

# ---------------- BLOCK ----------------
def create_block(transactions):
    last_block = blockchain[-1]
    block = {
        "index": len(blockchain),
        "timestamp": time.time(),
        "transactions": transactions,
        "previous_hash": last_block["hash"],
        "nonce": 0
    }
    block["hash"] = proof_of_work(block)
    blockchain.append(block)
    save_chain()
    broadcast_block(block)

# ---------------- NETWORK ----------------
def broadcast_block(block):
    for node in PEER_NODES:
        try:
            requests.post(node + "/receive_block", json=block, timeout=3)
        except:
            pass

def sync_chain():
    global blockchain
    for node in PEER_NODES:
        try:
            r = requests.get(node + "/chain", timeout=3)
            chain = r.json()
            if len(chain) > len(blockchain):
                blockchain = chain
                save_chain()
        except:
            pass

# ---------------- SERVER ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "BC8 Blockchain Node Running"

@app.route("/chain", methods=["GET"])
def get_chain():
    return jsonify(blockchain)

@app.route("/receive_block", methods=["POST"])
def receive_block():
    block = request.json
    if block["index"] != len(blockchain):
        return "Rejected", 400
    if not block["hash"].startswith("0" * DIFFICULTY):
        return "Invalid", 400
    blockchain.append(block)
    save_chain()
    return "OK", 200

def start_server():
    app.run(host="0.0.0.0", port=PORT)

# ---------------- TRANSACTION ----------------
def add_transaction(sender, receiver, amount, key):
    if key != MASTER_PRIVATE_KEY:
        return "Invalid Key"
    if get_balance(sender) < amount:
        return "Low Balance"
    tx = {
        "sender": sender,
        "receiver": receiver,
        "amount": amount
    }
    create_block([tx])
    return "Success"

# ---------------- INIT ----------------
load_chain()
create_genesis_block()

threading.Thread(target=start_server, daemon=True).start()

# ---------------- GUI ----------------
if GUI_AVAILABLE:
    root = tk.Tk()
    root.title("BC8 Node")
    root.geometry("400x400")

    tk.Label(root, text="Sender").pack()
    sender = tk.Entry(root)
    sender.pack()

    tk.Label(root, text="Receiver").pack()
    receiver = tk.Entry(root)
    receiver.pack()

    tk.Label(root, text="Amount").pack()
    amount = tk.Entry(root)
    amount.pack()

    tk.Label(root, text="Key").pack()
    key = tk.Entry(root)
    key.pack()

    def send_tx():
        try:
            amt = int(amount.get())
        except:
            messagebox.showerror("Error", "Invalid amount")
            return

        res = add_transaction(
            sender.get(),
            receiver.get(),
            amt,
            key.get()
        )
        messagebox.showinfo("Result", res)

    tk.Button(root, text="Send", command=send_tx).pack()

    root.mainloop()
