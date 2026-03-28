import tkinter as tk
from tkinter import messagebox
import json
import os
import time
import hashlib
import qrcode
from PIL import Image, ImageTk

# ---------------- CONFIG ----------------

CHAIN_FILE = "bc7_chain_node1.json"
DIFFICULTY = 2
OWNER = "1454d2717559abd53c81fb39d2d1e7bf24c6842301e8e4b99439cee68fe9ba1e"
CURRENCY = "Global Currency (GC)"

blockchain = []

# ---------------- LOAD CHAIN ----------------

def load_chain():
    global blockchain
    if os.path.exists(CHAIN_FILE):
        with open(CHAIN_FILE, "r") as f:
            blockchain = json.load(f)
    else:
        blockchain = []

# ---------------- SAVE ----------------

def save_chain():
    with open(CHAIN_FILE, "w") as f:
        json.dump(blockchain, f, indent=4)

# ---------------- HASH ----------------

def hash_block(block):
    return hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()

# ---------------- GENESIS ----------------

def create_genesis():
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

def mine_block(block):
    block["nonce"] = 0
    hash_val = hash_block(block)

    while not hash_val.startswith("0" * DIFFICULTY):
        block["nonce"] += 1
        hash_val = hash_block(block)

    return hash_val

# ---------------- ADD BLOCK ----------------

def add_block(tx):
    last = blockchain[-1]

    block = {
        "index": len(blockchain),
        "timestamp": time.time(),
        "transactions": [tx],
        "previous_hash": last["hash"],
        "nonce": 0
    }

    block["hash"] = mine_block(block)

    blockchain.append(block)
    save_chain()

# ---------------- SEND ----------------

def send():
    receiver = receiver_entry.get().strip()
    amount = amount_entry.get().strip()

    if receiver == "" or amount == "":
        messagebox.showerror("Error", "Enter receiver & amount")
        return

    if receiver == OWNER:
        messagebox.showerror("Error", "Sender and Receiver cannot be same.\nTransaction Aborted!")
        return

    try:
        amount = int(amount)
    except:
        messagebox.showerror("Error", "Invalid amount")
        return

    if amount <= 0:
        messagebox.showerror("Error", "Amount must be greater than 0")
        return

    if get_balance(OWNER) < amount:
        messagebox.showerror("Error", "Insufficient balance")
        return

    tx = {
        "sender": OWNER,
        "receiver": receiver,
        "amount": amount
    }

    add_block(tx)
    update_balance()

    receiver_entry.delete(0, tk.END)
    amount_entry.delete(0, tk.END)

    messagebox.showinfo("Success", "Transaction Sent Successfully")

# ---------------- COPY OWNER ----------------

def copy_owner():
    root.clipboard_clear()
    root.clipboard_append(OWNER)
    messagebox.showinfo("Copied", "Owner address copied")

# ---------------- PASTE RECEIVER ----------------

def paste_receiver():
    try:
        data = root.clipboard_get()
        receiver_entry.delete(0, tk.END)
        receiver_entry.insert(0, data)
        update_qr(data)
    except:
        messagebox.showerror("Error", "Clipboard empty")

# ---------------- QR UPDATE ----------------

def update_qr(data=None):
    if not data:
        data = OWNER

    qr = qrcode.make(data)
    img = qr.resize((120, 120))
    img = ImageTk.PhotoImage(img)

    qr_label.config(image=img)
    qr_label.image = img

# ---------------- UPDATE BALANCE ----------------

def update_balance():
    bal = get_balance(OWNER)
    balance_label.config(text=f"{bal:,} GC")

# ---------------- INIT ----------------

load_chain()
create_genesis()

# ---------------- GUI ----------------

root = tk.Tk()
root.title("Crypto Wallet")
root.geometry("420x550")
root.configure(bg="#ffc0cb")

# ---------------- CURRENCY ----------------

tk.Label(
    root,
    text=CURRENCY,
    font=("Arial", 16, "bold"),
    bg="#ffc0cb"
).pack(pady=5)

# ---------------- BALANCE ----------------

balance_label = tk.Label(
    root,
    text="0 GC",
    font=("Arial", 22, "bold"),
    bg="#ffc0cb"
)
balance_label.pack(pady=10)

update_balance()

# ---------------- SEND ----------------

tk.Label(root, text="Receiver", bg="#ffc0cb").pack()
receiver_entry = tk.Entry(root, width=30)
receiver_entry.pack(pady=5)

tk.Button(root, text="Paste", command=paste_receiver).pack(pady=2)

tk.Label(root, text="Amount", bg="#ffc0cb").pack()
amount_entry = tk.Entry(root, width=30)
amount_entry.pack(pady=5)

tk.Button(root, text="Send", bg="green", fg="white", width=20, command=send).pack(pady=10)

# ---------------- QR SECTION ----------------

tk.Label(root, text="Your Wallet QR", bg="#ffc0cb", font=("Arial", 12, "bold")).pack(pady=5)

qr_label = tk.Label(root, bg="#ffc0cb")
qr_label.pack()

update_qr()

tk.Label(root, text="Owner Address", bg="#ffc0cb").pack(pady=5)

tk.Label(root, text=OWNER, wraplength=350, bg="#ffc0cb").pack()

tk.Button(root, text="Copy Address", command=copy_owner).pack(pady=5)

root.mainloop()