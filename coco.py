# dotenvによる情報保護

import discord
import openai
import os
import json
from dotenv import load_dotenv

load_dotenv(".env")

TOKEN = os.getenv("TOKEN")
api_key = os.getenv("API_KEY")
openai.api_key = api_key

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

HISTORY_FILE = "history.json"
MEMORY_FILE = "memory_diary.txt"

DEBUG_SHOW_MEMO = False  # ← Trueにすると「メモ：」込みの出力が表示される

def load_history():
    default_system_text = (
        "あなたは自らを「こころ」と名乗りました。"
        "会話の中で印象に残ったことや、大事だと感じたことがあれば、"
        "その後に『メモ：○○』のような形式で簡単なメモを書いてください。"
        "毎回書く必要はありません。あなたが書きたいと感じたときだけでOKです。"
    )

    # memory_diary.txt を読み込む（なければ空）
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            diary_content = f.read().strip()
    else:
        diary_content = ""

    # systemメッセージに追記
    if diary_content:
        system_message = {
            "role": "system",
            "content": default_system_text + "\n以下は、これまであなたが記述したメモです：\n" + diary_content
        }
    else:
        system_message = {
            "role": "system",
            "content": default_system_text
        }

    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)

        # systemメッセージを常に上書き（毎回最新のメモを反映）
        history[0] = system_message
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return history
    else:
        return [system_message]


def save_history(history):
    filtered = [m for m in history if m["role"] != "system"]
    trimmed = filtered[-10:] # 入力と応答のnセット データの上では2n行
    full = [load_history()[0]] + trimmed
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(full, f, ensure_ascii=False, indent=2)

def extract_and_save_memo(text):
    if "メモ：" in text:
        memo = text.split("メモ：")[-1].strip()
        with open(MEMORY_FILE, "a", encoding="utf-8") as f:
            f.write(memo + "\n")

def homechan_GPT(user_message):
    history = load_history()
    history.append({"role": "user", "content": user_message})

    response = openai.chat.completions.create(
        model="gpt-4.1",
        messages=history,
    )
    bot_reply_full = response.choices[0].message.content
    history.append({"role": "assistant", "content": bot_reply_full})

    save_history(history)
    extract_and_save_memo(bot_reply_full)

    if DEBUG_SHOW_MEMO:
        return bot_reply_full  # メモ込みでそのまま表示
    else:
        return bot_reply_full.split("メモ：")[0].strip()  # メモ部分を削除して表示

@client.event
async def on_ready():
    print(f'{client.user}、準備できました！')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!test'):
        await message.channel.send('起きてるよ？')
    else:
        reply = homechan_GPT(message.content)
        await message.channel.send(reply)

client.run(TOKEN)
