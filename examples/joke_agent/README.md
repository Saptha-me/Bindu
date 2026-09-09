# Joke Agent 😄

A Bindu agent that tells programming jokes using a public API.
Built to demonstrate `bindufy` with real-world retry logic.

## What it does

- Fetches jokes from `official-joke-api.appspot.com`
- Uses **exponential backoff + jitter** retry logic if the API is slow or down
- Falls back to built-in jokes if all retries fail
- No API key required — works out of the box

## How to run
```bash
python examples/joke_agent/joke_agent.py
```

## Test it

Once the agent is running, open a new terminal and run:
```bash
curl -X POST http://localhost:3773/messages \
-H "Content-Type: application/json" \
-d '[{"role": "user", "content": "Tell me a joke!"}]'
```

## Expected response
```
😄 Here's one for you!

**Why do programmers prefer dark mode?**

...Because light attracts bugs! 🥁
```

## Retry logic

If the joke API is unavailable, the agent retries up to 3 times
using exponential backoff with jitter (random delay added to prevent
thundering herd). If all retries fail, it falls back to built-in jokes
so the agent never returns an error to the user.