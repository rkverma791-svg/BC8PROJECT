#import tkinter as tk
#from tkinter import messagebox, ttk
#-chatgpt code --------------
try:
    import tkinter as tk
    from tkinter import messagebox, ttk
    GUI_AVAILABLE = True
except:
    GUI_AVAILABLE = False
    #-----------------
import hashlib
import json
import time
import os
import threading
import requests
from flask import Flask, request, jsonify

# ---------------- NODE CONFIG ----------------

NODE_IP = "192.0.0.8"
PORT = 5000

PEER_NODES = [
    "http://10.93.239.198:5000",
    "http://192.0.0.4:5000"
]

CHAIN_FILE = "bc7_chain_node1.json"
CONTACT_FILE = "contacts.json"

DIFFICULTY = 3
MAX_SUPPLY = 1000000000000
MASTER_PRIVATE_KEY = "1234"

blockchain = []
contacts = {}

# ---------------- CONTACTS ----------------

def load_contacts():
    global contacts
    if os.path.exists(CONTACT_FILE):
        with open(CONTACT_FILE, "r") as f:
            contacts = json.load(f)
    else:
        contacts = {}
        save_contacts()

def save_contacts():
    with open(CONTACT_FILE, "w") as f:
        json.dump(contacts, f, indent=4)

def refresh_contacts():
    contact_list = []
    for name, num in contacts.items():
        contact_list.append(f"{name} - {num}")
    contact_menu["values"] = contact_list

def contact_selected(event):
    selected = contact_menu.get()
    if "-" in selected:
        number = selected.split("-")[1].strip()
        receiver_entry.delete(0, tk.END)
        receiver_entry.insert(0, number)

def add_contact():
    name = contact_name_entry.get().strip()
    number = contact_number_entry.get().strip()

    if name == "" or number == "":
        messagebox.showerror("Error", "Enter name and number")
        return

    contacts[name] = number
    save_contacts()
    refresh_contacts()
    messagebox.showinfo("Success", "Contact added")

def delete_contact():
    selected = contact_menu.get()

    if "-" not in selected:
        messagebox.showerror("Error", "Select contact from list")
        return

    name = selected.split("-")[0].strip()

    if name in contacts:
        del contacts[name]
        save_contacts()
        refresh_contacts()
        messagebox.showinfo("Deleted", "Contact removed")

# ---------------- HASH ----------------

def hash_block(block):
    block_string = json.dumps(block, sort_keys=True).encode()
    return hashlib.sha256(block_string).hexdigest()

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

# ---------------- GENESIS ----------------

def create_genesis_block():
    if len(blockchain) == 0:
        block = {
            "index": 0,
            "timestamp": time.time(),
            "transactions": ["Genesis Block"],
            "previous_hash": "0",
            "nonce": 0
        }

        block["hash"] = hash_block(block)
        blockchain.append(block)
        save_chain()

# ---------------- BALANCE ----------------

def get_balance(name):
    if name == "ZERO":
        return 0

    balance = 0

    for block in blockchain:
        for tx in block["transactions"]:
            if isinstance(tx, dict):
                if tx["sender"] == name:
                    balance -= tx["amount"]

                if tx["receiver"] == name:
                    balance += tx["amount"]

    if balance < 0:
        balance = 0

    return int(balance)

# ---------------- SUPPLY ----------------

def supply_stats():

    minted = 0
    burned = 0

    for block in blockchain:
        for tx in block["transactions"]:

            if isinstance(tx, dict):

                if tx["sender"] == "SYSTEM":
                    minted += tx["amount"]

                if tx["receiver"] == "ZERO":
                    burned += tx["amount"]

    circulating = MAX_SUPPLY - burned
    remaining = MAX_SUPPLY - minted

    return minted, burned, circulating, remaining

# ---------------- POW ----------------

def proof_of_work(block):

    block["nonce"] = 0
    computed_hash = hash_block(block)

    while not computed_hash.startswith("0" * DIFFICULTY):
        block["nonce"] += 1
        computed_hash = hash_block(block)

    return computed_hash

# ---------------- CREATE BLOCK ----------------

def create_block(transactions):

    last_block = blockchain[-1]

    block = {
        "index": len(blockchain),
        "timestamp": time.time(),
        "transactions": transactions,
        "previous_hash": last_block["hash"],
        "nonce": 0
    }

    proof = proof_of_work(block)
    block["hash"] = proof

    blockchain.append(block)
    save_chain()

    broadcast_block(block)

# ---------------- BROADCAST ----------------

def broadcast_block(block):

    for node in PEER_NODES:

        try:

            if node == f"http://{NODE_IP}:{PORT}":
                continue

            requests.post(node + "/receive_block", json=block, timeout=3)

        except:
            pass

# ---------------- SYNC ----------------

def sync_chain():

    global blockchain

    for node in PEER_NODES:

        if node == f"http://{NODE_IP}:{PORT}":
            continue

        try:

            r = requests.get(node + "/chain", timeout=3)
            chain = r.json()

            if len(chain) > len(blockchain):
                blockchain = chain
                save_chain()

        except:
            pass


def auto_sync():

    while True:
        sync_chain()
        time.sleep(20)

# ---------------- SERVER ----------------

app = Flask(__name__)

@app.route("/chain", methods=["GET"])
def get_chain():
    return jsonify(blockchain)

@app.route("/receive_block", methods=["POST"])
def receive_block():

    block = request.json

    if block["index"] != len(blockchain):
        return "Rejected", 400

    if not block["hash"].startswith("0" * DIFFICULTY):
        return "Invalid POW", 400

    blockchain.append(block)
    save_chain()

    return "Block Added", 200


def start_server():
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

# ---------------- TRANSACTION ----------------

def add_transaction(btn):

    btn.config(state="disabled")

    sender = sender_entry.get().strip()
    receiver = receiver_entry.get().strip()
    amount = amount_entry.get().strip()
    key = private_entry.get().strip()

    if key != MASTER_PRIVATE_KEY:
        messagebox.showerror("Error", "Invalid Private Key")
        btn.config(state="normal")
        return

    try:
        amount = int(amount)
    except:
        messagebox.showerror("Error", "Invalid amount")
        btn.config(state="normal")
        return

    if sender != "SYSTEM":
        if get_balance(sender) < amount:
            messagebox.showerror("Error", "Insufficient Balance")
            btn.config(state="normal")
            return

    tx = {
        "sender": sender,
        "receiver": receiver,
        "amount": amount
    }

    create_block([tx])

    messagebox.showinfo("Success", "Block mined")

# ---------------- PASTE RECEIVER ----------------

def paste_receiver():
    try:
        receiver_entry.delete(0, tk.END)
        receiver_entry.insert(0, root.clipboard_get())
    except:
        pass

# ---------------- RESET ----------------

def reset_fields():

    sender_entry.delete(0, tk.END)
    receiver_entry.delete(0, tk.END)
    amount_entry.delete(0, tk.END)
    private_entry.delete(0, tk.END)
    balance_entry.delete(0, tk.END)
    contact_name_entry.delete(0, tk.END)
    contact_number_entry.delete(0, tk.END)

    text_box.delete(1.0, tk.END)

    contact_menu.set("")
    refresh_contacts()

    for widget in root.winfo_children():
        try:
            if isinstance(widget, tk.Button):
                widget.config(state="normal")
        except:
            pass

        if isinstance(widget, tk.Frame):
            for child in widget.winfo_children():
                try:
                    if isinstance(child, tk.Button):
                        child.config(state="normal")
                except:
                    pass

    sender_entry.focus_set()

# ---------------- VIEW CHAIN ----------------

def view_chain(btn):

    btn.config(state="disabled")

    text_box.delete(1.0, tk.END)

    for block in reversed(blockchain):

        text_box.insert(tk.END, json.dumps(block, indent=4))
        text_box.insert(tk.END, "\n\n")

# ---------------- BALANCE ----------------

def check_balance(btn):

    btn.config(state="disabled")

    name = balance_entry.get().strip()
    bal = get_balance(name)

    messagebox.showinfo("Balance", f"{name}\nBalance: {bal:,}")

# ---------------- STATS ----------------

def show_stats(btn):

    btn.config(state="disabled")

    minted, burned, circulating, remaining = supply_stats()

    messagebox.showinfo(
        "Network Stats",
        f"Blocks: {len(blockchain)}\n\n"
        f"Minted: {minted:,}\n"
        f"Burned: {burned:,}\n"
        f"Circulating: {circulating:,}\n"
        f"Remaining: {remaining:,}"
    )

# ---------------- PASTE ----------------

def paste_key():

    try:
        private_entry.delete(0, tk.END)
        private_entry.insert(0, root.clipboard_get())
    except:
        pass

# ---------------- INIT ----------------

load_contacts()
load_chain()
create_genesis_block()

threading.Thread(target=start_server, daemon=True).start()
threading.Thread(target=auto_sync, daemon=True).start()

# ---------------- GUI ----------------
    if GUI_AVAILABLE:
    root = tk.Tk()
    root.title("BC8 Node 1")
    root.geometry("500x930")
    root.configure(bg="light pink")

    # 👇👇👇 पूरा GUI code यहीं होना चाहिए 👇👇👇

    tk.Label(root, text="Sender").pack()
    sender_entry = tk.Entry(root)
    sender_entry.pack()

    # बाकी पूरा code

    root.mainloop()
root = tk.Tk()
root.title("BC7 Node 1")
root.geometry("500x930")
root.configure(bg="light pink")

def green_button(parent, text, command):
    btn = tk.Button(parent, text=text, bg="light green", width=18)
    btn.config(command=lambda: command(btn))
    return btn

tk.Label(root, text="BC8-BLOCKCHAIN NODE", bg="light pink", font=("Arial", 15)).pack(pady=10)

tk.Label(root, text="Sender", bg="light pink").pack()
sender_entry = tk.Entry(root, width=35)
sender_entry.pack()

tk.Label(root, text="Receiver", bg="light pink").pack()
receiver_entry = tk.Entry(root, width=35)
receiver_entry.pack()

# -------- NEW BUTTON --------
tk.Button(root, text="Paste Receiver", bg="light green", width=18, command=paste_receiver).pack(pady=3)

tk.Label(root, text="Select Contact", bg="light pink").pack()
contact_menu = ttk.Combobox(root, width=32)
contact_menu.pack()
refresh_contacts()
contact_menu.bind("<<ComboboxSelected>>", contact_selected)

tk.Label(root, text="Contact Name", bg="light pink").pack()
contact_name_entry = tk.Entry(root, width=35)
contact_name_entry.pack()

tk.Label(root, text="Contact Number", bg="light pink").pack()
contact_number_entry = tk.Entry(root, width=35)
contact_number_entry.pack()

tk.Button(root, text="Add Contact", bg="light green", width=18, command=add_contact).pack(pady=3)
tk.Button(root, text="Delete Selected Contact", bg="light green", width=18, command=delete_contact).pack(pady=3)

tk.Label(root, text="Amount", bg="light pink").pack()
amount_entry = tk.Entry(root, width=35)
amount_entry.pack()

tk.Label(root, text="Private Key", bg="light pink").pack()
private_entry = tk.Entry(root, width=35, show="*")
private_entry.pack()

tk.Button(root, text="Paste Key", bg="light green", width=18, command=paste_key).pack(pady=3)

tk.Label(root, text="Check Balance Name", bg="light pink").pack()
balance_entry = tk.Entry(root, width=35)
balance_entry.pack()

green_button(root,"Add Transaction",add_transaction).pack(pady=3)
green_button(root,"View Blockchain",view_chain).pack(pady=3)
green_button(root,"Check Balance",check_balance).pack(pady=3)
green_button(root,"Network Stats",show_stats).pack(pady=3)

tk.Button(root,text="Reset Fields",bg="light green",width=18,command=reset_fields).pack(pady=6)

frame = tk.Frame(root)
frame.pack()

scroll = tk.Scrollbar(frame)
scroll.pack(side=tk.RIGHT, fill=tk.Y)

text_box = tk.Text(frame,height=24,width=55,yscrollcommand=scroll.set)
text_box.pack(side=tk.LEFT)

scroll.config(command=text_box.yview)

root.mainloop()
