import tkinter as tk
import random
import math
import os
import sys
import time

# Optional Pillow integration for JPG/JPEG support and auto-resizing
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Optional native sound playback for Windows
if sys.platform == "win32":
    import winsound

# =========================================================================
# ASSET PATH RESOLUTION (Fixes IDLE & PyInstaller directory loading)
# =========================================================================
def resource_path(relative_path):
    """ Get absolute path to resource, works for IDLE, script folder, and PyInstaller """
    if not relative_path:
        return None
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    
    # Lock path to the directory where this script file lives
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, relative_path)

# =========================================================================
# ASSET CONFIGURATION - EDIT PATHS AND SETTINGS HERE
# =========================================================================
CONFIG = {
    "GAME_TITLE": "CUT THE PUSSY",
    "WINDOW_WIDTH": 800,
    "WINDOW_HEIGHT": 600,
    "BG_COLOR": "#181824",
    
    # Custom Asset Filenames (Place files in the same folder as this script)
    "BG_IMAGE_PATH": "background.png",     # e.g., "background.png" or "arena.jpg"
    "LOGO_IMAGE_PATH": "logo.png",         # e.g., "logo.png" or "logo.jpg"
    "TARGET_IMAGE_PATHS": [],              # e.g., ["cat1.png", "cat2.png"]
    "SLASH_SOUND_PATH": "slash.wav",       # e.g., "slash.wav"
    
    "SPLASH_DURATION_MS": 2500,            # Logo display duration in ms
    "MAX_LIVES": 3,
    
    # Mechanics Tuning
    "BOMB_CHANCE": 0.18,
    "FREEZE_CHANCE": 0.12,
    "FREEZE_DURATION_FRAMES": 160
}

class CutThePussyGame:
    def __init__(self, root):
        self.root = root
        self.root.title(CONFIG["GAME_TITLE"])
        self.root.geometry(f"{CONFIG['WINDOW_WIDTH']}x{CONFIG['WINDOW_HEIGHT']}")
        self.root.resizable(False, False)

        # Canvas setup
        self.canvas = tk.Canvas(
            root, 
            width=CONFIG["WINDOW_WIDTH"], 
            height=CONFIG["WINDOW_HEIGHT"], 
            bg=CONFIG["BG_COLOR"],
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        # Load & Retain Asset References (Prevents Garbage Collection)
        self.bg_photo = self.load_image(CONFIG["BG_IMAGE_PATH"], size=(CONFIG["WINDOW_WIDTH"], CONFIG["WINDOW_HEIGHT"]))
        self.logo_photo = self.load_image(CONFIG["LOGO_IMAGE_PATH"], size=(400, 250))
        self.target_photos = [self.load_image(p, size=(70, 70)) for p in CONFIG["TARGET_IMAGE_PATHS"] if p]
        self.target_photos = [p for p in self.target_photos if p]

        # Game State
        self.score = 0
        self.lives = CONFIG["MAX_LIVES"]
        self.game_running = False
        self.targets = []
        self.particles = []
        self.floating_texts = []
        self.slash_trail = []
        self.last_mouse_pos = None
        
        # Power-Up & Combo State
        self.freeze_timer = 0
        self.recent_slices = []

        # Event Bindings
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)

        # Start Splash Screen
        self.show_splash_screen()

    def load_image(self, relative_path, size=None):
        """Loads PNG/GIF/JPG images reliably and resizes if needed."""
        if not relative_path:
            return None
            
        full_path = resource_path(relative_path)
        if not os.path.exists(full_path):
            print(f"[Warning] Image file not found: {full_path}")
            return None

        try:
            if HAS_PIL:
                img = Image.open(full_path)
                if size:
                    img = img.resize(size, Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(img)
            else:
                # Standard Tkinter PhotoImage (Requires PNG or GIF)
                img = tk.PhotoImage(file=full_path)
                return img
        except Exception as e:
            print(f"[Error] Failed to load image '{relative_path}': {e}")
            return None

    def draw_background(self):
        """Renders background and ensures it stays behind all game elements."""
        if self.bg_photo:
            self.canvas.delete("bg_tag")
            self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw", tags="bg_tag")
            self.canvas.tag_lower("bg_tag")

    def play_slash_sound(self):
        sound_path = resource_path(CONFIG["SLASH_SOUND_PATH"])
        if sound_path and os.path.exists(sound_path) and sys.platform == "win32":
            try:
                winsound.PlaySound(sound_path, winsound.SND_ASYNC | winsound.SND_FILENAME)
            except Exception:
                pass

    # ---------------------------------------------------------------------
    # SPLASH SCREEN LOGIC
    # ---------------------------------------------------------------------
    def show_splash_screen(self):
        self.draw_background()
        
        cx = CONFIG["WINDOW_WIDTH"] // 2
        cy = CONFIG["WINDOW_HEIGHT"] // 2

        if self.logo_photo:
            self.splash_logo_id = self.canvas.create_image(cx, cy - 30, image=self.logo_photo)
        else:
            self.splash_logo_id = self.canvas.create_text(
                cx, cy - 40,
                text=CONFIG["GAME_TITLE"],
                font=("Impact", 48, "bold"),
                fill="#ff2a6d"
            )

        self.splash_sub_id = self.canvas.create_text(
            cx, cy + 120,
            text="GET READY TO SLASH!",
            font=("Arial", 18, "bold"),
            fill="#05d9e8"
        )

        self.root.after(CONFIG["SPLASH_DURATION_MS"], self.start_game)

    # ---------------------------------------------------------------------
    # MAIN GAME LOOP & LOGIC
    # ---------------------------------------------------------------------
    def start_game(self):
        if hasattr(self, 'splash_logo_id'):
            self.canvas.delete(self.splash_logo_id)
        if hasattr(self, 'splash_sub_id'):
            self.canvas.delete(self.splash_sub_id)

        self.score = 0
        self.lives = CONFIG["MAX_LIVES"]
        self.freeze_timer = 0
        self.recent_slices.clear()
        self.game_running = True

        # UI Overlay
        self.score_text = self.canvas.create_text(
            20, 25, anchor="nw", text=f"SCORE: {self.score}", 
            font=("Arial", 16, "bold"), fill="#ffffff"
        )
        self.lives_text = self.canvas.create_text(
            CONFIG["WINDOW_WIDTH"] - 20, 25, anchor="ne", 
            text=f"LIVES: {'❤️' * self.lives}", font=("Arial", 16, "bold"), fill="#ff2a6d"
        )
        self.freeze_status_text = self.canvas.create_text(
            CONFIG["WINDOW_WIDTH"] // 2, 25, anchor="n", text="", 
            font=("Impact", 20), fill="#05d9e8"
        )

        self.schedule_spawns()
        self.update_game()

    def schedule_spawns(self):
        if not self.game_running:
            return
        
        self.spawn_target()
        base_delay = random.randint(800, 1600)
        if self.freeze_timer > 0:
            base_delay = int(base_delay * 1.8)

        self.root.after(base_delay, self.schedule_spawns)

    def spawn_target(self):
        radius = 35
        x = random.randint(100, CONFIG["WINDOW_WIDTH"] - 100)
        y = CONFIG["WINDOW_HEIGHT"] + radius
        vx = random.uniform(-4, 4)
        vy = random.uniform(-18, -13)
        
        rand_val = random.random()
        if rand_val < CONFIG["BOMB_CHANCE"]:
            target_type = "bomb"
        elif rand_val < CONFIG["BOMB_CHANCE"] + CONFIG["FREEZE_CHANCE"]:
            target_type = "freeze"
        else:
            target_type = "regular"

        photo = random.choice(self.target_photos) if (self.target_photos and target_type == "regular") else None

        target = {
            "x": x, "y": y, "vx": vx, "vy": vy,
            "radius": radius, "photo": photo,
            "type": target_type,
            "canvas_ids": []
        }
        self.draw_target(target)
        self.targets.append(target)

    def draw_target(self, target):
        x, y, r = target["x"], target["y"], target["radius"]
        ttype = target["type"]

        if ttype == "bomb":
            body = self.canvas.create_oval(x-r, y-r, x+r, y+r, fill="#2b2b2b", outline="#ff2a6d", width=3)
            fuse = self.canvas.create_line(x, y-r, x+10, y-r-12, fill="#ff9e00", width=3)
            spark = self.canvas.create_text(x+12, y-r-15, text="💥", font=("Arial", 12))
            icon = self.canvas.create_text(x, y, text="💣", font=("Arial", 22))
            target["canvas_ids"].extend([body, fuse, spark, icon])

        elif ttype == "freeze":
            body = self.canvas.create_oval(x-r, y-r, x+r, y+r, fill="#00b4d8", outline="#ffffff", width=3)
            icon = self.canvas.create_text(x, y, text="❄️", font=("Arial", 24))
            target["canvas_ids"].extend([body, icon])

        else:
            if target["photo"]:
                img_id = self.canvas.create_image(x, y, image=target["photo"])
                target["canvas_ids"].append(img_id)
            else:
                face = self.canvas.create_oval(x-r, y-r, x+r, y+r, fill="#ff9e00", outline="#ffffff", width=2)
                ear_l = self.canvas.create_polygon(x-r+5, y-r+10, x-r-10, y-r-15, x-r+20, y-r+2, fill="#ff9e00")
                ear_r = self.canvas.create_polygon(x+r-5, y-r+10, x+r+10, y-r-15, x+r-20, y-r+2, fill="#ff9e00")
                eye_l = self.canvas.create_oval(x-15, y-10, x-5, y, fill="#000000")
                eye_r = self.canvas.create_oval(x+5, y-10, x+15, y, fill="#000000")
                nose = self.canvas.create_polygon(x-5, y+5, x+5, y+5, x, y+10, fill="#ff2a6d")
                target["canvas_ids"].extend([ear_l, ear_r, face, eye_l, eye_r, nose])

    def create_splash_particles(self, x, y, particle_type="regular"):
        if particle_type == "bomb":
            colors = ["#ff2a6d", "#ff9e00", "#d00000", "#000000"]
            count = 25
        elif particle_type == "freeze":
            colors = ["#05d9e8", "#00b4d8", "#caf0f8", "#ffffff"]
            count = 20
        else:
            colors = ["#ff2a6d", "#05d9e8", "#f7f7f7", "#ff9e00"]
            count = 12

        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(3, 11)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            color = random.choice(colors)
            size = random.randint(3, 8)
            pid = self.canvas.create_oval(x-size, y-size, x+size, y+size, fill=color, outline="")
            self.particles.append({"id": pid, "x": x, "y": y, "vx": vx, "vy": vy, "life": 18})

    def spawn_floating_text(self, x, y, text, color="#ffffff"):
        tid = self.canvas.create_text(
            x, y, text=text, font=("Impact", 22, "bold"), fill=color
        )
        self.floating_texts.append({"id": tid, "x": x, "y": y, "life": 25})

    def on_mouse_move(self, event):
        cur_pos = (event.x, event.y)
        self.slash_trail.append({"pos": cur_pos, "alpha": 8})
        
        if self.last_mouse_pos and self.game_running:
            cx, cy = cur_pos
            for target in self.targets[:]:
                tx, ty, r = target["x"], target["y"], target["radius"]
                dist = math.hypot(cx - tx, cy - ty)
                if dist < r + 10:
                    self.slice_target(target)

        self.last_mouse_pos = cur_pos

    def slice_target(self, target):
        for cid in target["canvas_ids"]:
            self.canvas.delete(cid)
        if target in self.targets:
            self.targets.remove(target)

        tx, ty = target["x"], target["y"]
        ttype = target["type"]

        if ttype == "bomb":
            self.create_splash_particles(tx, ty, particle_type="bomb")
            self.spawn_floating_text(tx, ty, "BOMB! -1 LIFE", color="#ff2a6d")
            self.score = max(0, self.score - 20)
            self.lives -= 1
            self.canvas.itemconfig(self.score_text, text=f"SCORE: {self.score}")
            self.canvas.itemconfig(self.lives_text, text=f"LIVES: {'❤️' * max(0, self.lives)}")
            
            if self.lives <= 0:
                self.game_over()
            return

        if ttype == "freeze":
            self.freeze_timer = CONFIG["FREEZE_DURATION_FRAMES"]
            self.create_splash_particles(tx, ty, particle_type="freeze")
            self.spawn_floating_text(tx, ty, "TIME FROZEN!", color="#05d9e8")
            self.play_slash_sound()
            return

        now = time.time()
        self.recent_slices.append(now)
        self.recent_slices = [t for t in self.recent_slices if now - t < 0.35]
        
        combo_count = len(self.recent_slices)
        base_points = 10
        
        if combo_count >= 2:
            bonus_points = combo_count * 5
            total_earned = base_points + bonus_points
            self.score += total_earned
            self.spawn_floating_text(tx, ty, f"{combo_count}x COMBO! +{total_earned}", color="#ff9e00")
        else:
            self.score += base_points

        self.canvas.itemconfig(self.score_text, text=f"SCORE: {self.score}")
        self.create_splash_particles(tx, ty, particle_type="regular")
        self.play_slash_sound()

    def update_game(self):
        if not self.game_running:
            return

        if self.freeze_timer > 0:
            self.freeze_timer -= 1
            speed_mult = 0.35
            self.canvas.itemconfig(self.freeze_status_text, text="❄️ FROZEN ❄️")
        else:
            speed_mult = 1.0
            self.canvas.itemconfig(self.freeze_status_text, text="")

        gravity = 0.55 * speed_mult

        for target in self.targets[:]:
            target["x"] += target["vx"] * speed_mult
            target["y"] += target["vy"] * speed_mult
            target["vy"] += gravity

            dx = target["vx"] * speed_mult
            dy = target["vy"] * speed_mult
            for cid in target["canvas_ids"]:
                self.canvas.move(cid, dx, dy)

            if target["y"] > CONFIG["WINDOW_HEIGHT"] + 50 and target["vy"] > 0:
                for cid in target["canvas_ids"]:
                    self.canvas.delete(cid)
                self.targets.remove(target)
                
                if target["type"] == "regular":
                    self.lives -= 1
                    self.canvas.itemconfig(self.lives_text, text=f"LIVES: {'❤️' * max(0, self.lives)}")
                    if self.lives <= 0:
                        self.game_over()

        for ft in self.floating_texts[:]:
            ft["y"] -= 1.5
            ft["life"] -= 1
            self.canvas.move(ft["id"], 0, -1.5)
            if ft["life"] <= 0:
                self.canvas.delete(ft["id"])
                self.floating_texts.remove(ft)

        for p in self.particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
            self.canvas.move(p["id"], p["vx"], p["vy"])
            if p["life"] <= 0:
                self.canvas.delete(p["id"])
                self.particles.remove(p)

        self.canvas.delete("slash_line")
        if len(self.slash_trail) > 1:
            pts = [p["pos"] for p in self.slash_trail]
            flat_pts = [coord for pt in pts for coord in pt]
            self.canvas.create_line(flat_pts, fill="#05d9e8", width=4, tags="slash_line", capstyle="round")

        for st in self.slash_trail[:]:
            st["alpha"] -= 1
            if st["alpha"] <= 0:
                self.slash_trail.remove(st)

        self.root.after(20, self.update_game)

    def game_over(self):
        self.game_running = False
        self.canvas.create_text(
            CONFIG["WINDOW_WIDTH"]//2, CONFIG["WINDOW_HEIGHT"]//2 - 20,
            text="GAME OVER", font=("Impact", 52), fill="#ff2a6d"
        )
        self.canvas.create_text(
            CONFIG["WINDOW_WIDTH"]//2, CONFIG["WINDOW_HEIGHT"]//2 + 40,
            text=f"FINAL SCORE: {self.score}\nClick Anywhere to Restart", 
            font=("Arial", 16, "bold"), fill="#ffffff", justify="center"
        )
        self.canvas.bind("<Button-1>", self.restart_game)

    def restart_game(self, event):
        self.canvas.unbind("<Button-1>")
        self.canvas.delete("all")
        self.draw_background()
        self.start_game()

# =========================================================================
# APPLICATION ENTRY POINT
# =========================================================================
if __name__ == "__main__":
    root = tk.Tk()
    game = CutThePussyGame(root)
    root.mainloop()
