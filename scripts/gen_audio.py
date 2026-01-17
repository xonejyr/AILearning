import asyncio
import edge_tts
import json
import os

async def generate_speech():
    with open("几何/题目1_教学指令.json", "r", encoding="utf-8") as f:
        steps = json.load(f)

    if not os.path.exists("audio"):
        os.makedirs("audio")

    for i, step in enumerate(steps):
        text = step["speech"]
        # 使用云希（男声）或晓晓（女声）
        voice = "zh-CN-YunxiNeural" 
        output_file = f"audio/step_{i+1}.mp3"
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        print(f"Generated: {output_file}")

if __name__ == "__main__":
    asyncio.run(generate_speech())