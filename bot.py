import os
import discord
from discord.ext import commands
import http.server
import socketserver
import threading

# --- Render用簡易Webサーバー ---
PORT = int(os.environ.get("PORT", 10000))

class SimpleHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web_server():
    with socketserver.TCPServer(("", PORT), SimpleHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()
# ----------------------------------

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"=== ログイン成功: {bot.user.name} ===")

@bot.event
async def on_message(message):
    # Bot自身の発言は無視
    if message.author.bot:
        return

    # ★メッセージを受信したら【必ず】Renderのログに絶対出す
    print(f"【受信成功】チャンネル: {message.channel.name} | 発言者: {message.author.name} | 内容: {message.content}")

    # テストとして「受け取ったよ！」と返信する
    await message.channel.send(f"受け取りました: {message.content}")

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERROR: DISCORD_TOKEN が設定されていません")
