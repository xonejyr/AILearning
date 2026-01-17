from PIL import Image, ImageDraw, ImageFont
import math

# ==========================================
# 1. 生成相对网格 (10x10 Grid, 0.0-1.0)
# ==========================================
def add_smart_grid(image_path, output_path):
    """
    给图片叠加 10x10 的红色网格，标注 0.0 - 1.0。
    用于让 LLM 进行相对坐标估算。
    """
    with Image.open(image_path).convert("RGBA") as base:
        width, height = base.size
        
        # 创建覆盖层
        overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        
        # 颜色配置
        line_color = (255, 0, 0, 128)  # 半透明红
        text_color = (255, 0, 0, 255)  # 实心红
        
        # 字体大小自适应 (宽度的 2%)
        try:
            font_size = max(12, int(width * 0.02))
            font = ImageFont.truetype("arial.ttf", size=font_size)
        except:
            font = ImageFont.load_default()

        # 步长 (十分之一)
        step_x = width / 10.0
        step_y = height / 10.0

        # 画竖线 (X轴 0.0 - 1.0)
        for i in range(11):
            x = int(i * step_x)
            # 修正边缘防止画出界
            if x >= width: x = width - 1
            
            draw.line([(x, 0), (x, height)], fill=line_color, width=2)
            # 标注 (0.1, 0.2...)
            label = f"{i/10:.1f}"
            draw.text((x + 2, 5), label, fill=text_color, font=font)

        # 画横线 (Y轴 0.0 - 1.0)
        for i in range(11):
            y = int(i * step_y)
            if y >= height: y = height - 1
            
            draw.line([(0, y), (width, y)], fill=line_color, width=2)
            label = f"{i/10:.1f}"
            draw.text((5, y + 2), label, fill=text_color, font=font)

        # 合并保存
        out = Image.alpha_composite(base, overlay)
        out.convert("RGB").save(output_path, quality=95)
        
        # 返回真实宽高，供 Renderer 计算长宽比
        return width, height

# ==========================================
# 2. 归一化处理 (数据打包)
# ==========================================
def process_layout_data(llm_raw_data, real_width, real_height):
    """
    输入：LLM 返回的相对坐标 {"A": [0.5, 0.5]}
    处理：计算图片真实长宽比，打包数据。
    输出：Renderer 所需的 layout_info 结构。
    """
    aspect_ratio = real_width / real_height
    
    return {
        "aspect_ratio": aspect_ratio,     # 关键：告诉 Renderer 原图是扁的还是长的
        "relative_layout": llm_raw_data   # 透传坐标
    }