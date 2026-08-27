import asyncio
from telethon import TelegramClient, errors
from telethon.errors import FloodWaitError

# --- CONFIGURATION ---
api_id = 35165310  
api_hash = "d633a5c123ba915797629608cb6ee06c"  

# List of groups and topics IDsbto post in
target_groups = [
    # Format: ( group_username_or_id, topic_id)
    (-1002256623070, 11992),
    ("@Flips2", 15),
    ("@shoreline", 319),
    ("@texted", 24),
    ("@castmart", 5),
    ("@marketunlimited", 71892),
    ("@porkmarket", 15),
    ("@Luxurmarket", 12),
    ("@buffestmarket", 20),
]

# Wait time between broadcast rounds (3600 seconds = 1 hour)
INTERVAL_SECONDS = 3600

# Your Complete Ad Text
AD_TEXT = """Roboro SMM Service 📤

Tik tok 📱
$6- 1,000 Followers 📈
$1 - 1000views 👀
$2 - 1000 saves ⚡️
$5 - 1,000 Likes 📤  
$4 - 10,000 shares ✔️

YouTube 📱
15$ - 1.000 Subscribers 🔼
2$ - 1.000 Views 👀
8$ - 1.000 Likes 🔥
8$ - 500 Comments 💬
5$ - 500 Shares 🔗

Instagram 📱
7$ - 1.000 Followers 📈
4$ - 10.000 Likes 👍
2$ - 1000 Comments 💬
3$ - 10.000 Views 👀
5$ - 1000 Shares ✔️
5$ - 1000 Saves ⭐️

Telegram 📱
4$ - 10.000 Post views 👀
5$ - 1.000 Channel Members 💭
10$ - 1000 Premium Members 💬
3$ - 1.000 reactions 😀

Twitte 📱
10$ - 1.000 Followers 🔝
5$ - 1.000 Likes 😍
5$ - 1.000 Retweets 💫
10$ - 10000 Tweet Views 🌐
10$ - 10.000 Video Views 👀

Other Services Available: 📌

Contact:- 🔔@roborotemp"""

client = TelegramClient("user_session", api_id, api_hash)


async def send_advertisements():
    async with client:
        print("Broadcaster started successfully!")
        while True:
            for item in target_groups:
                if isinstance(item, tuple):
                    group, topic_id = item
                else:
                    group, topic_id = item, None

            try:
               if topic_id:
                   await client.send_message(group, AD_TEXT, reply_to=topic_id)
                   print(f"[+] post sent successfully to {group} (Topic: {topic_id})")
               else: 
                    await client.send_message(group, AD_TEXT)
                    print(f"[+] Post sent successfully to {group}")
            except errors.FloodWaitError as e:
                print(f"[!] Account rate-limited! Pausing 60s for {e.seconds} seconds before moving to next group immediately.")
                await asyncio.sleep(e.seconds)
                continue  
            except Exception as e:
                if "wait of" in str(e).lower():
                    print(f"[!] Account rate-limited! Pausing 60s group: before next group: {e}")
                    await asyncio.sleep(60)
                    continue
                print(f"[-] Failed to send to {group}: {e}")

            await asyncio.sleep(20)

        print("\nWaiting 1 hour for the next broadcast round...\n")
        await asyncio.sleep(3600)



