import json
import os
from PIL import Image
from utils import normalize_coords

# ================= Configuration =================
# 定义输入输出路径 (在 pipeline 中通常由主控脚本传入，这里为了独立运行写在配置里)
IMAGE_PATH = "input/problem.jpg"             # 真实来源：原始图片
RAW_LAYOUT_PATH = "output/p2_raw_output.json" # 真实来源：P2 LLM 的输出文件
OUTPUT_PATH = "output/final_layout.json"      # 目的地：清洗后的数据

def main():
    print("🚀 开始执行坐标归一化 (Production Mode)...")

    # -------------------------------------------------
    # 1. 动态获取图片真实尺寸 (Source of Truth: Image)
    # -------------------------------------------------
    if not os.path.exists(IMAGE_PATH):
        print(f"❌ 错误：找不到图片文件: {IMAGE_PATH}")
        return

    # 只读取头部信息，不加载整个图片数据，速度很快
    with Image.open(IMAGE_PATH) as img:
        real_width, real_height = img.size
        print(f"📏 [读取成功] 图片真实尺寸: {real_width} x {real_height}")

    # -------------------------------------------------
    # 2. 动态加载 LLM 的原始输出 (Source of Truth: P2 JSON)
    # -------------------------------------------------
    if not os.path.exists(RAW_LAYOUT_PATH):
        print(f"❌ 错误：找不到 P2 的输出文件: {RAW_LAYOUT_PATH}")
        print("💡 提示：请先运行 P2 步骤生成原始坐标数据。")
        return

    try:
        with open(RAW_LAYOUT_PATH, "r", encoding="utf-8") as f:
            llm_data = json.load(f)
            
            # 防御性编程：检查 key 是否存在
            if "layout_map" not in llm_data:
                raise ValueError("JSON 中缺少 'layout_map' 字段")
            
            raw_layout_map = llm_data["layout_map"]
            print(f"📥 [读取成功] 获取到 {len(raw_layout_map)} 个点的原始坐标")
            
    except Exception as e:
        print(f"❌ JSON 读取或解析失败: {e}")
        return

    # -------------------------------------------------
    # 3. 执行核心算法 (引用 utils)
    # -------------------------------------------------
    print("🔄 正在计算坐标映射...")
    
    # 这一步完全基于读取到的 real_width/height 和 raw_layout_map
    final_layout, canvas_size = normalize_coords(raw_layout_map, real_width, real_height)

    # -------------------------------------------------
    # 4. 保存结果到文件
    # -------------------------------------------------
    output_data = {
        "meta_info": {
            "source_image": IMAGE_PATH,
            "original_size": [real_width, real_height],
            "logic_canvas_size": canvas_size
        },
        "layout": final_layout
    }

    # 自动创建输出目录
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"✅ [完成] 归一化数据已保存至: {OUTPUT_PATH}")
    print(f"   逻辑画布尺寸: {canvas_size}")
    print("👉 下一步：Renderer 将读取此文件进行绘图。")

if __name__ == "__main__":
    main()