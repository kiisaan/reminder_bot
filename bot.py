import datetime
import os
import re
import sqlite3
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import dateparser

# 環境変数からDiscordのトークンを取得
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
scheduler = AsyncIOScheduler()

# データベースの初期化（再起動しても予定が消えないようにする）
DB_FILE = "reminders.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER,
            remind_time TEXT,
            url TEXT,
            content TEXT,
            sent INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    # 登録済みの未送信リマインドを再スケジュール
    reschedule_existing_reminders()
    scheduler.start()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content

    # メッセージからURLを抽出
    url_match = re.search(r"https?://[\w/:%#\$&\?\(\)~\.=\+\-]+", content)
    if not url_match:
        return
    url = url_match.group(0)

    # URL部分を除いたテキストを日付解析用にする
    text_for_date = content.replace(url, "").strip()
    
    # 日時を解析（例: "10月25日 15:00" や "明日 13:00" など）
    parsed_date = dateparser.parse(text_for_date, settings={'PREFER_DATES_FROM': 'future'})
    
    if parsed_date:
        # イベント時間の5分前を計算
        remind_time = parsed_date - datetime.timedelta(minutes=5)
        now = datetime.datetime.now()

        if remind_time > now:
            # データベースに保存
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO reminders (channel_id, remind_time, url, content) VALUES (?, ?, ?, ?)",
                (message.channel.id, remind_time.isoformat(), url, content)
            )
            conn.commit()
            reminder_id = cursor.lastrowid
            conn.close()

            # スケジューラーに登録
            scheduler.add_job(
                send_reminder,
                'date',
                run_date=remind_time,
                args=[reminder_id, message.channel.id, url, parsed_date.strftime('%Y-%m-%d %H:%M')]
            )

            await message.channel.reply(f"✅ リマインダーを登録しました！（{parsed_date.strftime('%Y-%m-%d %H:%M')}の5分前に通知します）")

async def send_reminder(reminder_id, channel_id, url, event_time_str):
    channel = client.get_channel(channel_id)
    if channel:
        await channel.send(f"⏰ **まもなくイベントの時間です！**（予定時刻: {event_time_str}）\n{url}")
    
    # 送信済みフラグを更新
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()

def reschedule_existing_reminders():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, channel_id, remind_time, url, content FROM reminders WHERE sent = 0")
    rows = cursor.fetchall()
    conn.close()

    now = datetime.datetime.now()
    for row in rows:
        r_id, channel_id, r_time_str, url, content = row
        r_time = datetime.datetime.fromisoformat(r_time_str)
        if r_time > now:
            scheduler.add_job(
                send_reminder,
                'date',
                run_date=r_time,
                args=[r_id, channel_id, url, r_time.strftime('%Y-%m-%d %H:%M')]
            )

client.run(TOKEN)
