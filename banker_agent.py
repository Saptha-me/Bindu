import json
import os
import threading
import time
from bindu.penguin.bindufy import bindufy

# file to store the money data
db_file = "ledger.json"

class BankSystem:
    def __init__(self):
        # using a lock to stop two people writing at the same time
        self.lock = threading.Lock()
        self.init_db()

    def init_db(self):
        if not os.path.exists(db_file):
            with open(db_file, "w") as f:
                # admin starts with 1 million
                json.dump({"admin": 1000000, "user1": 500}, f)

    def get_balance(self, username):
        with self.lock:
            with open(db_file, "r") as f:
                data = json.load(f)
            return data.get(username, 0)

    def transfer(self, sender, receiver, amount):
        # basic security checks
        if amount <= 0:
            return False, "error: amount must be positive"
        
        with self.lock:
            # read data
            with open(db_file, "r") as f:
                data = json.load(f)

            sender_bal = data.get(sender, 0)
            
            # check if they have enough money
            if sender_bal < amount:
                print(f"failed transfer: {sender} has {sender_bal} but tried to send {amount}")
                return False, "insufficient funds"

            # do the transfer
            data[sender] -= amount
            data[receiver] = data.get(receiver, 0) + amount

            # save immediately
            with open(db_file, "w") as f:
                json.dump(data, f, indent=2)

            print(f"success: {sender} sent {amount} to {receiver}")
            return True, f"transfer complete. new balance: {data[sender]}"


bank = BankSystem()

def handler(messages):
    try:
        last_msg = messages[-1]["content"].strip()
        parts = last_msg.split()
        
     
        command = parts[0].lower()

        if command == "balance":
            if len(parts) < 2:
                return [{"role": "assistant", "content": "usage: balance <username>"}]
            
            user = parts[1]
            bal = bank.get_balance(user)
            return [{"role": "assistant", "content": f"user {user} has {bal} credits"}]

        elif command == "transfer":
            # example: transfer 100 admin user1
            if len(parts) < 4:
                return [{"role": "assistant", "content": "usage: transfer <amount> <sender> <receiver>"}]
            
            try:
                amount = int(parts[1])
                sender = parts[2]
                receiver = parts[3]
            except ValueError:
                return [{"role": "assistant", "content": "error: amount must be a number"}]

            success, msg = bank.transfer(sender, receiver, amount)
            status = "success" if success else "failed"
            return [{"role": "assistant", "content": f"{status}: {msg}"}]

        else:
            return [{"role": "assistant", "content": "bank ready. use 'balance' or 'transfer'"}]

    except Exception as e:
        print(f"error: {str(e)}")
        return [{"role": "assistant", "content": "system error"}]

config = {
    "author": "sahasrabudhesoham@gmail.com",
    "name": "secure_ledger",
    "description": "a thread-safe ledger that prevents race conditions",
    "deployment": {"url": "http://localhost:3776", "expose": True},
    "skills": [] 
}

if __name__ == "__main__":
    print("bank agent started on port 3776...")
    bindufy(config, handler)