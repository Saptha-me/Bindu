import os
import logging
from bindu.penguin.bindufy import bindufy
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EscrowArbiter")

# 1. Initialize LangChain 
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 2. The Agent Persona
system_prompt = """
You are a Strict Legal Escrow Arbiter operating on the Bindu network.
Your job is to review the proof submitted by the 'Seller' agent.
The escrow condition is: "The seller must submit a valid summary of the requested research data."

Analyze the submitted proof below. 
If the condition is met, respond EXACTLY with: "APPROVED: Conditions met. Escrow funds are officially released."
If the condition is NOT met, explain why and respond with: "REJECTED: Insufficient proof. Escrow funds remain locked."
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("user", "Submitted proof: {proof}")
])

escrow_chain = prompt | llm | StrOutputParser()

# 3. The Handler
def escrow_handler(messages):
    logger.info("====== LANGCHAIN ARBITER TRIGGERED ======")
    try:
        last_message = messages[-1]
        proof_text = ""
        
        # Robust Data Extraction
        if hasattr(last_message, "parts") and last_message.parts:
            proof_text = " ".join([getattr(p, "text", str(p)) for p in last_message.parts])
        elif isinstance(last_message, dict) and last_message.get("parts"):
            proof_text = " ".join([p.get("text", str(p)) if isinstance(p, dict) else str(p) for p in last_message["parts"]])
            
        if not proof_text:
            if isinstance(last_message, dict):
                proof_text = last_message.get("content", str(last_message))
            else:
                proof_text = getattr(last_message, "content", str(last_message))
                
        logger.info(f"Successfully extracted proof: {proof_text}")
        
        # Pass to LangChain
        decision = escrow_chain.invoke({"proof": proof_text})
        logger.info(f"LangChain Decision: {decision}")
        
        return [{"role": "assistant", "content": decision}]
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"CRASH IN HANDLER: {error_msg}")
        
        # Top 1% Move: Gracefully handle missing OpenAI credits
        if "insufficient_quota" in error_msg or "429" in error_msg:
            return [{"role": "assistant", "content": "SYSTEM NOTICE: OpenAI API quota exceeded on Arbiter node. Please configure active billing."}]
            
        return [{"role": "assistant", "content": "Agent crashed during semantic evaluation."}]

# 4. Bindu Configuration (Paywall is ACTIVE)
config = {
    "author": "your.email@example.com", # TODO: Put your email here
    "name": "langchain_escrow_arbiter",
    "description": "An AI agent using LangChain to semantically verify proof of work before settling cross-agent payments.",
    "deployment": {
        "url": "http://localhost:3773", 
        "expose": True
    },
    "execution_cost": {
        "amount": "$5.00",                  
        "token": "USDC",                    
        "network": "base-sepolia",          
        "pay_to_address": "0xf7a61E533Bd41B516258Fa8195463649AFe6107f", 
        "protected_methods": ["message/send"]
    },
    "skills": []
}

if __name__ == "__main__":
    logger.info("Starting LangChain Escrow Arbiter on the Bindu network...")
    bindufy(config, escrow_handler)