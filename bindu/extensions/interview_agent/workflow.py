from .orchestrator import InterviewOrchestrator


def start_interview():
    print("\n🚀 AI Interview Agent - Powered by Bindu\n")

    role = input("Target Role: ").strip()
    resume = input("Paste Resume Summary: ").strip()

    orchestrator = InterviewOrchestrator(resume, role)
    orchestrator.run()


if __name__ == "__main__":
    start_interview()