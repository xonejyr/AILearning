# generate_task.py
import json
import os
from PIL import Image
from utils import process_layout_data  # 确保 utils.py 在同级目录

# 1. 定义你的输入文件 (就是你刚才给我的那些内容)
DIR = "../题目/1/output"
FILE_LOGIC = f"{DIR}/1_logic.json"
FILE_RAW = f"{DIR}/2_raw_layout.json"
FILE_TIMELINE = f"{DIR}/3_timeline.json"
IMAGE_PATH = f"{DIR}/../题目1_题目.jpg" # 必须有图片来计算长宽比
OUTPUT_FILE = f"{DIR}/render_task.json"

def main():
    # 1. 读取三个 JSON
    with open(FILE_LOGIC, 'r', encoding='utf-8') as f: logic = json.load(f)
    with open(FILE_RAW, 'r', encoding='utf-8') as f: raw = json.load(f)["layout_map"]
    with open(FILE_TIMELINE, 'r', encoding='utf-8') as f: timeline = json.load(f)
    
    # 2. 读取图片获取长宽比 (关键步骤)
    if os.path.exists(IMAGE_PATH):
        with Image.open(IMAGE_PATH) as img:
            w, h = img.size
    else:
        print("⚠️ 警告: 找不到图片，默认使用 16:9 比例")
        w, h = 1920, 1080

    # 3. 使用 utils 打包 layout
    layout_info = process_layout_data(raw, w, h)

    # 4. 组装最终的大 JSON
    final_task = {
        "meta": logic,
        "layout_info": layout_info,
        "timeline": timeline["timeline"]
    }

    # 5. 保存
    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        json.dump(final_task, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 成功生成: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()