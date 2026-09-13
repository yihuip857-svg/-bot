import os
import sqlite3
import datetime
import discord
from discord.ext import commands
from discord import app_commands

# --- データベースの初期化 ---
conn = sqlite3.connect('hihi_data.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS drop_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    guild_id INTEGER,
    created_at TIMESTAMP
)
''')
conn.commit()

# --- Discord Botの設定 ---
TOKEN = "ここにBotのトークンを貼る"

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # スラッシュコマンドを同期
        await self.tree.sync()

client = MyClient()

@client.event
async def on_ready():
    print(f'ログインしました: {client.user}')

# --- コマンド1: ドロップ報告 (/hihi) ---
@client.tree.command(name="hihi", description="ヒヒイロカネのドロップを報告")
@app_commands.describe(image="ドロップ画面のスクリーンショット")
async def hihi(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer()
    # 画像チェック
    if not image.content_type or not image.content_type.startswith('image/'):
        await interaction.followup.send("画像ファイルを添付してください！", ephemeral=True)
        return

    # DBに記録
    now = datetime.datetime.now()
    cursor.execute(
        "INSERT INTO drop_logs (user_id, guild_id, created_at) VALUES (?, ?, ?)",
        (interaction.user.id, interaction.guild_id, now)
    )
    conn.commit()

    # 通算カウントを取得
    cursor.execute(
        "SELECT COUNT(*) FROM drop_logs WHERE user_id = ? AND guild_id = ?",
        (interaction.user.id, interaction.guild_id)
    )
    total = cursor.fetchone()[0]

    await interaction.response.send_message(
        f"🎉 **{interaction.user.display_name}** さんのヒヒイロドロップを記録しました！\n"
        f"現在のサーバー内通算: **{total} 個**\n"
        f"証拠画像: {image.url}"
    )

# --- コマンド2: 個人のカウント確認 (/count) ---
@client.tree.command(name="count", description="自分のドロップ数を確認")
async def count(interaction: discord.Interaction):
    cursor.execute(
        "SELECT COUNT(*) FROM drop_logs WHERE user_id = ? AND guild_id = ?",
        (interaction.user.id, interaction.guild_id)
    )
    total = cursor.fetchone()[0]
    
    await interaction.followup.send(
        f"📊 **{interaction.user.display_name}** さんのヒヒイロ通算ドロップ数: **{total} 個**",
        ephemeral=True
    )

# --- コマンド3: サーバー内ランキング (/ranking) ---
@client.tree.command(name="ranking", description="サーバー内のヒヒイロドロップランキングを表示")
@app_commands.choices(period=[
    app_commands.Choice(name="全期間", value="all"),
    app_commands.Choice(name="今月", value="month"),
    app_commands.Choice(name="今週", value="week")
])
async def ranking(interaction: discord.Interaction, period: app_commands.Choice[str]):
    now = datetime.datetime.now()
    
    if period.value == "month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        title = "今月のドロップランキング"
    elif period.value == "week":
        start_date = (now - datetime.timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        title = "今週のドロップランキング"
    else:
        start_date = datetime.datetime(2000, 1, 1)
        title = "全期間のドロップランキング"

    # 集計クエリ
    cursor.execute('''
        SELECT user_id, COUNT(*) as count 
        FROM drop_logs 
        WHERE guild_id = ? AND created_at >= ?
        GROUP BY user_id 
        ORDER BY count DESC 
        LIMIT 10
    ''', (interaction.guild_id, start_date))
    
    results = cursor.fetchall()

    if not results:
        await interaction.response.send_message("該当期間のドロップ記録はありません。")
        return

    text = f"🏆 **{title}** 🏆\n"
    for i, (user_id, num) in enumerate(results, 1):
        member = interaction.guild.get_member(user_id)
        name = member.display_name if member else f"ユーザーID:{user_id}"
        text += f"**{i}位**: {name} - {num}個\n"

    await interaction.response.send_message(text)

# 起動
client.run(os.getenv("DISCORD_TOKEN"))

