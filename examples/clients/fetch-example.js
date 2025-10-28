/**
 * Bindu x402 Client Example using x402-fetch
 * 
 * This example demonstrates how to interact with a Bindu agent that requires payment.
 * The x402-fetch library automatically handles payment verification and retries.
 * 
 * Prerequisites:
 * 1. npm install x402-fetch viem dotenv
 * 2. Create .env file with WALLET_PRIVATE_KEY
 * 3. Ensure you have USDC on the configured network (e.g., Base Sepolia)
 * 4. Start your Bindu agent with execution_cost configured
 * 
 * Usage:
 * node fetch-example.js
 */

import { wrapFetchWithPayment, decodeXPaymentResponse } from "x402-fetch";
import { privateKeyToAccount } from "viem/accounts";
import dotenv from "dotenv";

// Load environment variables
dotenv.config();

// Configuration
const AGENT_URL = process.env.AGENT_URL || "http://localhost:3773";
const WALLET_PRIVATE_KEY = process.env.WALLET_PRIVATE_KEY;

if (!WALLET_PRIVATE_KEY) {
  console.error("❌ Error: WALLET_PRIVATE_KEY not found in environment variables");
  console.error("Please create a .env file with your wallet private key:");
  console.error('WALLET_PRIVATE_KEY="0x..."');
  process.exit(1);
}

async function main() {
  try {
    console.log("🚀 Bindu x402 Client Example\n");

    // Create wallet account from private key
    const account = privateKeyToAccount(WALLET_PRIVATE_KEY);
    console.log(`📝 Using wallet: ${account.address}`);
    console.log(`🎯 Agent URL: ${AGENT_URL}\n`);

    // Wrap fetch with automatic payment handling
    const fetchWithPayment = wrapFetchWithPayment(fetch, account);

    // Create A2A message request
    const a2aRequest = {
      jsonrpc: "2.0",
      id: "1",
      method: "message/send",
      params: {
        message: {
          role: "user",
          parts: [
            {
              kind: "text",
              text: "Hello! Can you help me with something?"
            }
          ]
        }
      }
    };

    console.log("📤 Sending message to agent...");
    console.log(`Message: "${a2aRequest.params.message.parts[0].text}"\n`);

    // Make request - payment is handled automatically!
    const response = await fetchWithPayment(AGENT_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(a2aRequest),
    });

    // Check response status
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`❌ Request failed with status ${response.status}`);
      console.error(`Error: ${errorText}`);
      process.exit(1);
    }

    // Parse agent response
    const result = await response.json();
    console.log("✅ Agent response received!");
    console.log("\n📋 Task Details:");
    console.log(`  Task ID: ${result.result.id}`);
    console.log(`  Status: ${result.result.status.state}`);
    
    if (result.result.messages && result.result.messages.length > 0) {
      const lastMessage = result.result.messages[result.result.messages.length - 1];
      if (lastMessage.parts && lastMessage.parts.length > 0) {
        console.log(`\n💬 Agent says:`);
        console.log(`  ${lastMessage.parts[0].text}`);
      }
    }

    // Decode payment confirmation from response headers
    const paymentResponseHeader = response.headers.get("x-payment-response");
    if (paymentResponseHeader) {
      const paymentResponse = decodeXPaymentResponse(paymentResponseHeader);
      console.log("\n💰 Payment Confirmation:");
      console.log(`  Success: ${paymentResponse.success}`);
      console.log(`  Transaction Hash: ${paymentResponse.transactionHash || 'N/A'}`);
      console.log(`  Timestamp: ${new Date(paymentResponse.timestamp * 1000).toISOString()}`);
    }

    console.log("\n✨ Done!");

  } catch (error) {
    console.error("\n❌ Error:", error.message);
    
    if (error.response) {
      console.error("Response status:", error.response.status);
      console.error("Response data:", error.response.data);
    }
    
    process.exit(1);
  }
}

// Run the example
main();
