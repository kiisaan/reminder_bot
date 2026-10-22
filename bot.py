import os
import re
import datetime
import asyncio
import discord
from discord.ext import commands
import dateparser
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import http.server
import socketserver
import threading

# --- Renderのポート要件を満たすための簡易Webサーバー ---
PORT = int(os.environ.get("PORT", 10000))

class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Discord Bot is alive!")

def run_web_server():
    with socketserver.TCPServer(("", PORT), SimpleHandler) as httpd:
        print(f"Web server started on port {PORT}")
        httpd.serve_forever()

# 別スレッドでWebサーバーを起動
threading.Thread(target=run_web_server, daemon=True).start()
# --------------------------------------------------

# Intentsの設定（すべてのインテントを有効化）
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# スケジューラーの初期化
scheduler = AsyncIOScheduler()

@bot.event
async def on_ready():
    scheduler.start()
    print(f"Logged in as {bot.user.name}")

# メッセージ監視
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # デバッグログ：メッセージを受信したら必ず出力
    print(f"[RECEIVED MESSAGE]: {message.content}")

    content = message.content

    # URLを抽出
    url_pattern = r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+'
    urls = re.findall(url_pattern, content)

    if not urls:
        print(" -> URLが見つかりませんでした")
        await bot.process_commands(message)
        return

    target_url = urls[0]

    # URLを除外したテキストから日時を解析
    text_without_url = content.replace(target_url, "")
    parsed_date = dateparser.parse(text_without_url, languages=['ja'])

    print(f" -> 解析された日時: {parsed_date}")

    if parsed_date:
        # 過去指定の場合はスキップ
        if parsed_date <= datetime.datetime.now():
            print(" -> 過去の日時のためスキップされました")
            await bot.process_commands(message)
            return

        # 5分前を計算
        remind_time = parsed_date - datetime.timedelta(minutes=5)
        
        if remind_time < datetime.datetime.now():
            remind_time = datetime.datetime.now() + datetime.timedelta(seconds=10)

        channel_id = message.channel.id
        
        # リマインドタスクの関数
        async def send_reminder():
            target_channel = bot.get_channel(channel_id)
            if target_channel:
                await target_channel.send(
                    f"⏰ **リマインダー通知**\n"
                    f"まもなく予定の時間です（5分前）！\n"
                    f"🔗 対象URL: {target_url}"
                )

        # スケジューラーに登録
        scheduler.add_job(send_reminder, 'date', run_date=remind_time)
        
        # 登録完了のリアクション
        await message.add_reaction("✅")
        print(f" -> リマインダー登録成功! (実行予定: {remind_time})")

    await bot.process_commands(message)

# Botの起動
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("Error: DISCORD_TOKEN environment variable is not set or empty.")
else:
    bot.run(TOKEN)
