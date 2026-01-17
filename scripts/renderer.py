from manim import *
import json
import os
import numpy as np
from gtts import gTTS
from layout_config import UGP_CONFIG

TASK_FILE = "../题目/1/output/render_task.json"

class UGPScene(Scene):
    def construct(self):
        self.camera.background_color = UGP_CONFIG["camera_bg_color"]
        self.load_data()
        self.setup_layout_regions()
        self.show_problem_statement()
        self.calculate_figure_transform()
        self.execute_timeline()

    # ... (Layout System 代码与之前相同，省略重复部分以节省篇幅) ...
    # 这里的 setup_layout_regions 代码保持不变
    def setup_layout_regions(self):
        h = config.frame_height
        w = config.frame_width
        header_h = h * UGP_CONFIG["layout_header_h"]
        footer_h = h * UGP_CONFIG["layout_footer_h"]
        middle_h = h - header_h - footer_h
        left_w = w * UGP_CONFIG["layout_split_ratio"]
        right_w = w - left_w
        
        self.zone_header = {"center": UP * (h/2 - header_h/2), "width": w, "height": header_h}
        self.zone_footer = {"center": DOWN * (h/2 - footer_h/2), "width": w, "height": footer_h}
        center_y = (self.zone_header["center"][1] - header_h/2) - middle_h/2
        self.zone_solution = {
            "center": np.array([-w/2 + left_w/2, center_y, 0]),
            "width": left_w, "height": middle_h,
            "cursor": np.array([-w/2 + 0.5, center_y + middle_h/2 - 0.8, 0])
        }
        self.zone_figure = {
            "center": np.array([w/2 - right_w/2, center_y, 0]),
            "width": right_w, "height": middle_h
        }

    # ... (Auto-Zoom 代码保持不变) ...
    def calculate_figure_transform(self):
        coords = list(self.task_data["layout_info"]["relative_layout"].values())
        if not coords: 
            self.fig_scale = 1.0; self.fig_rel_center = np.array([0.5, 0.5, 0])
            return
        arr = np.array(coords)
        min_x, min_y = np.min(arr, axis=0)
        max_x, max_y = np.max(arr, axis=0)
        self.fig_rel_center = np.array([(min_x + max_x)/2.0, (min_y + max_y)/2.0, 0])
        span_x = max(max_x - min_x, 0.1)
        span_y = max(max_y - min_y, 0.1)
        aspect_ratio = self.task_data["layout_info"].get("aspect_ratio", 1.0)
        target_w = self.zone_figure["width"] * 0.7
        target_h = self.zone_figure["height"] * 0.7
        scale_y_based = target_h / (span_y * 8.0)
        scale_x_based = target_w / (span_x * (8.0 * aspect_ratio))
        self.fig_scale = min(scale_y_based, scale_x_based)
        self.base_unit = 8.0

    def get_coords(self, pid):
        if pid not in self.task_data["layout_info"]["relative_layout"]:
            return self.zone_figure["center"]
        rel_pos = self.task_data["layout_info"]["relative_layout"][pid]
        dx = (rel_pos[0] - self.fig_rel_center[0]) * self.task_data["layout_info"].get("aspect_ratio", 1.0)
        dy = rel_pos[1] - self.fig_rel_center[1]
        manim_dx = dx * self.base_unit * self.fig_scale
        manim_dy = -dy * self.base_unit * self.fig_scale 
        return self.zone_figure["center"] + np.array([manim_dx, manim_dy, 0])

    # ... (Execution Logic) ...
    def load_data(self):
        if not os.path.exists(TASK_FILE): raise FileNotFoundError(f"Missing {TASK_FILE}")
        with open(TASK_FILE, "r", encoding="utf-8") as f: self.task_data = json.load(f)
        self.ugp_objects = {}
        self.math_lines = [] 

    def show_problem_statement(self):
        text = self.task_data["meta"].get("problem_text", "Geometry Problem")
        disp_text = text[:45] + "..." if len(text) > 45 else text
        label = Text(disp_text, font_size=UGP_CONFIG["font_size_header"], color=UGP_CONFIG["text_main_color"])
        label.move_to(self.zone_header["center"])
        self.add(label)

    def execute_timeline(self):
        self.subtitle_obj = Text("", font_size=UGP_CONFIG["font_size_subtitle"]).move_to(self.zone_footer["center"])
        self.add(self.subtitle_obj)
        for i, step in enumerate(self.task_data["timeline"]):
            voice_text = step.get("voice", "")
            actions = step.get("actions", [])
            new_sub = Text(voice_text, font_size=UGP_CONFIG["font_size_subtitle"], color=BLACK)
            new_sub.move_to(self.zone_footer["center"])
            duration = self.play_voice(voice_text, i)
            run_time = max(duration, 1.5)
            anims = [Transform(self.subtitle_obj, new_sub)]
            for action in actions:
                anim = self.parse_action(action)
                if anim: anims.append(anim)
            if anims: self.play(AnimationGroup(*anims), run_time=run_time)

    # =======================================================
    # 🔍 核心解析逻辑 (针对你的 Timeline 进行了增强)
    # =======================================================
    def parse_action(self, action):
        op = action["op"]
        
        # 1. WRITE_MATH
        if op == "WRITE_MATH":
            content = action.get("content", "")
            tex = MathTex(content, color=UGP_CONFIG["math_color"], font_size=UGP_CONFIG["font_size_math"])
            if not self.math_lines:
                tex.move_to(self.zone_solution["cursor"], aligned_edge=UL)
            else:
                tex.next_to(self.math_lines[-1], DOWN, buff=UGP_CONFIG["math_line_buff"]).align_to(self.math_lines[-1], LEFT)
            self.math_lines.append(tex)
            return Write(tex)

        # 2. DRAW_AXES (你的 Timeline 包含此指令)
        elif op == "DRAW_AXES":
            # 注意：因为点的位置完全由 LLM 的 Layout 决定，这里的 Axes 主要是为了装饰
            # 我们根据 Figure Region 的大小画一个坐标系
            axes = Axes(
                x_range=action["params"].get("x_range", [-5, 5]),
                y_range=action["params"].get("y_range", [-5, 5]),
                axis_config={"color": GRAY, "stroke_width": 2},
                x_length=self.zone_figure["width"] * 0.9,
                y_length=self.zone_figure["height"] * 0.9
            ).move_to(self.zone_figure["center"])
            return Create(axes)

        # 3. LABEL_COORD (你的 Timeline 包含此指令)
        elif op == "LABEL_COORD":
            target = action["target"]
            text = action["text"]
            direction_str = action.get("direction", "DOWN")
            
            # 解析方向
            direction_map = {"UP": UP, "DOWN": DOWN, "LEFT": LEFT, "RIGHT": RIGHT}
            vect = direction_map.get(direction_str, DOWN)
            
            if target in self.ugp_objects:
                dot = self.ugp_objects[target]
                label = MathTex(text, color=BLACK, font_size=30).next_to(dot, vect)
                return Write(label)
            return None

        # 4. DRAW_SHAPE, DRAW_LINE, ADD_MARKER
        targets = action.get("targets", [])
        color_str = action.get("color", UGP_CONFIG["drawing_color"])
        c = getattr(ManimColor, color_str, color_str) if hasattr(ManimColor, color_str) else color_str

        if op == "DRAW_SHAPE":
            pts = [self.get_coords(p) for p in targets]
            if action.get("type") == "point":
                g = VGroup()
                for i, p in enumerate(pts):
                    d = Dot(p, color=c, radius=0.08)
                    self.ugp_objects[targets[i]] = d
                    g.add(d)
                return Create(g)
            elif action.get("type") == "poly":
                poly = Polygon(*pts, color=c)
                self.ugp_objects["".join(sorted(targets))] = poly
                return Create(poly)

        elif op == "DRAW_LINE":
            p1, p2 = self.get_coords(targets[0]), self.get_coords(targets[1])
            l = Line(p1, p2, color=c)
            if action.get("subtype") == "segment": pass # Default
            key = "".join(sorted(targets))
            self.ugp_objects[key] = l
            return Create(l)

        elif op == "ADD_MARKER":
            style = action.get("style")
            m_color = UGP_CONFIG["marker_color"]
            if style == "tick": # 画短线
                anims = []
                for t in targets: # 单点ID或线段ID，这里timeline给的是["A", "D"]点
                    # 你的JSON里: targets: ["A", "D"]，意图可能是标记线段AD，或者是标记点？
                    # 通常 tick 是标记线段相等。这里假设是标记线段 AD
                    # 如果 targets 是 ["A", "D"] 两个点，我们理解为标记线段 AD
                    if len(targets) == 2:
                         p1, p2 = self.get_coords(targets[0]), self.get_coords(targets[1])
                         l = Line(p1, p2)
                         tick = Line(UP, DOWN, color=m_color).scale(0.1).move_to(l.get_center()).rotate(l.get_angle() + PI/2)
                         return Create(tick)
            elif style == "right_angle":
                # targets: ["A", "B", "C"] -> B is corner
                pA, pB, pC = [self.get_coords(p) for p in targets]
                l1 = Line(pB, pA)
                l2 = Line(pB, pC)
                mark = RightAngle(l1, l2, length=0.3, color=m_color)
                return Create(mark)

        # 5. DRAW_ARC (你的 Timeline 包含此指令)
        elif op == "DRAW_ARC":
            # targets: [Center, Start, End] -> [A, C, M]
            if len(targets) == 3:
                center = self.get_coords(targets[0])
                start = self.get_coords(targets[1])
                end = self.get_coords(targets[2])
                
                radius = np.linalg.norm(start - center)
                
                # 计算角度 (Manim使用弧度)
                v_start = start - center
                v_end = end - center
                angle_start = np.arctan2(v_start[1], v_start[0])
                angle_end = np.arctan2(v_end[1], v_end[0])
                
                # 计算扫过的角度
                angle_diff = angle_end - angle_start
                # 简单处理：确保是画劣弧还是优弧？通常几何题画逆时针
                # 这里做一个简单的处理，保证画出来
                if angle_diff < -PI: angle_diff += 2*PI
                if angle_diff > PI: angle_diff -= 2*PI
                
                arc = Arc(radius=radius, start_angle=angle_start, angle=angle_diff, arc_center=center, color=c)
                return Create(arc)

        elif op == "HIGHLIGHT":
            anims = []
            for tid in targets:
                keys = [tid, "".join(sorted(tid))]
                obj = None
                for k in keys:
                    if k in self.ugp_objects: obj = self.ugp_objects[k]
                if obj:
                    anims.append(Indicate(obj, color=UGP_CONFIG["highlight_color"], scale_factor=1.5))
            if anims: return AnimationGroup(*anims)

        return None

    def play_voice(self, text, idx):
        if not text: return 0.5
        path = f"temp/voice_{idx}.mp3"
        os.makedirs("temp", exist_ok=True)
        try:
            if not os.path.exists(path):
                tts = gTTS(text=text, lang='en') # 你的timeline是英文
                tts.save(path)
            self.add_sound(path)
            return len(text) * 0.1 + 0.5 # 英文语速估算
        except:
            return 1.0