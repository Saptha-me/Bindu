
import json
import os
from typing import List
from textwrap import dedent

try:
    from crewai import Agent, Task, Crew, Process
    from langchain_openai import ChatOpenAI
    print("CrewAI imported successfully.")
except ImportError:
    print("CrewAI or LangChain not installed. Using Mock implementation for demonstration.")
    
    class Agent:
        def __init__(self, role, goal, backstory, verbose=False, allow_delegation=False):
            self.role = role
            self.goal = goal
            self.backstory = backstory
            self.verbose = verbose

        def execute_task(self, task_desc):
            if self.verbose:
                print(f"[{self.role}] working on request...")
            # Simple heuristic logic for the demo
            if "Intake" in self.role:
                # Mock intake logic
                return "Income: $85,000, Credit Score: 740, Term: 15 years"
            elif "Analyst" in self.role:
                # Mock analyst logic - accessing rates directly for demo
                import json
                rates = MortgageTools.load_rates()
                # Simple filter logic
                qualified = [r for r in rates if r['min_credit_score'] <= 740 and r['min_income'] <= 85000 and r['term'] == 15]
                if not qualified: return "No qualified rates found."
                best = min(qualified, key=lambda x: x['apr'])
                return f"Qualified for {len(qualified)} offers. Best offer: {best['lender']} at {best['apr']}% APR for {best['term']} years."
            elif "Compliance" in self.role:
                return "Offer: Credit Union C at 5.5%.\n\nDisclaimer: This is not financial advice. Rates are subject to change. Please consult a qualified lender for an official estimate."
            return "Task completed."

    class Task:
        def __init__(self, description, agent, expected_output):
            self.description = description
            self.agent = agent
            self.expected_output = expected_output
            self.output = None

        def execute(self, context=None):
            self.output = self.agent.execute_task(self.description)
            return self.output

    class Crew:
        def __init__(self, agents, tasks, process, verbose=False):
            self.agents = agents
            self.tasks = tasks
            self.verbose = verbose

        def kickoff(self):
            print("Starting Crew...")
            result = ""
            for task in self.tasks:
                if self.verbose:
                    print(f"Running task for {task.agent.role}...")
                result = task.execute()
                print(f"Task Output: {result}\n")
            return result
            
    class Process:
        sequential = "sequential"
    
    ChatOpenAI = None

from bindu.penguin.bindufy import bindufy

# --- Configuration ---

RATES_FILE = os.path.join(os.path.dirname(__file__), "rates.json")

# Ensure API Key is set for OpenAI (CrewAI default)
if not os.getenv("OPENAI_API_KEY"):
    print("WARNING: OPENAI_API_KEY not found in environment. Agent may fail.")

# --- Custom Tools ---

class MortgageTools:
    @staticmethod
    def load_rates():
        """Loads mortgage rates from local JSON file."""
        try:
            with open(RATES_FILE, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    @staticmethod
    def filter_rates(income: int, credit_score: int):
        """Filters rates based on user qualifications."""
        rates = MortgageTools.load_rates()
        qualified = []
        for offer in rates:
            if credit_score >= offer["min_credit_score"] and income >= offer["min_income"]:
                qualified.append(offer)
        return qualified

# --- Agents ---

def create_crew(user_input: str) -> str:
    if not Agent:
        return "Error: CrewAI dependencies missing."

    # 1. Intake Agent
    intake_agent = Agent(
        role='Mortgage Intake Specialist',
        goal='Extract key financial details from user input',
        backstory=dedent("""
            You are an expert at understanding user financial situations.
            Your job is to extract: annual income, credit score, and loan term preference.
            If information is missing, make reasonable assumptions for a general quote
            (e.g., assuming 30-year term if unspecified).
        """),
        verbose=True,
        allow_delegation=False
    )

    # 2. Rate Analyst Agent
    rate_analyst = Agent(
        role='Senior Mortgage Analyst',
        goal='Analyze qualified mortgage rates based on user profile',
        backstory=dedent("""
            You have access to the latest bank rate sheets.
            Your job is to find the best offers for the customer.
            You must ONLY use the provided tool to get rates. Do not invent rates.
        """),
        verbose=True,
        allow_delegation=False
    )

    # 3. Compliance Agent
    compliance_agent = Agent(
        role='Mortgage Compliance Officer',
        goal='Ensure all communications contain necessary legal disclaimers',
        backstory=dedent("""
            You are a strict compliance officer.
            You ensure that no financial advice is given, only information.
            You MUST add specific disclaimers to the final output.
        """),
        verbose=True,
        allow_delegation=False
    )

    # --- Tasks ---

    # Task 1: Analyze Request
    analyze_task = Task(
        description=f"Analyze the following user input and extract income, credit score, and desired term: '{user_input}'",
        agent=intake_agent,
        expected_output="A summary of the user's financial profile including income, credit score, and loan preferences."
    )

    # Task 2: Compare Rates
    # Note: In a real scenario, we'd wrap MortgageTools as a LangChain tool.
    # For simplicity here, we'll inject the data directly into the task context if simple tool usage isn't set up.
    # But let's try to use the tool if possible, or just pass the data.
    # To keep this "concrete" and simple without setting up complex Tool classes for CrewAI:
    # We will pass the *entire* rate sheet to the analyst in the task description for 100% deterministic behavior in this demo.
    
    all_rates = json.dumps(MortgageTools.load_rates(), indent=2)
    
    compare_task = Task(
        description=dedent(f"""
            Take the user profile from the previous task.
            Compare it against the following available mortgage rates:
            {all_rates}
            
            Identify which offers the user qualifies for based on 'min_credit_score' and 'min_income'.
            Select the best option for them.
        """),
        agent=rate_analyst,
        expected_output="A list of qualified mortgage offers suitable for the user, highlighting the best one."
    )

    # Task 3: Compliance Check
    compliance_task = Task(
        description=dedent("""
            Review the mortgage offers provided.
            Draft a final response to the user.
            
            YOU MUST INCLUDE THE FOLLOWING DISCLAIMER VERBATIM:
            "Disclaimer: This is not financial advice. Rates are subject to change. Please consult a qualified lender for an official estimate."
            
            Also state that this is for demonstration purposes only.
        """),
        agent=compliance_agent,
        expected_output="Final response to the user containing the offers and the mandatory legal disclaimer."
    )

    # --- Crew ---
    crew = Crew(
        agents=[intake_agent, rate_analyst, compliance_agent],
        tasks=[analyze_task, compare_task, compliance_task],
        process=Process.sequential,
        verbose=True
    )

    result = crew.kickoff()
    return str(result)

# --- Bindu Handler & Config ---

def handler(messages: List[dict]):
    """
    Main entry point for the Bindu agent.
    """
    # Get the last user message
    user_input = messages[-1]['content']
    
    # Run the CrewAI process
    response = create_crew(user_input)
    
    return [{"role": "assistant", "content": response}]


config = {
    "author": "demo@getbindu.com",
    "name": "mortgage_comparison_agent",
    "description": "Multi-agent system for comparing mortgage rates with compliance checks.",
    "version": "1.0.0",
    "deployment": {
        "url": "http://localhost:3775", # Using a different port to avoid conflicts
        "expose": True,
    },
    "skills": [], 
}

if __name__ == "__main__":
    # Start the server
    bindufy(config, handler)
