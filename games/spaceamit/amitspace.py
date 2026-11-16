import tkinter as tk
import random
import os
import platform

# ==========================================
# SCRIPT PATH & ASSET RESOLUTION
# ==========================================
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

# ==========================================
# CONFIGURATION
# ==========================================
WIDTH, HEIGHT = 400, 600
GAME_FPS = 30
PLAYER_SPEED = 8
LASER_SPEED = 12
INITIAL_ENEMY_SPEED = 2.0
ENEMY_ROWS, ENEMY_COLS = 4, 6

# ==========================================
# AUDIO ENGINE (CROSS-PLATFORM)
# ==========================================
def trigger_fallback_beep(sound_type):
    try:
        if platform.system() == "Windows":
            import winsound
            freq = 1000 if sound_type == "laser" else 250
            winsound.Beep(freq, 50)
        else:
            print('\a', end='', flush=True)
    except Exception:
        pass

def play_sound(sound_type):
    name_map = {
        "laser": ["laser", "shoot", "fire", "blaster", "pew"],
        "explosion": ["explosion", "boom", "hit", "destroy", "crash"]
    }
    possible_names = name_map.get(sound_type, [sound_type])
    supported_exts = [".wav", ".mp3", ".ogg", ".m4a"]
    target_file = None

    try:
        files_in_dir = os.listdir(BASE_DIR)
    except Exception:
        files_in_dir = []

    for name in possible_names:
        for f in files_in_dir:
            f_lower = f.lower()
            for ext in supported_exts:
                if f_lower == (name + ext):
                    target_file = os.path.join(BASE_DIR, f)
                    break
            if target_file:
                break
        if target_file:
            break

    if not target_file:
        trigger_fallback_beep(sound_type)
        return

    played = False

    # 1. Android (Pydroid 3)
    try:
        from jnius import autoclass
        MediaPlayer = autoclass('android.media.MediaPlayer')
        mp = MediaPlayer()
        mp.setDataSource(target_file)
        mp.prepare()
        mp.start()
        played = True
    except Exception:
        pass

    # 2. Windows
    if not played and platform.system() == "Windows":
        try:
            import winsound
            if target_file.lower().endswith(".wav"):
                winsound.PlaySound(target_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                played = True
        except Exception:
            pass

        if not played:
            try:
                import ctypes
                alias = f"snd_{random.randint(1000, 9999)}"
                ctypes.windll.winmm.mciSendStringW(f'open "{target_file}" alias {alias}', None, 0, 0)
                ctypes.windll.winmm.mciSendStringW(f'play {alias} from 0', None, 0, 0)
                played = True
            except Exception:
                pass

    # 3. macOS
    if not played and platform.system() == "Darwin":
        if os.system(f'afplay "{target_file}" &') == 0:
            played = True

    # 4. Linux / Shell Fallbacks
    if not played:
        for cmd in [f'aplay -q "{target_file}" &', f'paplay "{target_file}" &', f'ffplay -nodisp -autoexit "{target_file}" >/dev/null 2>&1 &']:
            if os.system(cmd) == 0:
                played = True
                break

    if not played:
        trigger_fallback_beep(sound_type)

# ==========================================
# IMAGE LOADER HELPER
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
# GAME CLASS
# ==========================================
class RetroShooterGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Space Invaders")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.resizable(False, False)

        # Main Canvas with high-contrast background
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#050814", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Generate Fixed Background Stars
        self.stars = [(random.randint(0, WIDTH), random.randint(0, HEIGHT)) for _ in range(40)]

        # Load Custom PNG Assets
        self.player_img = load_scaled_image("player.png", 40, 40)
        self.enemy_img = load_scaled_image("enemy.png", 32, 32)

        # Game Logic Variables
        self.game_state = "MENU"  # MENU, PLAYING, GAMEOVER
        self.score = 0
        self.wave = 1

        self.player_x = WIDTH // 2
        self.player_y = HEIGHT - 50
        self.move_left = False
        self.move_right = False
        self.fire_cooldown = 0

        self.lasers = []
        self.enemies = []
        self.enemy_dir = 1
        self.enemy_speed = INITIAL_ENEMY_SPEED

        # Bind Input Events
        self.bind_controls()
        
        # Start Game Loop
        self.game_loop()

    def bind_controls(self):
        self.root.bind("<KeyPress-Left>", lambda e: self.set_move('left', True))
        self.root.bind("<KeyRelease-Left>", lambda e: self.set_move('left', False))
        self.root.bind("<KeyPress-Right>", lambda e: self.set_move('right', True))
        self.root.bind("<KeyRelease-Right>", lambda e: self.set_move('right', False))
        self.root.bind("<KeyPress-a>", lambda e: self.set_move('left', True))
        self.root.bind("<KeyRelease-a>", lambda e: self.set_move('left', False))
        self.root.bind("<KeyPress-d>", lambda e: self.set_move('right', True))
        self.root.bind("<KeyRelease-d>", lambda e: self.set_move('right', False))
        self.root.bind("<space>", lambda e: self.handle_action())

        # Touch / Mouse Controls
        self.canvas.bind("<Motion>", self.on_touch_move)
        self.canvas.bind("<B1-Motion>", self.on_touch_move)
        self.canvas.bind("<Button-1>", self.on_touch_click)

    def set_move(self, direction, value):
        if direction == 'left':
            self.move_left = value
        elif direction == 'right':
            self.move_right = value

    def handle_action(self):
        if self.game_state in ["MENU", "GAMEOVER"]:
            self.start_new_game()
        elif self.game_state == "PLAYING":
            self.fire_laser()

    def on_touch_move(self, event):
        if self.game_state == "PLAYING":
            self.player_x = max(20, min(WIDTH - 20, event.x))

    def on_touch_click(self, event):
        if self.game_state in ["MENU", "GAMEOVER"]:
            self.start_new_game()
        elif self.game_state == "PLAYING":
            self.fire_laser()

    def start_new_game(self):
        self.score = 0
        self.wave = 1
        self.start_wave()

    def start_wave(self):
        self.player_x = WIDTH // 2
        self.lasers.clear()
        self.enemy_speed = INITIAL_ENEMY_SPEED + (self.wave - 1) * 0.8
        self.enemy_dir = 1
        self.spawn_enemies()
        self.game_state = "PLAYING"

    def spawn_enemies(self):
        self.enemies.clear()
        start_x = 45
        start_y = 80
        spacing_x = 52
        spacing_y = 38

        for r in range(ENEMY_ROWS):
            for c in range(ENEMY_COLS):
                self.enemies.append({
                    'x': start_x + c * spacing_x,
                    'y': start_y + r * spacing_y,
                    'alive': True
                })

    def fire_laser(self):
        if self.game_state == "PLAYING" and self.fire_cooldown <= 0:
            self.lasers.append({'x': self.player_x, 'y': self.player_y - 20})
            play_sound("laser")
            self.fire_cooldown = 5

    def game_loop(self):
        if self.game_state == "PLAYING":
            self.update_game_logic()
        
        self.draw_screen()
        self.root.after(GAME_FPS, self.game_loop)

    def update_game_logic(self):
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1

        if self.move_left:
            self.player_x = max(20, self.player_x - PLAYER_SPEED)
        if self.move_right:
            self.player_x = min(WIDTH - 20, self.player_x + PLAYER_SPEED)

        # Update Lasers
        for laser in self.lasers[:]:
            laser['y'] -= LASER_SPEED
            if laser['y'] < 0:
                self.lasers.remove(laser)

        # Update Enemies
        hit_wall = False
        alive_enemies = [e for e in self.enemies if e['alive']]

        if not alive_enemies:
            self.wave += 1
            self.start_wave()
            return

        for e in alive_enemies:
            e['x'] += self.enemy_speed * self.enemy_dir
            if e['x'] >= WIDTH - 20 or e['x'] <= 20:
                hit_wall = True

        if hit_wall:
            self.enemy_dir *= -1
            for e in alive_enemies:
                e['y'] += 16
                if e['y'] >= self.player_y - 25:
                    self.game_state = "GAMEOVER"
                    play_sound("explosion")
                    return

        # Collision Check
        for laser in self.lasers[:]:
            for e in alive_enemies:
                if abs(laser['x'] - e['x']) < 20 and abs(laser['y'] - e['y']) < 20:
                    e['alive'] = False
                    if laser in self.lasers:
                        self.lasers.remove(laser)
                    self.score += 100
                    play_sound("explosion")
                    break

    def draw_screen(self):
        self.canvas.delete("all")

        # Draw Background Stars
        for sx, sy in self.stars:
            self.canvas.create_rectangle(sx, sy, sx + 2, sy + 2, fill="#ffffff", outline="")

        # Top Bar
        self.canvas.create_rectangle(0, 0, WIDTH, 45, fill="#1e293b", outline="")
        self.canvas.create_text(60, 22, text=f"SCORE: {self.score}", font=("Arial", 12, "bold"), fill="#38bdf8")
        self.canvas.create_text(340, 22, text=f"WAVE: {self.wave}", font=("Arial", 12, "bold"), fill="#facc15")

        if self.game_state in ["PLAYING", "GAMEOVER"]:
            # Player
            if self.player_img:
                self.canvas.create_image(self.player_x, self.player_y, image=self.player_img)
            else:
                self.canvas.create_polygon(
                    self.player_x, self.player_y - 16,
                    self.player_x - 16, self.player_y + 14,
                    self.player_x + 16, self.player_y + 14,
                    fill="#38bdf8", outline="#ffffff", width=2
                )

            # Lasers
            for laser in self.lasers:
                self.canvas.create_line(laser['x'], laser['y'], laser['x'], laser['y'] - 10, fill="#facc15", width=3)

            # Enemies
            for e in self.enemies:
                if e['alive']:
                    if self.enemy_img:
                        self.canvas.create_image(e['x'], e['y'], image=self.enemy_img)
                    else:
                        self.canvas.create_oval(e['x'] - 12, e['y'] - 12, e['x'] + 12, e['y'] + 12, fill="#ef4444", outline="#ffffff", width=1)

        # Overlays
        if self.game_state == "MENU":
            self.canvas.create_rectangle(30, 180, 370, 380, fill="#1e293b", outline="#38bdf8", width=3)
            self.canvas.create_text(WIDTH // 2, 230, text="SPACE INVADERS", font=("Arial", 20, "bold"), fill="#38bdf8")
            self.canvas.create_text(WIDTH // 2, 280, text="Tap or Press SPACE to Start", font=("Arial", 12, "bold"), fill="#ffffff")
            self.canvas.create_text(WIDTH // 2, 330, text="Arrow Keys / Touch to Move", font=("Arial", 10), fill="#94a3b8")

        elif self.game_state == "GAMEOVER":
            self.canvas.create_rectangle(30, 180, 370, 380, fill="#1e293b", outline="#ef4444", width=3)
            self.canvas.create_text(WIDTH // 2, 230, text="GAME OVER", font=("Arial", 22, "bold"), fill="#ef4444")
            self.canvas.create_text(WIDTH // 2, 280, text=f"Final Score: {self.score}", font=("Arial", 14, "bold"), fill="#ffffff")
            self.canvas.create_text(WIDTH // 2, 330, text="Tap or Press SPACE to Play Again", font=("Arial", 11, "bold"), fill="#38bdf8")

if __name__ == "__main__":
    root = tk.Tk()
    game = RetroShooterGame(root)
    root.mainloop()
