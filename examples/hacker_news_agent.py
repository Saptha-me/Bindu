"""
Hacker News Agent - Fetches and summarizes top HN stories

Usage:
    python examples/hacker_news_agent.py
    
Example queries:
    - "What are the top stories today?"
    - "Show me top 5 posts"
    - "Latest HN stories"
"""
import requests
from bindu.penguin.bindufy import bindufy


def fetch_hn_top_stories(limit=10):
    """Fetch top stories from Hacker News API."""
    try:
        top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        story_url = "https://hacker-news.firebaseio.com/v0/item/{}.json"
        
        response = requests.get(top_stories_url, timeout=5)
        response.raise_for_status()
        story_ids = response.json()[:limit]
        
        stories = []
        for sid in story_ids:
            story_response = requests.get(story_url.format(sid), timeout=5)
            story = story_response.json()
            if story:
                stories.append({
                    "title": story.get("title", "No title"),
                    "url": story.get("url", ""),
                    "score": story.get("score", 0),
                    "by": story.get("by", "unknown"),
                    "time": story.get("time", 0)
                })
        
        return stories
    except Exception as e:
        return {"error": str(e)}


def handler(messages: list[dict[str, str]]):
    """Process HN queries and return formatted results."""
    last_msg = messages[-1]["content"].lower()
    
    # Extract number if specified
    limit = 5
    if "top 10" in last_msg or "10 stories" in last_msg:
        limit = 10
    elif "top 3" in last_msg or "3 stories" in last_msg:
        limit = 3
    
    # Check for HN query keywords
    keywords = ["top", "stories", "posts", "hacker news", "hn", "latest"]
    if any(word in last_msg for word in keywords):
        stories = fetch_hn_top_stories(limit)
        
        if isinstance(stories, dict) and "error" in stories:
            return [{
                "role": "assistant",
                "content": f"❌ Error fetching stories: {stories['error']}"
            }]
        
        if not stories:
            return [{
                "role": "assistant",
                "content": "No stories found at the moment."
            }]
        
        response = f"📰 **Top {len(stories)} Hacker News Stories:**\n\n"
        for i, story in enumerate(stories, 1):
            response += f"{i}. **{story['title']}** ({story['score']} points)\n"
            if story['url']:
                response += f"   🔗 {story['url']}\n"
            response += f"   👤 by {story['by']}\n\n"
        
        return [{"role": "assistant", "content": response}]
    
    return [{
        "role": "assistant",
        "content": "I can fetch top Hacker News stories. Try asking:\n- 'What are the top stories today?'\n- 'Show me top 10 HN posts'\n- 'Latest stories'"
    }]


# Bindu configuration (for demonstration purposes)
config = {
    "author": "shiv4321@gmail.com",
    "name": "hacker_news_agent",
    "description": "Fetches and summarizes top Hacker News stories with real-time API integration",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True
    },
    "skills": ["skills/question-answering"]
}

if __name__ == "__main__":
    bindufy(config, handler)   
