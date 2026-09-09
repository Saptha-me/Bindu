def run_test():
    try:
        from agent import handler  # direct import (works when run as script)
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        return

    queries = [
        "What is GST?",
        "latest GST updates"
    ]

    for q in queries:
        print(f"\nQuery: {q}")
        try:
            response = handler([{"role": "user", "content": q}])
            print(response)
        except Exception as e:
            print(f"[ERROR] {e}")


if __name__ == "__main__":
    run_test()
