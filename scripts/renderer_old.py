from manim import *
import json
import os
import numpy as np
from gtts import gTTS
from ugp_config import UGP_CONFIG  # 导入配置

TASK_FILE = "data/render_task.json"

class UGPScene(Scene):
    def construct(self):
        # 1. 初始化设置
        self.camera.background_color = UGP_CONFIG["camera_bg_color"]
        self.load_data()
        
        # 2. 布局初始化 (计算分区坐标)
        self.setup_layout_regions()
        
        # 3. 显示题目 (Top)
        self.show_problem_statement()

        # 4. 计算右侧绘图区的自动缩放 (关键算法)
        self.calculate_figure_transform()

        # 5. 执行时间轴
        self.execute_timeline()

    # =======================================================
    # 🏗️ 布局系统
    # =======================================================
    def setup_layout_regions(self):
        """根据配置文件计算四个区域的中心点和边界"""
        h = config.frame_height
        w = config.frame_width
        
        # 读取比例
        header_h = h * UGP_CONFIG["layout_header_h"]
        footer_h = h * UGP_CONFIG["layout_footer_h"]
        middle_h = h - header_h - footer_h
        left_w = w * UGP_CONFIG["layout_split_ratio"]
        right_w = w - left_w
        
        # 1. Header (Top)
        self.zone_header = {
            "center": UP * (h/2 - header_h/2),
            "width": w, "height": header_h
        }
        
        # 2. Footer (Bottom)
        self.zone_footer = {
            "center": DOWN * (h/2 - footer_h/2),
            "width": w, "height": footer_h
        }
        
        # 计算中间区域的 Y 中心
        center_y = (self.zone_header["center"][1] - header_h/2) - middle_h/2
        
        # 3. Solution Region (Left)
        self.zone_solution = {
            "center": np.array([-w/2 + left_w/2, center_y, 0]),
            "width": left_w, "height": middle_h,
            # 光标初始位置：左上角 (带一点 padding)
            "cursor": np.array([-w/2 + 0.5, center_y + middle_h/2 - 0.5, 0])
        }
        
        # 4. Figure Region (Right)
        self.zone_figure = {
            "center": np.array([w/2 - right_w/2, center_y, 0]),
            "width": right_w, "height": middle_h
        }

    # =======================================================
    # 📐 自动构图算法 (Auto-Zoom)
    # =======================================================
    def calculate_figure_transform(self):
        """
        无论 LLM 返回的坐标在原图的哪个角落，
        这个函数都会把它映射并充满右侧的 Figure Region。
        """
        # 获取相对坐标 (0.0 - 1.0)
        coords = list(self.task_data["layout_info"]["relative_layout"].values())
        if not coords: 
            self.fig_scale = 1.0
            self.fig_offset = ORIGIN
            self.fig_rel_center = np.array([0.5, 0.5, 0])
            return

        # 1. 计算相对坐标的包围盒
        arr = np.array(coords)
        min_x, min_y = np.min(arr, axis=0)
        max_x, max_y = np.max(arr, axis=0)
        
        # 相对中心
        rel_center_x = (min_x + max_x) / 2.0
        rel_center_y = (min_y + max_y) / 2.0
        self.fig_rel_center = np.array([rel_center_x, rel_center_y, 0])
        
        # 相对跨度 (防止单点导致除以0)
        span_x = max(max_x - min_x, 0.1)
        span_y = max(max_y - min_y, 0.1)
        
        # 2. 计算原图长宽比带来的影响
        # aspect_ratio > 1 说明是宽图，< 1 说明是高图
        aspect_ratio = self.task_data["layout_info"].get("aspect_ratio", 1.0)
        
        # 3. 目标容器大小 (Manim 单位)
        target_w = self.zone_figure["width"] * 0.8  # 留20%边距
        target_h = self.zone_figure["height"] * 0.8
        
        # 4. 计算缩放倍率
        # 物理跨度 = 相对跨度 * (假设的全屏尺寸)
        # 这里我们需要将相对坐标 (0-1) 转换为一种物理中间态
        # 假设 Manim 屏幕高度 8.0 对应 相对高度 1.0
        
        # 如果 Y 轴铺满：Scale = target_h / span_y
        scale_y_based = target_h / (span_y * 8.0) # 8.0 是 Manim 默认全高
        
        # 如果 X 轴铺满：Scale = target_w / span_x
        # 这里的 X 轴长度要考虑图片比例。
        # 如果图片很宽 (Ratio=2.0)，那么相对 x=1.0 代表物理长度 16.0
        scale_x_based = target_w / (span_x * (8.0 * aspect_ratio))
        
        # 取最小值，保证能塞进去
        self.fig_scale = min(scale_y_based, scale_x_based)
        
        # 基础乘数 (将相对坐标放大到 Manim 可见的数量级)
        self.base_unit = 8.0 

    def get_coords(self, pid):
        """核心坐标变换：相对 -> 局部居中"""
        if pid not in self.task_data["layout_info"]["relative_layout"]:
            return self.zone_figure["center"]
            
        rel_pos = self.task_data["layout_info"]["relative_layout"][pid]
        rx, ry = rel_pos[0], rel_pos[1]
        
        # 1. 归零 (相对于几何群组中心)
        dx = rx - self.fig_rel_center[0]
        dy = ry - self.fig_rel_center[1]
        
        # 2. 考虑长宽比 (Aspect Ratio Correction)
        aspect_ratio = self.task_data["layout_info"].get("aspect_ratio", 1.0)
        phys_dx = dx * aspect_ratio # 修正 X 轴的物理跨度
        
        # 3. 缩放
        manim_dx = phys_dx * self.base_unit * self.fig_scale
        manim_dy = -dy * self.base_unit * self.fig_scale # Y 轴翻转
        
        # 4. 平移到区域中心
        return self.zone_figure["center"] + np.array([manim_dx, manim_dy, 0])

    # =======================================================
    # 🎬 执行逻辑
    # =======================================================
    def load_data(self):
        if not os.path.exists(TASK_FILE): raise FileNotFoundError("No task file")
        with open(TASK_FILE, "r", encoding="utf-8") as f: self.task_data = json.load(f)
        self.ugp_objects = {}
        self.math_lines = [] 

    def show_problem_statement(self):
        text = self.task_data["meta"].get("problem_text", "Geometry Problem")
        # 简单的截断处理
        disp_text = text[:50] + "..." if len(text) > 50 else text
        
        label = Text(disp_text, font_size=UGP_CONFIG["font_size_header"], color=UGP_CONFIG["text_main_color"])
        label.move_to(self.zone_header["center"])
        self.add(label)

    def execute_timeline(self):
        self.subtitle_obj = Text("", font_size=UGP_CONFIG["font_size_subtitle"]).move_to(self.zone_footer["center"])
        self.add(self.subtitle_obj)

        for i, step in enumerate(self.task_data["timeline"]):
            voice_text = step.get("voice", "")
            actions = step.get("actions", [])
            
            # 1. 字幕
            new_sub = Text(voice_text, font_size=UGP_CONFIG["font_size_subtitle"], color=BLACK)
            new_sub.move_to(self.zone_footer["center"])
            
            # 2. 语音
            duration = self.play_voice(voice_text, i)
            run_time = max(duration, 1.5)

            # 3. 动作
            anims = [Transform(self.subtitle_obj, new_sub)]
            
            for action in actions:
                anim = self.parse_action(action)
                if anim: anims.append(anim)
            
            self.play(AnimationGroup(*anims), run_time=run_time)

    def parse_action(self, action):
        op = action["op"]
        
        # --- A. 数学公式 (投递到左侧 Solution Region) ---
        if op == "WRITE_MATH":
            content = action.get("content", "")
            tex = MathTex(content, color=UGP_CONFIG["math_color"], font_size=UGP_CONFIG["font_size_math"])
            
            if not self.math_lines:
                tex.move_to(self.zone_solution["cursor"], aligned_edge=UL)
            else:
                last_line = self.math_lines[-1]
                tex.next_to(last_line, DOWN, buff=UGP_CONFIG["math_line_buff"])
                tex.align_to(last_line, LEFT)
            
            self.math_lines.append(tex)
            return Write(tex)

        # --- B. 几何绘图 (投递到右侧 Figure Region) ---
        targets = action.get("targets", [])
        color = action.get("color", UGP_CONFIG["drawing_color"])
        
        if op == "DRAW_SHAPE":
            pts = [self.get_coords(p) for p in targets]
            if action.get("type") == "point":
                g = VGroup()
                for i, p in enumerate(pts):
                    d = Dot(p, color=color)
                    l = Tex(targets[i], color=BLACK, font_size=24).next_to(d, UP*0.2)
                    g.add(d, l)
                    self.ugp_objects[targets[i]] = d
                return Create(g)
            else:
                poly = Polygon(*pts, color=color)
                # 保存组合ID，例如 "ABC"
                key = "".join(sorted(targets))
                self.ugp_objects[key] = poly
                return Create(poly)

        elif op == "DRAW_LINE":
            p1, p2 = self.get_coords(targets[0]), self.get_coords(targets[1])
            l = Line(p1, p2, color=color)
            if action.get("type") == "dashed": l = DashedLine(p1, p2, color=color)
            key = "".join(sorted(targets))
            self.ugp_objects[key] = l
            return Create(l)
            
        elif op == "HIGHLIGHT":
            # 查找对象逻辑 (简化版)
            anims = []
            for tid in targets:
                # 尝试单点ID 或 组合ID
                keys = [tid, "".join(sorted(tid))]
                obj = None
                for k in keys:
                    if k in self.ugp_objects: obj = self.ugp_objects[k]
                
                if obj:
                    anims.append(Indicate(obj, color=UGP_CONFIG["highlight_color"], scale_factor=1.2))
            if anims: return AnimationGroup(*anims)
            
        return None

    def play_voice(self, text, idx):
        if not text: return 0.5
        path = f"temp/voice_{idx}.mp3"
        os.makedirs("temp", exist_ok=True)
        try:
            if not os.path.exists(path):
                tts = gTTS(text=text, lang='zh-cn')
                tts.save(path)
            self.add_sound(path)
            # 估算时长: 中文约每秒3.5字
            return len(text) * 0.28 + 0.5
        except:
            return 1.0