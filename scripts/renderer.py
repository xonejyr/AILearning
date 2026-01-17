from manim import *
import json
import os
import numpy as np
from pydub import AudioSegment

# ==========================================
# 环境变量配置 (保持不变)
# ==========================================
# ffmpeg_bin_dir = r"C:\Program Files\ffmpeg-8.0.1-essentials_build\bin"
# os.environ["PATH"] += os.pathsep + ffmpeg_bin_dir
# AudioSegment.converter = os.path.join(ffmpeg_bin_dir, "ffmpeg.exe")
# AudioSegment.ffprobe   = os.path.join(ffmpeg_bin_dir, "ffprobe.exe")

# 显式指向你 ffmpeg 的路径，这样 pydub 就不再瞎找了
AudioSegment.converter = r"C:\ffmpeg\bin\ffmpeg.exe" 
AudioSegment.ffprobe = r"C:\ffmpeg\bin\ffprobe.exe"

class GeometryRenderer(Scene):
    def construct(self):
        # 1. 基础配置
        self.camera.background_color = "#FFFFFF"
        self.font_name = "Microsoft YaHei"
        
        # 布局常量 (Manim 坐标系: 宽[-7.1, 7.1], 高[-4, 4])
        self.layout = {
            "header_top": 3.5,
            "divider_x": 1.0,         # 分割线位置 (偏右，留更多空间给左图)
            "right_text_x": 4.0,      # 右侧文字中心 x 坐标
            "right_text_width": 5.5,  # 右侧文字最大宽度 (Manim单位)
            "drawing_center": np.array([-3.0, -0.5, 0]) # 左侧绘图中心
        }

        # 2. 加载数据
        try:
            self.load_data()
        except Exception as e:
            print(f"数据加载错误: {e}")
            return

        # 3. 初始化场景
        self.setup_layout()

        # 4. 执行步骤
        for i, step in enumerate(self.steps):
            self.execute_step(step, i)

        self.wait(2)

    def load_data(self):
        # 假设 JSON 路径由外部传入或固定
        with open("./几何/题目1_坐标映射.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            self.coords_map = data.get("Points", {})
            self.lines_map = data.get("Lines", {})
            # 读取画布缩放比例，默认为 0.012
            self.scale_factor = data.get("Config", {}).get("scale", 0.012)
            
        with open("./几何/题目1_教学指令.json", "r", encoding="utf-8") as f:
            self.steps = json.load(f)

    def setup_layout(self):
        # 绘制分割线
        self.add(Line(UP*4, DOWN*4, color="#EEEEEE", stroke_width=2).shift(RIGHT * self.layout["divider_x"]))
        self.right_vgroup = VGroup() # 用于堆叠右侧板书

    def execute_step(self, data, step_index):
        action = data.get("action")
        speech = data.get("speech", "")
        board_text = data.get("text_right", "")
        
        # --- 1. 音频同步 ---
        audio_path = f"audio/step_{step_index + 1}.mp3"
        duration = self.get_safe_duration(audio_path)
        
        if os.path.exists(audio_path):
            self.add_sound(audio_path)
        
        # --- 2. 底部字幕 ---
        # 使用 Paragraph 实现字幕自动换行，防止超出底部
        subtitle = Paragraph(speech, font=self.font_name, font_size=18, color=BLACK, width=12)
        subtitle.to_edge(DOWN, buff=0.2)
        self.add(subtitle)

        # --- 3. 右侧板书 (核心优化：防溢出) ---
        new_board_content = VGroup()
        if board_text:
            lines = board_text.split('\n')
            for line in lines:
                if not line.strip(): continue
                # 智能渲染：尝试 LaTeX，失败则回退到 Text
                elem = self.create_smart_text(line)
                new_board_content.add(elem)
            
            # 左对齐排列
            new_board_content.arrange(DOWN, aligned_edge=LEFT, buff=0.15)
            
            # 布局管理：如果已有内容，接在下面；否则放在顶部
            if len(self.right_vgroup) > 0:
                new_board_content.next_to(self.right_vgroup, DOWN, aligned_edge=LEFT, buff=0.5)
            else:
                # 初始位置：分割线右侧 + 顶部偏移
                new_board_content.move_to(np.array([self.layout["right_text_x"], 2.0, 0]))
                new_board_content.to_edge(RIGHT, buff=0.5).shift(UP*2)

            # 缩放检查：如果宽度过大，进行缩放
            if new_board_content.width > self.layout["right_text_width"]:
                new_board_content.scale(self.layout["right_text_width"] / new_board_content.width)

        # --- 4. 绘图动作 (完全基于数据驱动) ---
        anim_group = [Write(new_board_content)]
        
        if action == "SETUP_HEADER":
            # 题目显示：支持多行
            header_text = data.get("content", "")
            header = Paragraph(header_text, font=self.font_name, font_size=20, color=BLACK, width=13, alignment="left")
            header.to_corner(UL, buff=0.5)
            self.add(header)
            
            # 初始数轴绘制 (如果有)
            if "Number_Line" in self.lines_map:
                l = self.lines_map["Number_Line"]
                start, end = self.p2m(l[0]), self.p2m(l[1])
                anim_group.append(Create(Arrow(start, end, color=BLACK, buff=0, stroke_width=2)))
                # 绘制刻度
                ticks = VGroup()
                for t in self.lines_map.get("Ticks", []):
                    p = self.p2m(t)
                    ticks.add(Line(p+DOWN*0.1, p+UP*0.1, color=BLACK))
                anim_group.append(Create(ticks))

        elif action == "DRAW_POLY":
            pts = [self.p2m(t) for t in data["targets"]]
            poly = Polygon(*pts, color=BLUE, stroke_width=3).set_fill(BLUE, opacity=0.1)
            # 自动生成顶点标签
            labels = VGroup()
            for i, tid in enumerate(data["targets"]):
                labels.add(Text(tid, font=self.font_name, font_size=16, color=BLACK).next_to(pts[i], UR, buff=0.1))
            anim_group.extend([Create(poly), Write(labels)])

        elif action == "DRAW_LINE":
            p1, p2 = self.p2m(data["targets"][0]), self.p2m(data["targets"][1])
            line = DashedLine(p1, p2, color=GRAY) if data.get("style") == "dashed" else Line(p1, p2, color=BLACK)
            anim_group.append(Create(line))

        elif action == "DRAW_ARC":
            # 约定：targets[0]=圆心, targets[1]=起点, targets[2]=终点
            c_id, s_id, e_id = targets[0], targets[1], targets[2]

            center = self.to_manim(c_id)
            start = self.to_manim(s_id)
            end = self.to_manim(e_id)

            # 自动计算半径
            radius = np.linalg.norm(start - center)

            # 画弧：ArcBetweenPoints 会自动处理圆弧轨迹
            # 如果弧线方向反了，可以尝试切换 start 和 end，或者增加 angle 参数
            arc = ArcBetweenPoints(start, end, radius=radius, color=YELLOW)

            self.play(Create(arc), run_time=duration)
            self.drawn_objects[f"arc_{c_id}"] = arc

        elif action == "HIGHLIGHT":
            # 通用高亮：支持点、线
            targets = data.get("targets", [])
            mobjects = []
            for t in targets:
                # 简单处理：如果是点ID，高亮该点位置
                mobjects.append(Dot(self.p2m(t), color=RED))
            anim_group.append(AnimationGroup(*[Indicate(m) for m in mobjects]))

        # --- 5. 执行与等待 ---
        # 预留 0.5 秒给观众消化，防止语音结束立刻切屏
        anim_time = min(duration, 2.5) 
        self.play(*anim_group, run_time=anim_time)
        
        wait_time = duration - anim_time
        if wait_time > 0:
            self.wait(wait_time)

        self.right_vgroup.add(new_board_content)
        self.remove(subtitle)

    # --- 辅助函数 ---
    def p2m(self, point_identifier):
        """像素坐标 -> Manim坐标"""
        if isinstance(point_identifier, str):
            px = self.coords_map.get(point_identifier, [0,0])
        else:
            px = point_identifier # 如果直接传入 [x, y]
        
        # 使用 self.layout["drawing_center"] 动态调整
        mx = (px[0] - 250) * self.scale_factor + self.layout["drawing_center"][0]
        my = (500 - px[1]) * self.scale_factor + self.layout["drawing_center"][1]
        return np.array([mx, my, 0])

    def get_safe_duration(self, path):
        if not os.path.exists(path): return 3.0
        try: return len(AudioSegment.from_file(path)) / 1000.0
        except: return 3.0

    def create_smart_text(self, text_str):
        """智能文本工厂：自动判断是否用 LaTeX，自动换行"""
        # 简单判断是否包含中文
        has_cjk = any('\u4e00' <= char <= '\u9fa5' for char in text_str)
        
        if not has_cjk and any(c in text_str for c in "=^√"):
            # 纯数学公式
            tex = text_str.replace("√", r"\sqrt{").replace("²", "}^2")
            if r"\sqrt{" in tex and "}" not in tex: tex += "}"
            return MathTex(tex, color=DARK_GRAY, font_size=28)
        else:
            # 混合文本，使用 Paragraph 进行自动换行（宽度限制）
            return Paragraph(text_str, font=self.font_name, font_size=16, color=DARK_GRAY, width=5)