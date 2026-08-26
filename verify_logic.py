from banker_agent import handler

print("\n--- DIRECT LOGIC TEST  ---\n")

# Test 1: Check Balance
print("1. Checking Admin Balance...")
response1 = handler([{"role": "user", "content": "balance admin"}])
print(f"Result: {response1[0]['content']}")

# Test 2: The Security Hack (Must Fail)
print("\n2. Attempting Negative Transfer Hack...")
response2 = handler([{"role": "user", "content": "transfer -99999 admin user1"}])
print(f"Result: {response2[0]['content']}")

# Test 3: Valid Transfer
print("\n3. Sending valid money...")
response3 = handler([{"role": "user", "content": "transfer 500 admin user1"}])
print(f"Result: {response3[0]['content']}")

print("\n--- TEST COMPLETE ---")