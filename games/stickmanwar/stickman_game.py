import tkinter as tk
from PIL import Image, ImageTk
import math
import random
import os

# Windows sound fallback
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# ==========================================
# PATH & CONFIGURATION
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WIDTH, HEIGHT = 900, 500
FLOOR_Y = 400

ROSTER = [
    "Koustav", "Pikai", "Laddo", "Rudra",
    "Amit", "Anik", "Rehan", "Deeu",
    "Aniket", "Shubronill", "Pavel", "Bipro"
]

COLORS = [
    "#ef4444", "#3b82f6", "#10b981", "#f59e0b",
    "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16",
    "#f97316", "#6366f1", "#14b8a6", "#d946ef"
]

SPECIAL_NAMES = {
    "Koustav": "LASER BEAM", "Pikai": "FIREBALL", "Laddo": "THUNDER STRIKE",
    "Rudra": "DRAGON DASH", "Amit": "SHADOW SLICE", "Anik": "TOXIC BLAST",
    "Rehan": "ICE SPIKE", "Deeu": "SONIC BOOM", "Aniket": "POWER SLAM",
    "Shubronill": "AURA BURST", "Pavel": "METEOR KICK", "Bipro": "HYPER BEAM"
}

FACE_IMAGES = {}
BG_IMAGE = None

def play_sfx(sound_type):
    if HAS_WINSOUND:
        try:
            if sound_type == "punch": winsound.Beep(450, 40)
            elif sound_type == "kick": winsound.Beep(300, 60)
            elif sound_type == "special": winsound.Beep(850, 120)
            elif sound_type == "hit": winsound.Beep(180, 50)
        except Exception:
            pass

def load_assets():
    global BG_IMAGE
    for name in ROSTER:
        img_path = os.path.join(SCRIPT_DIR, f"{name.lower()}.png")
        if os.path.exists(img_path):
            try:
                raw_img = Image.open(img_path).resize((32, 32))
                FACE_IMAGES[name] = ImageTk.PhotoImage(raw_img)
            except Exception:
                FACE_IMAGES[name] = None
        else:
            FACE_IMAGES[name] = None

    bg_path = os.path.join(SCRIPT_DIR, "arena_bg.png")
    if os.path.exists(bg_path):
        try:
            raw_bg = Image.open(bg_path).resize((WIDTH, HEIGHT))
            BG_IMAGE = ImageTk.PhotoImage(raw_bg)
        except Exception:
            BG_IMAGE = None

# ==========================================
# FIGHTER & PROJECTILE OBJECTS
# ==========================================
class Projectile:
    def __init__(self, x, y, direction, color):
        self.x = x
        self.y = y
        self.vx = direction * 12
        self.color = color
        self.active = True

    def update(self):
        self.x += self.vx
        if self.x < 0 or self.x > WIDTH:
            self.active = False

class Stickman:
    def __init__(self, name, color, start_x, is_p2=False):
        self.name = name
        self.color = color
        self.x = start_x
        self.y = FLOOR_Y
        self.vx = 0
        self.vy = 0
        self.is_p2 = is_p2
        self.facing = -1 if is_p2 else 1
        self.hp = 100
        self.energy = 0
        self.is_jumping = False
        self.is_attacking = False
        self.attack_type = None
        self.attack_cooldown = 0
        self.photo_image = FACE_IMAGES.get(name)
        self.special_title = SPECIAL_NAMES.get(name, "SPECIAL ATTACK")

    def update(self):
        self.x += self.vx
        self.y += self.vy

        if self.y < FLOOR_Y:
            self.vy += 1.2
        else:
            self.y = FLOOR_Y
            self.vy = 0
            self.is_jumping = False

        self.vx *= 0.8
        self.x = max(30, min(WIDTH - 30, self.x))

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
            if self.attack_cooldown == 0:
                self.is_attacking = False

# ==========================================
# GAME ENGINE
# ==========================================
class StickmanGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Stickman 1v1 Fighting Arena")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#0f172a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        load_assets()

        self.mode = "AI" # Defaults to VS AI
        self.p1_idx = 0
        self.p2_idx = 1
        self.state = "SELECT"
        
        self.keys = {}
        self.projectiles = []
        
        self.root.bind("<KeyPress>", self.key_down)
        self.root.bind("<KeyRelease>", self.key_up)
        
        self.canvas.bind("<Button-1>", self.on_touch_down)
        self.canvas.bind("<ButtonRelease-1>", self.on_touch_up)

        self.p1 = None
        self.p2 = None
        self.draw()

    def key_down(self, event):
        self.keys[event.keysym.lower()] = True

    def key_up(self, event):
        self.keys[event.keysym.lower()] = False

    def start_match(self):
        self.p1 = Stickman(ROSTER[self.p1_idx], COLORS[self.p1_idx], 200, False)
        self.p2 = Stickman(ROSTER[self.p2_idx], COLORS[self.p2_idx], 700, True)
        self.projectiles.clear()
        self.state = "FIGHT"
        self.game_loop()

    def process_inputs(self):
        if self.state != "FIGHT": return

        # Player 1 Inputs
        if self.keys.get("a"): 
            self.p1.vx = -5
            self.p1.facing = -1
        if self.keys.get("d"): 
            self.p1.vx = 5
            self.p1.facing = 1
        if self.keys.get("w") and not self.p1.is_jumping:
            self.p1.vy = -18
            self.p1.is_jumping = True
        if self.keys.get("f") and self.p1.attack_cooldown == 0:
            self.attack(self.p1, self.p2, "punch", dmg=8, reach=45)
        if self.keys.get("g") and self.p1.attack_cooldown == 0:
            self.attack(self.p1, self.p2, "kick", dmg=14, reach=55)
        if self.keys.get("h") and self.p1.energy >= 100 and self.p1.attack_cooldown == 0:
            self.use_special(self.p1, self.p2)

        # Player 2 / AI Inputs
        if self.mode == "PVP":
            if self.keys.get("left"): 
                self.p2.vx = -5
                self.p2.facing = -1
            if self.keys.get("right"): 
                self.p2.vx = 5
                self.p2.facing = 1
            if self.keys.get("up") and not self.p2.is_jumping:
                self.p2.vy = -18
                self.p2.is_jumping = True
            if self.keys.get("j") and self.p2.attack_cooldown == 0:
                self.attack(self.p2, self.p1, "punch", dmg=8, reach=45)
            if self.keys.get("k") and self.p2.attack_cooldown == 0:
                self.attack(self.p2, self.p1, "kick", dmg=14, reach=55)
            if self.keys.get("l") and self.p2.energy >= 100 and self.p2.attack_cooldown == 0:
                self.use_special(self.p2, self.p1)
        else:
            self.run_ai()

    def run_ai(self):
        if not self.p1 or not self.p2: return
        
        dist = self.p1.x - self.p2.x
        abs_dist = abs(dist)

        # Always face Player 1
        self.p2.facing = 1 if dist > 0 else -1

        # Chase Player 1 aggressively
        if abs_dist > 50:
            self.p2.vx = 4.5 if dist > 0 else -4.5

        # Jump if P1 jumps or randomly during combat
        if (self.p1.is_jumping or random.random() < 0.03) and not self.p2.is_jumping:
            self.p2.vy = -18
            self.p2.is_jumping = True

        # Perform Attacks when inside range
        if abs_dist <= 75 and self.p2.attack_cooldown == 0:
            if self.p2.energy >= 100:
                self.use_special(self.p2, self.p1)
            else:
                atk = "punch" if random.random() < 0.5 else "kick"
                dmg = 8 if atk == "punch" else 14
                self.attack(self.p2, self.p1, atk, dmg=dmg, reach=55)

    def attack(self, attacker, defender, atk_type, dmg, reach):
        attacker.is_attacking = True
        attacker.attack_type = atk_type
        attacker.attack_cooldown = 12
        play_sfx(atk_type)

        hit_x = attacker.x + (attacker.facing * reach)
        if abs(hit_x - defender.x) < 45 and abs(attacker.y - defender.y) < 60:
            defender.hp = max(0, defender.hp - dmg)
            defender.vx += attacker.facing * 8
            attacker.energy = min(100, attacker.energy + 15)
            defender.energy = min(100, defender.energy + 8)
            play_sfx("hit")

    def use_special(self, attacker, defender):
        attacker.energy = 0
        attacker.is_attacking = True
        attacker.attack_type = "special"
        attacker.attack_cooldown = 20
        play_sfx("special")

        proj = Projectile(attacker.x + (attacker.facing * 30), attacker.y - 60, attacker.facing, attacker.color)
        self.projectiles.append((proj, attacker, defender))

    def on_touch_down(self, event):
        x, y = event.x, event.y

        if self.state == "SELECT":
            # Mode Switch
            if 350 <= x <= 550 and 60 <= y <= 90:
                self.mode = "AI" if self.mode == "PVP" else "PVP"
                self.draw()
                return

            # Character Card Selection
            for i in range(12):
                r, c = i // 4, i % 4
                bx, by = 140 + c * 160, 105 + r * 100
                if bx <= x <= bx + 140 and by <= y <= by + 85:
                    if x <= bx + 70:
                        self.p1_idx = i
                    else:
                        self.p2_idx = i
                        self.mode = "AI" # Auto-enables AI Mode when setting P2 AI
                    self.draw()
                    return

            # Start Match Button
            if 360 <= x <= 540 and 445 <= y <= 485:
                self.start_match()

        elif self.state == "FIGHT":
            if 20 <= x <= 70 and 420 <= y <= 480: self.keys["a"] = True
            if 80 <= x <= 130 and 420 <= y <= 480: self.keys["d"] = True
            if 50 <= x <= 100 and 350 <= y <= 410: self.keys["w"] = True

            if 660 <= x <= 720 and 420 <= y <= 480: self.keys["f"] = True
            if 730 <= x <= 790 and 420 <= y <= 480: self.keys["g"] = True
            if 800 <= x <= 880 and 420 <= y <= 480: self.keys["h"] = True

    def on_touch_up(self, event):
        for k in ["a", "d", "w", "f", "g", "h"]:
            self.keys[k] = False

    def game_loop(self):
        if self.state == "FIGHT":
            self.process_inputs()
            self.p1.update()
            self.p2.update()

            for p_data in self.projectiles[:]:
                proj, att, defnd = p_data
                proj.update()
                
                if abs(proj.x - defnd.x) < 30 and abs(proj.y - (defnd.y - 50)) < 50:
                    defnd.hp = max(0, defnd.hp - 30)
                    defnd.vx += att.facing * 15
                    proj.active = False
                    play_sfx("hit")

                if not proj.active:
                    self.projectiles.remove(p_data)

            if self.p1.hp <= 0 or self.p2.hp <= 0:
                self.state = "GAME_OVER"

            self.draw()
            self.root.after(20, self.game_loop)

    def draw(self):
        self.canvas.delete("all")
        if self.state == "SELECT":
            self.draw_select_screen()
        else:
            self.draw_arena()
            self.draw_projectiles()
            self.draw_stickman(self.p1)
            self.draw_stickman(self.p2)
            self.draw_touch_controls()
            self.draw_hud()

    def draw_select_screen(self):
        self.canvas.create_text(WIDTH//2, 30, text="STICKMAN 1v1 FIGHTER", font=("Impact", 26), fill="#f43f5e")

        m_color = "#3b82f6" if self.mode == "AI" else "#22c55e"
        self.canvas.create_rectangle(350, 60, 550, 90, fill=m_color, outline="#fff")
        self.canvas.create_text(450, 75, text=f"MODE: {self.mode} (Tap to Switch)", font=("Arial", 10, "bold"), fill="#fff")

        for i, name in enumerate(ROSTER):
            r, c = i // 4, i % 4
            x, y = 140 + c * 160, 105 + r * 100

            p1_sel = (i == self.p1_idx)
            p2_sel = (i == self.p2_idx)
            border = "#ef4444" if p1_sel else ("#3b82f6" if p2_sel else "#334155")
            
            self.canvas.create_rectangle(x, y, x+140, y+85, fill="#1e293b", outline=border, width=3 if (p1_sel or p2_sel) else 1)
            
            img = FACE_IMAGES.get(name)
            if img:
                self.canvas.create_image(x + 22, y + 25, image=img)
                self.canvas.create_text(x + 80, y + 22, text=name, font=("Arial", 10, "bold"), fill=COLORS[i])
            else:
                self.canvas.create_text(x + 70, y + 22, text=name, font=("Arial", 10, "bold"), fill=COLORS[i])

            p1_bg = "#ef4444" if p1_sel else "#334155"
            self.canvas.create_rectangle(x + 6, y + 50, x + 66, y + 78, fill=p1_bg, outline="#fff" if p1_sel else "")
            self.canvas.create_text(x + 36, y + 64, text="SET P1", font=("Arial", 8, "bold"), fill="#fff")

            p2_bg = "#3b82f6" if p2_sel else "#334155"
            p2_label = "SET AI" if self.mode == "AI" else "SET P2"
            self.canvas.create_rectangle(x + 74, y + 50, x + 134, y + 78, fill=p2_bg, outline="#fff" if p2_sel else "")
            self.canvas.create_text(x + 104, y + 64, text=p2_label, font=("Arial", 8, "bold"), fill="#fff")

        self.canvas.create_rectangle(360, 445, 540, 485, fill="#22c55e", outline="#fff", width=2)
        self.canvas.create_text(450, 465, text="START MATCH", font=("Impact", 16), fill="#fff")

    def draw_arena(self):
        if BG_IMAGE:
            self.canvas.create_image(WIDTH//2, HEIGHT//2, image=BG_IMAGE)
        else:
            self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#0f172a")

        self.canvas.create_rectangle(0, FLOOR_Y, WIDTH, HEIGHT, fill="#1e293b", outline="")
        self.canvas.create_line(0, FLOOR_Y, WIDTH, FLOOR_Y, fill="#475569", width=4)

    def draw_projectiles(self):
        for proj, att, defnd in self.projectiles:
            self.canvas.create_oval(proj.x - 12, proj.y - 12, proj.x + 12, proj.y + 12, fill=proj.color, outline="#fff", width=2)

    def draw_stickman(self, p):
        x, y = p.x, p.y

        self.canvas.create_line(x, y - 40, x, y - 80, fill=p.color, width=4)
        self.canvas.create_line(x, y - 40, x - 15, y, fill=p.color, width=4)
        self.canvas.create_line(x, y - 40, x + 15, y, fill=p.color, width=4)

        if p.is_attacking:
            reach_x = x + (p.facing * 40)
            if p.attack_type == "punch":
                self.canvas.create_line(x, y - 65, reach_x, y - 65, fill="#fde047", width=5)
                self.canvas.create_line(x, y - 65, x - (p.facing * 15), y - 50, fill=p.color, width=4)
            elif p.attack_type == "kick":
                self.canvas.create_line(x, y - 40, reach_x, y - 25, fill="#fde047", width=5)
                self.canvas.create_line(x, y - 65, x + (p.facing * 15), y - 50, fill=p.color, width=4)
            elif p.attack_type == "special":
                self.canvas.create_line(x, y - 65, reach_x + (p.facing * 20), y - 65, fill="#ec4899", width=7)
        else:
            self.canvas.create_line(x, y - 65, x - 15, y - 45, fill=p.color, width=4)
            self.canvas.create_line(x, y - 65, x + 15, y - 45, fill=p.color, width=4)

        if p.photo_image:
            self.canvas.create_image(x, y - 95, image=p.photo_image)
        else:
            self.canvas.create_oval(x - 18, y - 110, x + 18, y - 74, fill="#0f172a", outline=p.color, width=3)
            self.canvas.create_text(x, y - 92, text=p.name[0], font=("Arial", 10, "bold"), fill="#fff")

    def draw_touch_controls(self):
        self.canvas.create_rectangle(20, 420, 70, 480, fill="#334155", outline="#fff")
        self.canvas.create_text(45, 450, text="◄", font=("Arial", 16, "bold"), fill="#fff")

        self.canvas.create_rectangle(80, 420, 130, 480, fill="#334155", outline="#fff")
        self.canvas.create_text(105, 450, text="►", font=("Arial", 16, "bold"), fill="#fff")

        self.canvas.create_rectangle(50, 350, 100, 410, fill="#334155", outline="#fff")
        self.canvas.create_text(75, 380, text="▲", font=("Arial", 16, "bold"), fill="#fff")

        self.canvas.create_rectangle(660, 420, 720, 480, fill="#ef4444", outline="#fff")
        self.canvas.create_text(690, 450, text="PUNCH", font=("Arial", 8, "bold"), fill="#fff")

        self.canvas.create_rectangle(730, 420, 790, 480, fill="#3b82f6", outline="#fff")
        self.canvas.create_text(760, 450, text="KICK", font=("Arial", 8, "bold"), fill="#fff")

        sp_bg = "#eab308" if self.p1.energy >= 100 else "#64748b"
        self.canvas.create_rectangle(800, 420, 880, 480, fill=sp_bg, outline="#fff")
        self.canvas.create_text(840, 450, text="SPECIAL", font=("Arial", 8, "bold"), fill="#000" if self.p1.energy >= 100 else "#fff")

    def draw_hud(self):
        self.canvas.create_rectangle(30, 15, 330, 35, fill="#090d16", outline="#fff")
        self.canvas.create_rectangle(30, 15, 30 + (self.p1.hp * 3), 35, fill="#ef4444")
        self.canvas.create_text(40, 25, text=f"P1: {self.p1.name}", anchor="w", font=("Arial", 10, "bold"), fill="#fff")

        self.canvas.create_rectangle(30, 40, 200, 50, fill="#090d16", outline="#fff")
        self.canvas.create_rectangle(30, 40, 30 + (self.p1.energy * 1.7), 50, fill="#eab308")

        self.canvas.create_rectangle(570, 15, 870, 35, fill="#090d16", outline="#fff")
        self.canvas.create_rectangle(870 - (self.p2.hp * 3), 15, 870, 35, fill="#3b82f6")
        self.canvas.create_text(860, 25, text=f"{'AI' if self.mode=='AI' else 'P2'}: {self.p2.name}", anchor="e", font=("Arial", 10, "bold"), fill="#fff")

        self.canvas.create_rectangle(700, 40, 870, 50, fill="#090d16", outline="#fff")
        self.canvas.create_rectangle(870 - (self.p2.energy * 1.7), 40, 870, 50, fill="#eab308")

        if self.state == "GAME_OVER":
            winner = self.p1.name if self.p2.hp <= 0 else self.p2.name
            self.canvas.create_text(WIDTH//2, HEIGHT//2 - 20, text=f"🏆 {winner.upper()} WINS! 🏆", font=("Impact", 32), fill="#fde047")
            self.canvas.create_text(WIDTH//2, HEIGHT//2 + 30, text="Tap Screen / Press [R] to Return", font=("Arial", 12, "bold"), fill="#fff")
            if self.keys.get("r"):
                self.state = "SELECT"
                self.draw()

if __name__ == "__main__":
    root = tk.Tk()
    game = StickmanGame(root)
    root.mainloop()
