import os
from utils import add_smart_grid

# 假设你的原图放在这里
INPUT_IMAGE = "../题目/1/题目1_题目.jpg"  
OUTPUT_IMAGE = "../题目/1/题目1_题目_grid.jpg"

def main():
    if not os.path.exists(INPUT_IMAGE):
        print(f"❌ 错误：找不到文件 {INPUT_IMAGE}，请先放一张图。")
        return

    print(f"🖼️ 正在处理图片: {INPUT_IMAGE} ...")
    
    # 调用 utils 函数
    w, h = add_smart_grid(INPUT_IMAGE, OUTPUT_IMAGE)
    
    print(f"✅ 网格图已生成: {OUTPUT_IMAGE}")
    print(f"📏 原始尺寸: {w} x {h}")
    print(f"📐 逻辑最长边: 1000")
    print("-" * 30)
    print("👉 下一步：把这张 temp_grid_for_llm.jpg 发给 P2 大模型。")

if __name__ == "__main__":
    main()