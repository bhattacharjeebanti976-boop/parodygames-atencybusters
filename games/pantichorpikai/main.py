import tkinter as tk
import random
import os
import platform
import threading

# ==========================================
# 1. ASSET CONFIGURATION
# ==========================================
CUSTOM_IMAGES = {
    "player": "player.png",
    "panti": "panti.png",
    "bomb": "bomb.png",
    "background": "background.png"
}

CUSTOM_SOUNDS = {
    "catch": "catch.mp3",
    "bomb_hit": "bomb_hit.mp3",
    "gameover": "gameover.mp3"
}

SOUND_KEYWORDS = {
    "catch": ["catch", "panti", "collect", "pickup", "coin", "point", "pop"],
    "bomb_hit": ["bomb", "explosion", "boom", "hit", "hurt", "damage"],
    "gameover": ["gameover", "death", "die", "fail", "lose"]
}

# ==========================================
# SCRIPT PATH & CONSTANTS
# ==========================================
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

WIDTH, HEIGHT = 500, 650
GAME_FPS = 30 

# ==========================================
# ADVANCED UNIVERSAL AUDIO ENGINE
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

def scan_and_register_sounds():
    global LOADED_SOUNDS
    LOADED_SOUNDS.clear()

    try:
        dir_files = os.listdir(BASE_DIR)
    except Exception:
        dir_files = []

    valid_exts = (".wav", ".mp3", ".ogg", ".m4a")

    for action, configured_name in CUSTOM_SOUNDS.items():
        matched_file = None
        exact_path = os.path.join(BASE_DIR, configured_name)
        
        if os.path.isfile(exact_path):
            matched_file = exact_path
        else:
            target_stem = os.path.splitext(configured_name)[0].lower()
            for f in dir_files:
                f_stem, f_ext = os.path.splitext(f)
                if f_stem.lower() == target_stem and f_ext.lower() in valid_exts:
                    matched_file = os.path.join(BASE_DIR, f)
                    break
            
            if not matched_file:
                keywords = SOUND_KEYWORDS.get(action, [action])
                for f in dir_files:
                    if f.lower().endswith(valid_exts):
                        if any(kw in f.lower() for kw in keywords):
                            matched_file = os.path.join(BASE_DIR, f)
                            break

        if matched_file:
            matched_file = os.path.abspath(matched_file)
            if PYGAME_AUDIO_READY:
                try:
                    LOADED_SOUNDS[action] = pygame.mixer.Sound(matched_file)
                except Exception:
                    LOADED_SOUNDS[action] = matched_file
            else:
                LOADED_SOUNDS[action] = matched_file

scan_and_register_sounds()

def trigger_fallback_beep(sound_type):
    try:
        if platform.system() == "Windows":
            import winsound
            freqs = {"catch": 900, "bomb_hit": 200, "gameover": 140}
            winsound.Beep(freqs.get(sound_type, 400), 40)
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
        target_file_win = os.path.abspath(target_file)
        if target_file_win.lower().endswith(".wav"):
            try:
                import winsound
                winsound.PlaySound(target_file_win, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
            except Exception:
                pass

        try:
            import ctypes
            winmm = ctypes.windll.winmm
            alias = f"snd_{random.randint(1000, 9999)}"
            cmd_open = f'open "{target_file_win}" alias {alias}'
            if target_file_win.lower().endswith(".mp3"):
                cmd_open = f'open "{target_file_win}" type mpegvideo alias {alias}'
                
            winmm.mciSendStringW(cmd_open, None, 0, 0)
            winmm.mciSendStringW(f'play {alias} from 0', None, 0, 0)
            return
        except Exception:
            pass
    elif platform.system() == "Darwin":
        try:
            os.system(f'afplay "{target_file}" &')
            return
        except Exception:
            pass
    elif platform.system() == "Linux":
        for cmd in [f'aplay -q "{target_file}" &', f'paplay "{target_file}" &']:
            if os.system(cmd) == 0:
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
        img = Image.open(path).resize((target_w, target_h))
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
class PantiChorPikai:
    def __init__(self, root):
        self.root = root
        self.root.title("Panti Chor Pikai")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#1e1b4b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Load Sprites (Panti size scaled up to 70x70)
        self.bg_img = load_scaled_image(CUSTOM_IMAGES["background"], WIDTH, HEIGHT)
        self.player_img = load_scaled_image(CUSTOM_IMAGES["player"], 64, 64)
        self.panti_img = load_scaled_image(CUSTOM_IMAGES["panti"], 70, 70)  # <-- INCREASED SIZE
        self.bomb_img = load_scaled_image(CUSTOM_IMAGES["bomb"], 40, 40)

        # Game State
        self.player_x = WIDTH // 2
        self.player_y = HEIGHT - 60
        self.player_speed = 12
        self.hp = 100
        self.max_hp = 100
        self.score = 0
        self.items = []
        self.spawn_timer = 0
        self.game_state = "MENU"

        self.keys = {'Left': False, 'Right': False, 'a': False, 'd': False}

        self.bind_controls()
        self.game_loop()

    def bind_controls(self):
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonPress-1>", self.on_click)

    def on_key_press(self, e):
        k = e.keysym.lower() if len(e.keysym) == 1 else e.keysym
        if k in self.keys:
            self.keys[k] = True
        elif e.keysym == "space":
            self.handle_action()

    def on_key_release(self, e):
        k = e.keysym.lower() if len(e.keysym) == 1 else e.keysym
        if k in self.keys:
            self.keys[k] = False

    def on_mouse_move(self, e):
        if self.game_state == "PLAYING":
            self.player_x = max(32, min(WIDTH - 32, e.x))

    def on_click(self, e):
        self.handle_action()

    def handle_action(self):
        if self.game_state in ["MENU", "GAMEOVER"]:
            self.start_game()

    def start_game(self):
        self.hp = 100
        self.score = 0
        self.player_x = WIDTH // 2
        self.items.clear()
        self.spawn_timer = 0
        self.game_state = "PLAYING"

    def spawn_falling_item(self):
        item_type = 'bomb' if random.random() < 0.35 else 'panti'
        speed = random.uniform(4.5, 7.5) + (self.score * 0.02)
        
        self.items.append({
            'x': random.randint(40, WIDTH - 40),
            'y': -40,
            'type': item_type,
            'speed': speed
        })

    def game_loop(self):
        if self.game_state == "PLAYING":
            self.update_game()

        self.draw_screen()
        self.root.after(GAME_FPS, self.game_loop)

    def update_game(self):
        if self.keys['Left'] or self.keys['a']:
            self.player_x = max(32, self.player_x - self.player_speed)
        if self.keys['Right'] or self.keys['d']:
            self.player_x = min(WIDTH - 32, self.player_x + self.player_speed)

        self.spawn_timer += 1
        spawn_rate = max(10, 30 - int(self.score * 0.1))
        if self.spawn_timer >= spawn_rate:
            self.spawn_timer = 0
            self.spawn_falling_item()

        for item in self.items[:]:
            item['y'] += item['speed']

            dx = abs(item['x'] - self.player_x)
            dy = abs(item['y'] - self.player_y)

            # Expanded collision box for larger panti (50px width, 45px height)
            catch_w = 50 if item['type'] == 'panti' else 40
            catch_h = 45 if item['type'] == 'panti' else 35

            if dx < catch_w and dy < catch_h:
                if item['type'] == 'panti':
                    self.score += 10
                    play_sound("catch")
                elif item['type'] == 'bomb':
                    self.hp -= 25
                    play_sound("bomb_hit")
                    if self.hp <= 0:
                        self.hp = 0
                        self.game_state = "GAMEOVER"
                        play_sound("gameover")
                        return

                self.items.remove(item)
                continue

            if item['y'] > HEIGHT + 50:
                self.items.remove(item)

    def draw_screen(self):
        self.canvas.delete("all")

        if self.bg_img:
            self.canvas.create_image(WIDTH // 2, HEIGHT // 2, image=self.bg_img)
        else:
            self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#1e1b4b", outline="")

        self.canvas.create_rectangle(0, 0, WIDTH, 50, fill="#0f172a", outline="")
        self.canvas.create_rectangle(20, 15, 170, 35, fill="#374151", outline="#4b5563")
        hp_ratio = max(0, self.hp / self.max_hp)
        bar_color = "#22c55e" if hp_ratio > 0.5 else ("#eab308" if hp_ratio > 0.25 else "#ef4444")
        self.canvas.create_rectangle(20, 15, 20 + (150 * hp_ratio), 35, fill=bar_color, outline="")
        self.canvas.create_text(95, 25, text=f"HP: {self.hp}/{self.max_hp}", font=("Arial", 9, "bold"), fill="#ffffff")
        self.canvas.create_text(WIDTH - 80, 25, text=f"SCORE: {self.score}", font=("Arial", 14, "bold"), fill="#facc15")

        if self.game_state in ["PLAYING", "GAMEOVER"]:
            for item in self.items:
                if item['type'] == 'panti':
                    if self.panti_img:
                        self.canvas.create_image(item['x'], item['y'], image=self.panti_img)
                    else:
                        # Larger fallback shape for Panti
                        self.canvas.create_oval(item['x'] - 28, item['y'] - 24, item['x'] + 28, item['y'] + 24, fill="#ec4899", outline="#ffffff", width=2)
                        self.canvas.create_text(item['x'], item['y'], text="V", font=("Arial", 16, "bold"), fill="#ffffff")
                
                elif item['type'] == 'bomb':
                    if self.bomb_img:
                        self.canvas.create_image(item['x'], item['y'], image=self.bomb_img)
                    else:
                        self.canvas.create_oval(item['x'] - 18, item['y'] - 18, item['x'] + 18, item['y'] + 18, fill="#111827", outline="#ef4444", width=2)
                        self.canvas.create_line(item['x'], item['y'] - 18, item['x'] + 6, item['y'] - 25, fill="#f97316", width=3)

            if self.player_img:
                self.canvas.create_image(self.player_x, self.player_y, image=self.player_img)
            else:
                self.canvas.create_rectangle(self.player_x - 30, self.player_y - 20, self.player_x + 30, self.player_y + 20, fill="#3b82f6", outline="#ffffff", width=2)
                self.canvas.create_text(self.player_x, self.player_y, text="CHOR", font=("Arial", 9, "bold"), fill="#ffffff")

        if self.game_state == "MENU":
            self.canvas.create_rectangle(40, 180, 460, 440, fill="#0f172a", outline="#ec4899", width=3)
            self.canvas.create_text(WIDTH // 2, 230, text="PANTI CHOR PIKAI", font=("Arial", 22, "bold"), fill="#ec4899")
            self.canvas.create_text(WIDTH // 2, 290, text="Catch Pantis = +10 Points\nAvoid Bombs = Lose HP\n\nControls: Mouse or A/D / Left-Right", font=("Arial", 11), fill="#ffffff", justify="center")
            self.canvas.create_text(WIDTH // 2, 390, text="Click or Press SPACE to Start", font=("Arial", 12, "bold"), fill="#facc15")

        elif self.game_state == "GAMEOVER":
            self.canvas.create_rectangle(40, 200, 460, 420, fill="#0f172a", outline="#ef4444", width=3)
            self.canvas.create_text(WIDTH // 2, 240, text="GAME OVER", font=("Arial", 24, "bold"), fill="#ef4444")
            self.canvas.create_text(WIDTH // 2, 295, text=f"Final Score: {self.score}", font=("Arial", 14, "bold"), fill="#ffffff")
            self.canvas.create_text(WIDTH // 2, 360, text="Click or Press SPACE to Play Again", font=("Arial", 12, "bold"), fill="#3b82f6")

if __name__ == "__main__":
    root = tk.Tk()
    game = PantiChorPikai(root)
    root.mainloop()
