from manim import *
import json
import os
import numpy as np
import textwrap  # <--- 新增：用于文本自动换行
from gtts import gTTS
from layout_config import UGP_CONFIG

TASK_FILE = "../题目/1/output/render_task.json"

class UGPScene(Scene):
    def construct(self):
        self.camera.background_color = UGP_CONFIG["camera_bg_color"]
        self.load_data()
        self.setup_layout_regions()
        
        # 1. 显示题目 (已修复溢出问题)
        self.show_problem_statement()

        # 2. 计算几何变换 (保留了抗扁平逻辑)
        self.calculate_figure_transform()

        # 3. 执行剧本
        self.execute_timeline()

    # =======================================================
    # 🏗️ 布局系统
    # =======================================================
    def setup_layout_regions(self):
        h = config.frame_height
        w = config.frame_width
        
        header_h = h * UGP_CONFIG["layout_header_h"]
        footer_h = h * UGP_CONFIG["layout_footer_h"]
        middle_h = h - header_h - footer_h
        left_w = w * UGP_CONFIG["layout_split_ratio"]
        right_w = w - left_w
        
        # Header
        self.zone_header = {"center": UP * (h/2 - header_h/2), "width": w, "height": header_h}
        # Footer
        self.zone_footer = {"center": DOWN * (h/2 - footer_h/2), "width": w, "height": footer_h}
        
        center_y = (self.zone_header["center"][1] - header_h/2) - middle_h/2
        
        # Solution (Left)
        self.zone_solution = {
            "center": np.array([-w/2 + left_w/2, center_y, 0]),
            "width": left_w, "height": middle_h,
            "cursor": np.array([-w/2 + 0.5, center_y + middle_h/2 - 0.8, 0])
        }
        # Figure (Right)
        self.zone_figure = {
            "center": np.array([w/2 - right_w/2, center_y, 0]),
            "width": right_w, "height": middle_h
        }

    # =======================================================
    # 📝 核心修复：题目显示 (自动换行 + 自动缩放)
    # =======================================================
    def show_problem_statement(self):
        raw_text = self.task_data["meta"].get("problem_text", "Geometry Problem")
        
        # 1. 自动换行算法
        # 估算：屏幕宽度约 14 单位，每行约容纳 60-70 个英文字符或 30-35 个中文字符
        # 这里设置为 50 比较安全
        wrapped_text_list = textwrap.wrap(raw_text, width=50)
        formatted_text = "\n".join(wrapped_text_list)
        
        # 2. 创建文本对象
        label = Text(
            formatted_text, 
            font_size=UGP_CONFIG["font_size_header"], 
            color=UGP_CONFIG["text_main_color"],
            line_spacing=1.2,
            weight=BOLD
        )
        
        # 3. 碰撞检测与自动缩放 (Auto-Fit)
        # 获取 Header 区域的最大允许宽高 (留 10% 边距)
        max_w = self.zone_header["width"] * 0.9
        max_h = self.zone_header["height"] * 0.9
        
        # 如果太宽，缩放
        if label.width > max_w:
            label.scale(max_w / label.width)
            
        # 如果太高 (行数太多)，继续缩放
        if label.height > max_h:
            label.scale(max_h / label.height)
            
        label.move_to(self.zone_header["center"])
        self.add(label)

    # =======================================================
    # 📐 抗扁平与自动构图
    # =======================================================
    def calculate_figure_transform(self):
        coords = list(self.task_data["layout_info"]["relative_layout"].values())
        if not coords: 
            self.fig_scale = 1.0; self.fig_rel_center = np.array([0.5, 0.5, 0]); return

        # 获取真实长宽比
        self.img_aspect = self.task_data["layout_info"].get("aspect_ratio", 1.77)

        # 还原物理坐标以计算包围盒
        phys_coords = []
        for p in coords:
            phys_coords.append([p[0] * self.img_aspect, p[1]])
        
        arr = np.array(phys_coords)
        min_x, min_y = np.min(arr, axis=0)
        max_x, max_y = np.max(arr, axis=0)
        
        self.phys_center = np.array([(min_x + max_x)/2.0, (min_y + max_y)/2.0, 0])
        
        span_x = max(max_x - min_x, 0.2)
        span_y = max(max_y - min_y, 0.2)
        
        # 缩放倍率计算
        target_w = self.zone_figure["width"] * 0.75
        target_h = self.zone_figure["height"] * 0.75
        
        # 基准单位 8.0
        scale_x = target_w / (span_x * 8.0)
        scale_y = target_h / (span_y * 8.0)
        
        self.fig_scale = min(scale_x, scale_y) * 8.0

    def get_coords(self, pid):
        if pid not in self.task_data["layout_info"]["relative_layout"]:
            return self.zone_figure["center"]
        rel_pos = self.task_data["layout_info"]["relative_layout"][pid]
        
        # 物理坐标还原
        phys_x = rel_pos[0] * self.img_aspect
        phys_y = rel_pos[1]
        
        dx = phys_x - self.phys_center[0]
        dy = phys_y - self.phys_center[1]
        
        # 缩放、翻转Y、平移
        manim_dx = dx * self.fig_scale
        manim_dy = -dy * self.fig_scale 
        
        return self.zone_figure["center"] + np.array([manim_dx, manim_dy, 0])

    # =======================================================
    # 🎬 执行与动作解析
    # =======================================================
    def load_data(self):
        if not os.path.exists(TASK_FILE): raise FileNotFoundError(f"Missing {TASK_FILE}")
        with open(TASK_FILE, "r", encoding="utf-8") as f: self.task_data = json.load(f)
        self.ugp_objects = {}; self.math_lines = [] 

    def execute_timeline(self):
        self.subtitle_obj = Text("", font_size=UGP_CONFIG["font_size_subtitle"]).move_to(self.zone_footer["center"])
        self.add(self.subtitle_obj)

        for i, step in enumerate(self.task_data["timeline"]):
            voice_text = step.get("voice", "")
            actions = step.get("actions", [])
            
            # 字幕直接切换 (无特效)
            new_sub = Text(voice_text, font_size=UGP_CONFIG["font_size_subtitle"], color=BLACK)
            # 字幕自动换行处理 (简单版)
            if len(voice_text) > 50:
                 new_sub = Text("\n".join(textwrap.wrap(voice_text, 50)), font_size=UGP_CONFIG["font_size_subtitle"]*0.8, color=BLACK)
            new_sub.move_to(self.zone_footer["center"])
            
            self.remove(self.subtitle_obj)
            self.add(new_sub)
            self.subtitle_obj = new_sub
            
            duration = self.play_voice(voice_text, i)
            run_time = max(duration, 1.5)

            anims = []
            for action in actions:
                anim = self.parse_action(action)
                if anim: anims.append(anim)
            
            if anims:
                self.play(AnimationGroup(*anims), run_time=run_time)
            else:
                self.wait(run_time)

    def parse_action(self, action):
        op = action["op"]
        
        if op == "WRITE_MATH":
            content = action.get("content", "")
            tex = MathTex(content, color=UGP_CONFIG["math_color"], font_size=UGP_CONFIG["font_size_math"])
            if not self.math_lines: tex.move_to(self.zone_solution["cursor"], aligned_edge=UL)
            else: tex.next_to(self.math_lines[-1], DOWN, buff=0.4).align_to(self.math_lines[-1], LEFT)
            self.math_lines.append(tex)
            return Write(tex)

        elif op == "DRAW_AXES":
            # 增强版：如果是 1D 数轴，画 NumberLine；如果是 2D，画 Axes
            params = action.get("params", {})
            # 简单判断：如果 y_range 很小，或者是 layout 中所有点 Y 坐标都差不多，可能是数轴
            # 但这里最稳妥的是看 params
            
            # 默认画 1D 数轴 (因为很多几何题是数轴)
            x_min, x_max = params.get("x_range", [-5, 5])[:2]
            
            number_line = NumberLine(
                x_range=[x_min, x_max, 1],
                length=self.zone_figure["width"] * 0.9,
                color=GRAY,
                include_numbers=True,
                label_direction=DOWN
            ).move_to(self.zone_figure["center"] + DOWN) # 下移一点，让图形在上面
            return Create(number_line)

        elif op == "DRAW_ARC":
            if len(action.get("targets", [])) >= 3:
                # ... (圆弧逻辑同上一个版本，保持不变) ...
                c_id, s_id, e_id = action["targets"][:3]
                p_c, p_s, p_m = self.get_coords(c_id), self.get_coords(s_id), self.get_coords(e_id)
                radius = np.linalg.norm(p_s - p_c)
                v_s, v_e = p_s - p_c, p_m - p_c
                ang_s = np.arctan2(v_s[1], v_s[0])
                ang_e = np.arctan2(v_e[1], v_e[0])
                if ang_e < ang_s: ang_e += TAU
                arc = Arc(radius=radius, start_angle=ang_s, angle=ang_e-ang_s, arc_center=p_c, color=UGP_CONFIG["drawing_color"])
                return Create(arc)

        # 自动画字母逻辑
        elif op == "DRAW_SHAPE":
            targets = action.get("targets", [])
            pts = [self.get_coords(p) for p in targets]
            color = action.get("color", UGP_CONFIG["drawing_color"])
            g = VGroup()
            
            if action.get("type") == "point":
                for i, p in enumerate(pts):
                    d = Dot(p, color=color)
                    l = Tex(targets[i], color=BLACK, font_size=30).next_to(d, UP*0.3)
                    g.add(d, l)
                    self.ugp_objects[targets[i]] = d
            else:
                poly = Polygon(*pts, color=color)
                g.add(poly)
                self.ugp_objects["".join(sorted(targets))] = poly
                for i, p in enumerate(pts):
                    # 智能方向：从中心向外
                    center = poly.get_center()
                    direction = normalize(p - center)
                    if np.linalg.norm(direction) == 0: direction = UP
                    l = Tex(targets[i], color=BLACK, font_size=30).next_to(p, direction * 0.3)
                    g.add(l)
            return Create(g)

        elif op == "DRAW_LINE":
            # ... (同前) ...
            targets = action.get("targets", [])
            p1, p2 = self.get_coords(targets[0]), self.get_coords(targets[1])
            l = Line(p1, p2, color=UGP_CONFIG["drawing_color"])
            if action.get("type") == "dashed": l = DashedLine(p1, p2, color=UGP_CONFIG["drawing_color"])
            return Create(l)

        elif op == "ADD_MARKER":
             # ... (同前) ...
             style = action.get("style")
             if style == "tick" and len(action.get("targets", [])) >= 2:
                 p1, p2 = self.get_coords(action["targets"][0]), self.get_coords(action["targets"][1])
                 tick = Line(UP, DOWN, color=UGP_CONFIG["marker_color"]).scale(0.1).move_to(Line(p1,p2).get_center()).rotate(Line(p1,p2).get_angle()+PI/2)
                 return Create(tick)
             elif style == "right_angle":
                 pA, pB, pC = [self.get_coords(p) for p in action["targets"]]
                 return Create(RightAngle(Line(pB, pA), Line(pB, pC), length=0.3, color=UGP_CONFIG["marker_color"]))

        elif op == "HIGHLIGHT":
             # ... (同前) ...
             anims = []
             for tid in action.get("targets", []):
                 keys = [tid, "".join(sorted(tid))]
                 obj = None
                 for k in keys: 
                     if k in self.ugp_objects: obj = self.ugp_objects[k]
                 if obj: anims.append(Indicate(obj, color=UGP_CONFIG["highlight_color"], scale_factor=1.5))
             if anims: return AnimationGroup(*anims)
             
        elif op == "LABEL_COORD":
            # ... (同前) ...
            target = action["target"]
            if target in self.ugp_objects:
                dot = self.ugp_objects[target]
                vect = {"UP": UP, "DOWN": DOWN}.get(action.get("direction", "DOWN"), DOWN)
                return Write(MathTex(action["text"], color=BLACK, font_size=24).next_to(dot, vect))

        return None

    def play_voice(self, text, idx):
        if not text: return 0.5
        path = f"temp/voice_{idx}.mp3"
        os.makedirs("temp", exist_ok=True)
        try:
            if not os.path.exists(path):
                gTTS(text=text, lang='en').save(path)
            self.add_sound(path)
            return len(text) * 0.1 + 0.5
        except: return 1.0