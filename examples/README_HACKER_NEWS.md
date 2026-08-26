# Hacker News Agent

A Bindu agent that fetches and displays top stories from Hacker News in real-time.

## Features

- 🔥 Real-time HN top stories via official API
- 📊 Customizable story limit (top 3, 5, or 10)
- ⚡ Error handling and timeout protection
- 🎯 Keyword-based query detection

## Installation
```bash
# The agent uses standard requests library (already in Bindu deps)
python examples/hacker_news_agent.py
```

## Usage

Start the agent:
```bash
python examples/hacker_news_agent.py
```

Query examples:
- "What are the top stories today?"
- "Show me top 10 HN posts"
- "Latest hacker news stories"

## API Integration

Uses the official Hacker News API:
- Endpoint: `https://hacker-news.firebaseio.com/v0/topstories.json`
- No authentication required
- Free and unlimited

## Response Format
```
📰 Top 5 Hacker News Stories:

1. **Story Title** (250 points)
   🔗 https://example.com/article
   👤 by username

...
```

## Technical Details

- **Timeout:** 5 seconds per request
- **Default limit:** 5 stories
- **Error handling:** Returns friendly error messages
- **Dependencies:** `requests` (built-in)


## Contributing

This example demonstrates:
- External API integration with Bindu
- Error handling best practices
- Natural language query parsing
- Formatted response generation



---

