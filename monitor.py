import asyncio, json, os, pathlib, requests
from twscrape import API

USERS   = [u.strip() for u in os.environ["X_USERS"].split(",") if u.strip()]
TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT  = os.environ["TELEGRAM_CHAT_ID"]
TG_TOPIC = os.environ.get("TELEGRAM_TOPIC_ID", "").strip()
AUTH     = os.environ["X_AUTH_TOKEN"]
CT0      = os.environ["X_CT0"]

STATE = pathlib.Path("state/last_seen.json")

def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {}

def save_state(s):
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(s, indent=2))

def tg(text):
    payload = {"chat_id": TG_CHAT, "text": text,
               "disable_web_page_preview": "false"}
    if TG_TOPIC:
        payload["message_thread_id"] = TG_TOPIC
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data=payload,
        timeout=30,
    ).raise_for_status()

async def main():
    api = API()
    await api.pool.add_account(
        "burner", "x", "x@x.com", "x",
        cookies=f"auth_token={AUTH}; ct0={CT0}",
    )
    await api.pool.login_all()

    state = load_state()
    for handle in USERS:
        user = await api.user_by_login(handle)
        if not user:
            continue
        fresh, last = [], int(state.get(handle, 0))
        async for tw in api.user_tweets(user.id, limit=20):
            if tw.retweetedTweet or tw.inReplyToTweetId:
                continue
            if int(tw.id) > last:
                fresh.append(tw)
        for tw in sorted(fresh, key=lambda t: int(t.id)):
            link = f"https://x.com/{handle}/status/{tw.id}"
            body = (tw.rawContent or "")[:500]
            if last == 0:
                break
            tg(f"🐦 @{handle} posted:\n\n{body}\n\n{link}")
        if fresh:
            state[handle] = max(int(state.get(handle, 0)),
                                max(int(t.id) for t in fresh))
    save_state(state)

asyncio.run(main())
