import tkinter as tk
import random
import os
import platform
import threading
import time

# ==========================================
# 1. EASY ASSET CONFIGURATION & SIZES
# ==========================================
# Adjust filenames and image dimensions directly in this dictionary:
ASSET_CONFIG = {
    # Background
    "background":      {"file": "shop_bg.png",       "size": (700, 750)},
    
    # Cups (Outlines / Sprites)
    "cup_small":       {"file": "cup_small.png",      "size": (130, 150)},
    "cup_medium":      {"file": "cup_medium.png",     "size": (150, 180)},
    "cup_large":       {"file": "cup_large.png",      "size": (170, 210)},
    
    # Tea Textures / Fill
    "tea_black":       {"file": "tea_black.png",      "size": (150, 180)},
    "tea_green":       {"file": "tea_green.png",      "size": (150, 180)},
    "tea_taro":        {"file": "tea_taro.png",       "size": (150, 180)},
    
    # Toppings (Transparent PNG recommended)
    "topping_boba":    {"file": "boba.png",          "size": (24, 24)},
    "topping_jelly":   {"file": "jelly.png",         "size": (24, 24)},
    "topping_pudding": {"file": "pudding.png",       "size": (24, 24)},
    "ice":             {"file": "ice_cubes.png",     "size": (28, 28)}
}

# Sound Effect Files (.mp3 or .wav in the same directory)
CUSTOM_SOUNDS = {
    "pour": "pour.mp3",                 # Sound when pouring tea / picking cup size
    "add_topping": "pop.mp3",           # Sound when dropping topping or ice
    "serve_success": "success.mp3",     # Sound for correct order completion
    "serve_fail": "error.mp3",         # Sound for incorrect recipe or timer out
    "clear": "clear.mp3"               # Sound when trashing/resetting cup
}

# ==========================================
# SCRIPT PATH & CONSTANTS
# ==========================================
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

WIDTH, HEIGHT = 700, 750
GAME_FPS = 30
HIGH_SCORE_FILE = os.path.join(BASE_DIR, "highscore.txt")

# Options & Colors for Fallback Vector Rendering
CUP_SIZES = {"Small": 130, "Medium": 160, "Large": 190}
TEA_FLAVORS = {
    "Black Milk Tea": {"color": "#d97706", "image_key": "tea_black"},
    "Green Tea":      {"color": "#84cc16", "image_key": "tea_green"},
    "Taro Tea":       {"color": "#c084fc", "image_key": "tea_taro"}
}
ICE_LEVELS = ["No Ice", "Low Ice", "Regular Ice"]
TOPPING_DATA = {
    "Boba":        {"color": "#18181b", "image_key": "topping_boba"},
    "Grass Jelly": {"color": "#09090b", "image_key": "topping_jelly"},
    "Egg Pudding": {"color": "#fef08a", "image_key": "topping_pudding"}
}

# ==========================================
# AUDIO ENGINE
# ==========================================
PYGAME_AUDIO_READY = False
LOADED_SOUNDS = {}

try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.mixer.set_num_channels(16)
    PYGAME_AUDIO_READY = True
except Exception:
    PYGAME_AUDIO_READY = False

def load_audio_assets():
    global LOADED_SOUNDS
    LOADED_SOUNDS.clear()

    for action, filename in CUSTOM_SOUNDS.items():
        filepath = os.path.join(BASE_DIR, filename)
        if os.path.exists(filepath):
            if PYGAME_AUDIO_READY:
                try:
                    LOADED_SOUNDS[action] = pygame.mixer.Sound(filepath)
                except Exception:
                    LOADED_SOUNDS[action] = filepath
            else:
                LOADED_SOUNDS[action] = filepath

load_audio_assets()

def trigger_fallback_beep(sound_type):
    try:
        if platform.system() == "Windows":
            import winsound
            freqs = {"pour": 400, "add_topping": 700, "serve_success": 950, "serve_fail": 220, "clear": 300}
            winsound.Beep(freqs.get(sound_type, 400), 50)
        else:
            print('\a', end='', flush=True)
    except Exception:
        pass

def _play_sound_async(sound_type):
    sound_obj = LOADED_SOUNDS.get(sound_type)
    if not sound_obj:
        trigger_fallback_beep(sound_type)
        return

    if PYGAME_AUDIO_READY and isinstance(sound_obj, pygame.mixer.Sound):
        try:
            sound_obj.play()
            return
        except Exception:
            pass

    target_file = sound_obj if isinstance(sound_obj, str) else None
    if not target_file or not os.path.exists(target_file):
        trigger_fallback_beep(sound_type)
        return

    if platform.system() == "Windows":
        try:
            import ctypes
            winmm = ctypes.windll.winmm
            alias = f"snd_{random.randint(1000, 9999)}"
            cmd_open = f'open "{target_file}" alias {alias}'
            if target_file.lower().endswith(".mp3"):
                cmd_open = f'open "{target_file}" type mpegvideo alias {alias}'
            winmm.mciSendStringW(cmd_open, None, 0, 0)
            winmm.mciSendStringW(f'play {alias} from 0', None, 0, 0)
            return
        except Exception:
            pass
    elif platform.system() == "Darwin":
        os.system(f'afplay "{target_file}" &')
        return
    elif platform.system() == "Linux":
        os.system(f'aplay -q "{target_file}" &')
        return

    trigger_fallback_beep(sound_type)

def play_sound(sound_type):
    threading.Thread(target=_play_sound_async, args=(sound_type,), daemon=True).start()

# ==========================================
# IMAGE LOADER UTILITY
# ==========================================
def load_scaled_image(filename, target_w, target_h):
    path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(path):
        return None

    try:
        from PIL import Image, ImageTk
        img = Image.open(path).resize((target_w, target_h), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        pass

    try:
        native = tk.PhotoImage(file=path)
        sx = max(1, native.width() // target_w)
        sy = max(1, native.height() // target_h)
        return native.subsample(sx, sy)
    except Exception:
        return None

# ==========================================
# MAIN GAME CLASS
# ==========================================
class BobaBaristaGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Boba Tea Barista - Custom Assets Edition")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#0f172a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.images = {}
        self.load_all_sprites()

        self.cup_x = WIDTH // 2
        self.cup_base_y = 440

        self.score = 0
        self.high_score = self.load_high_score()
        self.orders_completed = 0
        self.is_vip = False
        self.time_left = 25
        self.last_timer_update = time.time()
        
        self.current_order = {}
        self.user_cup = {
            "size": None,
            "tea": None,
            "ice": None,
            "toppings": [],
            "topping_positions": []
        }

        self.buttons = []
        self.canvas.bind("<ButtonPress-1>", self.on_click)

        self.generate_new_order()
        self.game_loop()

    def load_high_score(self):
        if os.path.exists(HIGH_SCORE_FILE):
            try:
                with open(HIGH_SCORE_FILE, "r") as f:
                    return int(f.read().strip())
            except Exception:
                return 0
        return 0

    def save_high_score(self):
        try:
            with open(HIGH_SCORE_FILE, "w") as f:
                f.write(str(self.high_score))
        except Exception:
            pass

    def load_all_sprites(self):
        """Loads all images using dimensions configured in ASSET_CONFIG."""
        for key, config in ASSET_CONFIG.items():
            w, h = config["size"]
            self.images[key] = load_scaled_image(config["file"], w, h)

    def generate_new_order(self):
        size = random.choice(list(CUP_SIZES.keys()))
        tea = random.choice(list(TEA_FLAVORS.keys()))
        ice = random.choice(ICE_LEVELS)
        
        num_toppings = random.choice([1, 2])
        toppings = random.sample(list(TOPPING_DATA.keys()), num_toppings)

        self.is_vip = random.random() < 0.30
        self.time_left = 18 if self.is_vip else 25

        self.current_order = {
            "size": size,
            "tea": tea,
            "ice": ice,
            "toppings": toppings
        }
        self.reset_cup(silent=True)

    def reset_cup(self, silent=False):
        self.user_cup = {
            "size": None,
            "tea": None,
            "ice": None,
            "toppings": [],
            "topping_positions": []
        }
        if not silent:
            play_sound("clear")

    def set_size(self, size_name):
        self.user_cup["size"] = size_name
        play_sound("pour")

    def set_tea(self, tea_name):
        if not self.user_cup["size"]:
            self.show_feedback("PICK A CUP SIZE FIRST!", "#ef4444")
            return
        self.user_cup["tea"] = tea_name
        play_sound("pour")

    def set_ice(self, ice_name):
        if not self.user_cup["size"]:
            self.show_feedback("PICK A CUP SIZE FIRST!", "#ef4444")
            return
        self.user_cup["ice"] = ice_name
        play_sound("add_topping")

    def add_topping(self, topping_name):
        if not self.user_cup["size"]:
            self.show_feedback("PICK A CUP SIZE FIRST!", "#ef4444")
            return

        if len(self.user_cup["toppings"]) >= 4:
            self.show_feedback("CUP FULL!", "#eab308")
            return

        self.user_cup["toppings"].append(topping_name)
        
        cup_h = CUP_SIZES[self.user_cup["size"]]
        px = self.cup_x + random.randint(-35, 35)
        py = (self.cup_base_y - 15) - random.randint(10, min(60, cup_h - 40))
        self.user_cup["topping_positions"].append((topping_name, px, py))

        play_sound("add_topping")

    def serve_boba(self):
        o = self.current_order
        c = self.user_cup

        size_match = c["size"] == o["size"]
        tea_match = c["tea"] == o["tea"]
        ice_match = c["ice"] == o["ice"]
        toppings_match = set(c["toppings"]) == set(o["toppings"])

        if size_match and tea_match and ice_match and toppings_match:
            time_bonus = int(self.time_left * 5)
            base_score = 150 + time_bonus
            earned = base_score * 2 if self.is_vip else base_score
            
            self.score += earned
            self.orders_completed += 1
            
            if self.score > self.high_score:
                self.high_score = self.score
                self.save_high_score()

            play_sound("serve_success")
            txt = f"VIP DELIGHT! +{earned} PTS (2X)" if self.is_vip else f"DELICIOUS! +{earned} PTS"
            clr = "#eab308" if self.is_vip else "#22c55e"
            self.show_feedback(txt, clr)
        else:
            self.score = max(0, self.score - 50)
            play_sound("serve_fail")
            self.show_feedback("WRONG RECIPE! -50 PTS", "#ef4444")

        self.generate_new_order()

    def show_feedback(self, text, color):
        self.canvas.create_rectangle(WIDTH//2 - 170, 210, WIDTH//2 + 170, 250, fill="#0f172a", outline=color, width=2)
        self.canvas.create_text(WIDTH//2, 230, text=text, font=("Arial", 12, "bold"), fill=color)
        self.root.update()
        self.root.after(600)

    def game_loop(self):
        now = time.time()
        if now - self.last_timer_update >= 1.0:
            self.last_timer_update = now
            self.time_left -= 1
            if self.time_left <= 0:
                play_sound("serve_fail")
                penalty = 60 if self.is_vip else 30
                self.score = max(0, self.score - penalty)
                msg = "VIP LEFT ANGRY! -60 PTS" if self.is_vip else "CUSTOMER LEFT! -30 PTS"
                self.show_feedback(msg, "#ef4444")
                self.generate_new_order()

        self.draw_screen()
        self.root.after(GAME_FPS, self.game_loop)

    def on_click(self, event):
        x, y = event.x, event.y
        for btn in self.buttons:
            if btn['x1'] <= x <= btn['x2'] and btn['y1'] <= y <= btn['y2']:
                btn['callback']()
                break

    def draw_screen(self):
        self.canvas.delete("all")
        self.buttons.clear()

        # 1. Background Image
        if self.images.get("background"):
            self.canvas.create_image(WIDTH // 2, HEIGHT // 2, image=self.images["background"])
        else:
            self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#1e1b4b", outline="")

        # 2. Top Header HUD
        self.canvas.create_rectangle(0, 0, WIDTH, 50, fill="#0f172a", outline="")
        self.canvas.create_text(80, 25, text=f"SERVED: {self.orders_completed}", font=("Arial", 11, "bold"), fill="#ffffff")
        self.canvas.create_text(WIDTH // 2, 25, text=f"HIGH SCORE: {self.high_score}", font=("Arial", 12, "bold"), fill="#f59e0b")
        self.canvas.create_text(WIDTH - 90, 25, text=f"SCORE: {self.score}", font=("Arial", 13, "bold"), fill="#facc15")

        # 3. Order Ticket
        card_bg = "#fefce8" if self.is_vip else "#ffffff"
        card_stroke = "#eab308" if self.is_vip else "#38bdf8"
        hdr_bg = "#ca8a04" if self.is_vip else "#0284c7"
        hdr_title = "⭐ VIP CUSTOMER ORDER (2X POINTS) ⭐" if self.is_vip else "CUSTOMER ORDER"

        self.canvas.create_rectangle(20, 60, WIDTH - 20, 165, fill=card_bg, outline=card_stroke, width=4 if self.is_vip else 3)
        self.canvas.create_rectangle(20, 60, WIDTH - 20, 90, fill=hdr_bg, outline="")
        self.canvas.create_text(WIDTH // 2, 75, text=hdr_title, font=("Arial", 11, "bold"), fill="#ffffff")

        max_time = 18 if self.is_vip else 25
        timer_ratio = max(0, self.time_left / max_time)
        bar_color = "#22c55e" if timer_ratio > 0.4 else ("#eab308" if timer_ratio > 0.2 else "#ef4444")
        self.canvas.create_rectangle(WIDTH - 150, 70, WIDTH - 30, 82, fill="#334155", outline="")
        self.canvas.create_rectangle(WIDTH - 150, 70, WIDTH - 150 + int(120 * timer_ratio), 82, fill=bar_color, outline="")

        ord_str = f"Size: {self.current_order['size']}   |   Tea: {self.current_order['tea']}   |   Ice: {self.current_order['ice']}"
        top_str = "Toppings: " + ", ".join(self.current_order["toppings"])
        self.canvas.create_text(WIDTH // 2, 112, text=ord_str, font=("Arial", 11, "bold"), fill="#0f172a")
        self.canvas.create_text(WIDTH // 2, 140, text=top_str, font=("Arial", 12, "bold"), fill=hdr_bg)

        # 4. Counter Base
        self.canvas.create_rectangle(80, self.cup_base_y, WIDTH - 80, self.cup_base_y + 20, fill="#475569", outline="#0f172a", width=2)

        # 5. Render Active Cup
        if self.user_cup["size"]:
            cup_h = CUP_SIZES[self.user_cup["size"]]
            cup_w = 110 if self.user_cup["size"] == "Small" else (130 if self.user_cup["size"] == "Medium" else 150)
            top_y = self.cup_base_y - cup_h

            # Custom Cup Image or Fallback Vector
            cup_img_key = f"cup_{self.user_cup['size'].lower()}"
            
            # Liquid Fill
            if self.user_cup["tea"]:
                tea_info = TEA_FLAVORS[self.user_cup["tea"]]
                img_key = tea_info["image_key"]
                
                if self.images.get(img_key):
                    self.canvas.create_image(self.cup_x, self.cup_base_y - (cup_h // 2), image=self.images[img_key])
                else:
                    self.canvas.create_rectangle(self.cup_x - (cup_w//2) + 6, top_y + 15,
                                                self.cup_x + (cup_w//2) - 6, self.cup_base_y - 4,
                                                fill=tea_info["color"], outline="")

            # Ice Cubes
            if self.user_cup["ice"] in ["Low Ice", "Regular Ice"]:
                count = 3 if self.user_cup["ice"] == "Low Ice" else 6
                for i in range(count):
                    ix = self.cup_x + (-30 + (i * 18) % 60)
                    iy = top_y + 35 + ((i * 12) % 40)
                    if self.images.get("ice"):
                        self.canvas.create_image(ix, iy, image=self.images["ice"])
                    else:
                        self.canvas.create_rectangle(ix-8, iy-8, ix+8, iy+8, fill="#e0f2fe", outline="#38bdf8")

            # Toppings
            for item in self.user_cup["topping_positions"]:
                t_name, px, py = item
                img_key = TOPPING_DATA[t_name]["image_key"]
                
                if self.images.get(img_key):
                    self.canvas.create_image(px, py, image=self.images[img_key])
                else:
                    c = TOPPING_DATA[t_name]["color"]
                    self.canvas.create_oval(px-7, py-7, px+7, py+7, fill=c, outline="#ffffff")

            # Cup Foreground Image or Vector Outline
            if self.images.get(cup_img_key):
                self.canvas.create_image(self.cup_x, self.cup_base_y - (cup_h // 2), image=self.images[cup_img_key])
            else:
                self.canvas.create_line(self.cup_x + 15, top_y - 30, self.cup_x - 10, self.cup_base_y - 10, fill="#ef4444", width=8)
                self.canvas.create_polygon(self.cup_x - (cup_w//2), top_y,
                                           self.cup_x + (cup_w//2), top_y,
                                           self.cup_x + (cup_w//2) - 15, self.cup_base_y,
                                           self.cup_x - (cup_w//2) + 15, self.cup_base_y,
                                           fill="", outline="#ffffff", width=4)

        # 6. Dashboard Controls
        dash_y = 480
        
        # 1. Size Selection
        self.canvas.create_text(90, dash_y + 15, text="1. SELECT SIZE", font=("Arial", 10, "bold"), fill="#94a3b8")
        sizes = list(CUP_SIZES.keys())
        for i, sz in enumerate(sizes):
            bx1, by1 = 30 + (i * 75), dash_y + 30
            bx2, by2 = bx1 + 65, by1 + 35
            active = self.user_cup["size"] == sz
            bg = "#0284c7" if active else "#334155"
            self.canvas.create_rectangle(bx1, by1, bx2, by2, fill=bg, outline="#ffffff" if active else "", width=2)
            self.canvas.create_text((bx1+bx2)//2, (by1+by2)//2, text=sz, font=("Arial", 9, "bold"), fill="#ffffff")
            self.buttons.append({'x1': bx1, 'y1': by1, 'x2': bx2, 'y2': by2, 'callback': lambda s=sz: self.set_size(s)})

        # 2. Tea Selection
        self.canvas.create_text(320, dash_y + 15, text="2. SELECT TEA FLAVOR", font=("Arial", 10, "bold"), fill="#94a3b8")
        teas = list(TEA_FLAVORS.keys())
        for i, t in enumerate(teas):
            bx1, by1 = 260 + (i * 140), dash_y + 30
            bx2, by2 = bx1 + 130, by1 + 35
            active = self.user_cup["tea"] == t
            bg = TEA_FLAVORS[t]["color"] if active else "#334155"
            self.canvas.create_rectangle(bx1, by1, bx2, by2, fill=bg, outline="#ffffff" if active else "", width=2)
            self.canvas.create_text((bx1+bx2)//2, (by1+by2)//2, text=t, font=("Arial", 9, "bold"), fill="#ffffff")
            self.buttons.append({'x1': bx1, 'y1': by1, 'x2': bx2, 'y2': by2, 'callback': lambda t_name=t: self.set_tea(t_name)})

        # 3. Ice Selection
        self.canvas.create_text(90, dash_y + 85, text="3. ICE LEVEL", font=("Arial", 10, "bold"), fill="#94a3b8")
        for i, ice in enumerate(ICE_LEVELS):
            bx1, by1 = 30 + (i * 75), dash_y + 100
            bx2, by2 = bx1 + 65, by1 + 35
            active = self.user_cup["ice"] == ice
            bg = "#0369a1" if active else "#334155"
            self.canvas.create_rectangle(bx1, by1, bx2, by2, fill=bg, outline="#ffffff" if active else "", width=2)
            self.canvas.create_text((bx1+bx2)//2, (by1+by2)//2, text=ice, font=("Arial", 8, "bold"), fill="#ffffff")
            self.buttons.append({'x1': bx1, 'y1': by1, 'x2': bx2, 'y2': by2, 'callback': lambda ic=ice: self.set_ice(ic)})

        # 4. Toppings Selection
        self.canvas.create_text(320, dash_y + 85, text="4. ADD TOPPINGS", font=("Arial", 10, "bold"), fill="#94a3b8")
        toppings = list(TOPPING_DATA.keys())
        for i, top in enumerate(toppings):
            bx1, by1 = 260 + (i * 140), dash_y + 100
            bx2, by2 = bx1 + 130, by1 + 35
            self.canvas.create_rectangle(bx1, by1, bx2, by2, fill="#334155", outline="#64748b", width=2)
            self.canvas.create_text((bx1+bx2)//2, (by1+by2)//2, text=f"+ {top}", font=("Arial", 9, "bold"), fill="#ffffff")
            self.buttons.append({'x1': bx1, 'y1': by1, 'x2': bx2, 'y2': by2, 'callback': lambda tp=top: self.add_topping(tp)})

        # 7. Action Buttons
        self.canvas.create_rectangle(WIDTH//2 + 20, 680, WIDTH//2 + 200, 730, fill="#22c55e", outline="#ffffff", width=2)
        self.canvas.create_text(WIDTH//2 + 110, 705, text="SERVE DRINK", font=("Arial", 13, "bold"), fill="#ffffff")
        self.buttons.append({
            'x1': WIDTH//2 + 20, 'y1': 680, 'x2': WIDTH//2 + 200, 'y2': 730,
            'callback': self.serve_boba
        })

        self.canvas.create_rectangle(WIDTH//2 - 200, 680, WIDTH//2 - 20, 730, fill="#ef4444", outline="#ffffff", width=2)
        self.canvas.create_text(WIDTH//2 - 110, 705, text="TRASH CUP", font=("Arial", 13, "bold"), fill="#ffffff")
        self.buttons.append({
            'x1': WIDTH//2 - 200, 'y1': 680, 'x2': WIDTH//2 - 20, 'y2': 730,
            'callback': lambda: self.reset_cup(silent=False)
        })

if __name__ == "__main__":
    root = tk.Tk()
    game = BobaBaristaGame(root)
    root.mainloop()
