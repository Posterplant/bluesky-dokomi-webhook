# requirements:
# pip install atproto requests apscheduler python-dotenv

import traceback
import os
import re
import sys
from datetime import datetime
import time

import requests
from atproto import Client as BskyClient
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")

SEARCH_QUERY = "dokomi"
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", 10))

SEEN_FILE = "seen_posts.txt"

bsky = BskyClient()
seen_posts = set()


def load_seen():
    global seen_posts

    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            seen_posts = set(x.strip() for x in f.readlines())


def save_seen():
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(seen_posts))


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()


def send_to_discord(content):
    r = requests.post(
        DISCORD_WEBHOOK_URL,
        json={"content": content},
        timeout=30,
    )

    r.raise_for_status()


def search_and_post():
    print(f"\n=== run @ {datetime.now()} ===", flush=True)

    try:
        results = bsky.app.bsky.feed.search_posts(
            {
                "q": SEARCH_QUERY,
                "limit": 30,
                "sort": "latest",
            }
        )

        print(f"got {len(results.posts)} posts", flush=True)

        new_count = 0

        for post in results.posts:
            uri = post.uri

            if uri in seen_posts:
                continue

            new_count += 1
            print(f"new: {uri}", flush=True)

            # ... existing formatting ...

            send_to_discord(f"New post by {post.author.handle}:\nhttps://bsky.app/profile/{post.author.handle}/post/{post.uri.split('/')[-1]}")

            print("posted to discord", flush=True)

            seen_posts.add(uri)

        print(f"done. new posts: {new_count}", flush=True)
        save_seen()

    except Exception as e:
        print("error:", e)
        traceback.print_exc()


def test_discord():
    """Send a test message to Discord"""
    test_message = "🧪 Test message from dokominews bot!"
    send_to_discord(test_message)
    print("Test message sent!")


def main():
    load_seen()

    print("logging into bluesky...")
    bsky.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)

    # Check for test flag
    if "--test" in sys.argv or "-test" in sys.argv:
        print("Running in test mode...")
        test_discord()
        print("Test complete. Exiting.")
        return

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        search_and_post,
        "interval",
        minutes=CHECK_INTERVAL_MINUTES,
    )

    search_and_post()

    print("scheduler started, checking every", CHECK_INTERVAL_MINUTES, "minutes")
    scheduler.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
