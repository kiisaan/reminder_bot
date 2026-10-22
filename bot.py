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
        httpd.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()
# --------------------------------------------------

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

scheduler = AsyncIOScheduler()

@bot.event
async def on_ready():
    scheduler.start()
    print(f"=== ログイン成功: {bot.user.name} ===")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    print(f"【受信】{message.content}")

    content = message.content

    # URLを抽出
    url_pattern = r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+'
    urls = re.findall(url_pattern, content)

    if not urls:
        print(" -> URLなしのためスキップ")
        await bot.process_commands(message)
        return

    target_url = urls[0]

    # URLを除外したテキストから日時を解析
    text_without_url = content.replace(target_url, "")
    parsed_date = dateparser.parse(text_without_url, languages=['ja'])

    print(f" -> 解析された日時: {parsed_date}")

    if parsed_date:
        if parsed_date <= datetime.datetime.now():
            print(" -> 過去の日時のためスキップ")
            await message.channel.send("⚠️ 指定された日時が過去（または現在より前）です。未来の日時を指定してください。")
            await bot.process_commands(message)
            return

        # 5分前を計算
        remind_time = parsed_date - datetime.timedelta(minutes=5)
        
        # もし設定時間が近すぎてすでに5分前を過ぎている場合の保険
        if remind_time < datetime.datetime.now():
            remind_time = datetime.datetime.now() + datetime.timedelta(seconds=10)

        channel_id = message.channel.id
        
        async def send_reminder():
            target_channel = bot.get_channel(channel_id)
            if target_channel:
                await target_channel.send(
                    f"⏰ **リマインダー通知**\n"
                    f"まもなく予定の時間（5分前）です！\n"
                    f"🔗 対象URL: {target_url}"
                )

        # スケジューラーに登録
        scheduler.add_job(send_reminder, 'date', run_date=remind_time)
        
        # 登録成功のリアクション
        await message.add_reaction("✅")
        print(f" -> リマインダー登録成功! (通知予定時刻: {remind_time})")

    else:
        print(" -> 日時が読み取れませんでした")
        await message.channel.send("⚠️ 日時がうまく読み取れませんでした。「今日の15:30」などのように指定してみてください。")

    await bot.process_commands(message)

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERROR: DISCORD_TOKEN が設定されていません")
