import tkinter as tk
import math
import random
import os
import platform
import threading

# ==========================================
# 1. CUSTOM AUDIO FILE CONFIGURATION
# ==========================================
# Type your exact sound file names here (placed in the same folder as this script):
CUSTOM_SOUND_FILES = {
    "zombie_hit": "zombie_hit.wav",    # <-- CHANGE YOUR ZOMBIE HIT SOUND HERE
    "shoot": "shoot.wav",
    "shotgun": "shotgun.wav",
    "laser": "laser.wav",
    "player_hit": "player_hit.wav",
    "spit": "spit.wav",
    "gameover": "gameover.wav"
}

# Secondary keyword matching fallback if specific file is not found:
SOUND_KEYWORDS = {
    "zombie_hit": ["zombie_hit", "zombie", "hit", "groan", "hurt", "impact"],
    "shoot": ["shoot", "fire", "gun", "pew", "pistol", "rifle"],
    "shotgun": ["shotgun", "boom", "blast", "shell"],
    "laser": ["laser", "beam", "zap", "pulse"],
    "player_hit": ["player_hit", "damage", "hurt_player"],
    "spit": ["spit", "acid", "slime", "venom"],
    "gameover": ["gameover", "death", "die", "fail", "lose"]
}

# ==========================================
# SCRIPT PATH & ASSET RESOLUTION
# ==========================================
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

WIDTH, HEIGHT = 500, 650
GAME_FPS = 30 

# ==========================================
# AUDIO ENGINE
# ==========================================
PYGAME_AUDIO_READY = False
LOADED_SOUND_EFFECTS = {}

try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.mixer.set_num_channels(16)
    PYGAME_AUDIO_READY = True
    print("[AUDIO ENGINE] Pygame mixer initialized successfully.")
except Exception:
    PYGAME_AUDIO_READY = False
    print("[AUDIO ENGINE] Pygame unavailable. Falling back to native system audio.")

def scan_and_register_sounds():
    """Scans for custom sound files or matches keywords in directory."""
    global LOADED_SOUND_EFFECTS
    LOADED_SOUND_EFFECTS.clear()

    try:
        dir_files = os.listdir(BASE_DIR)
    except Exception:
        dir_files = []

    for action, target_filename in CUSTOM_SOUND_FILES.items():
        matched_file = None
        
        # 1. Check exact explicit filename
        exact_path = os.path.join(BASE_DIR, target_filename)
        if os.path.exists(exact_path):
            matched_file = exact_path
        else:
            # 2. Check keyword fallback
            keywords = SOUND_KEYWORDS.get(action, [action])
            for f in dir_files:
                f_lower = f.lower()
                if f_lower.endswith((".wav", ".mp3", ".ogg", ".m4a")):
                    if any(kw in f_lower for kw in keywords):
                        matched_file = os.path.join(BASE_DIR, f)
                        break

        if matched_file:
            print(f"[AUDIO MATCH] '{action}' -> Loaded: {os.path.basename(matched_file)}")
            if PYGAME_AUDIO_READY:
                try:
                    LOADED_SOUND_EFFECTS[action] = pygame.mixer.Sound(matched_file)
                except Exception as err:
                    print(f"[AUDIO ERROR] Pygame failed loading {matched_file}: {err}")
                    LOADED_SOUND_EFFECTS[action] = matched_file
            else:
                LOADED_SOUND_EFFECTS[action] = matched_file
        else:
            print(f"[AUDIO NOTICE] No sound file found for '{action}'. Using fallback beep.")

scan_and_register_sounds()

def trigger_fallback_beep(sound_type):
    try:
        if platform.system() == "Windows":
            import winsound
            freqs = {"shoot": 800, "laser": 1200, "shotgun": 400, "zombie_hit": 250, "player_hit": 180, "spit": 600, "gameover": 150}
            winsound.Beep(freqs.get(sound_type, 400), 30)
        else:
            print('\a', end='', flush=True)
    except Exception:
        pass

def _play_sound_async(sound_type):
    sound_obj = LOADED_SOUND_EFFECTS.get(sound_type)

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
    if target_file and platform.system() == "Windows":
        try:
            import winsound
            if target_file.lower().endswith(".wav"):
                winsound.PlaySound(target_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
        except Exception:
            pass
        try:
            import ctypes
            alias = f"snd_{random.randint(10000, 99999)}"
            ctypes.windll.winmm.mciSendStringW(f'open "{target_file}" alias {alias}', None, 0, 0)
            ctypes.windll.winmm.mciSendStringW(f'play {alias} from 0', None, 0, 0)
            return
        except Exception:
            pass

    if target_file and platform.system() == "Darwin":
        if os.system(f'afplay "{target_file}" &') == 0:
            return

    if target_file and platform.system() == "Linux":
        for cmd in [f'aplay -q "{target_file}" &', f'paplay "{target_file}" &']:
            if os.system(cmd) == 0:
                return

    trigger_fallback_beep(sound_type)

def play_sound(sound_type):
    threading.Thread(target=_play_sound_async, args=(sound_type,), daemon=True).start()

# ==========================================
# IMAGE LOADER
# ==========================================
def load_scaled_image(filenames, target_w, target_h):
    if isinstance(filenames, str):
        filenames = [filenames]

    target_path = None
    for name in filenames:
        p = os.path.join(BASE_DIR, name)
        if os.path.exists(p):
            target_path = p
            break

    if not target_path:
        return None

    try:
        from PIL import Image, ImageTk
        img = Image.open(target_path).resize((target_w, target_h))
        return ImageTk.PhotoImage(img)
    except Exception:
        pass

    try:
        native = tk.PhotoImage(file=target_path)
        sx = max(1, native.width() // target_w)
        sy = max(1, native.height() // target_h)
        return native.subsample(sx, sy)
    except Exception:
        return None

# ==========================================
# GAME CLASS
# ==========================================
class ZombieRPGGame:
    def __init__(self, root):
        self.root = root
        self.root.title("2D Zombie Survival - Custom Sounds")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#111827", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.bg_img = load_scaled_image(["background.png", "bg.png"], WIDTH, HEIGHT)
        self.player_img = load_scaled_image("player.png", 36, 36)
        self.zombie_imgs = {
            'walker': load_scaled_image(["zombie.png", "walker.png"], 32, 32),
            'runner': load_scaled_image(["runner.png", "fast_zombie.png"], 26, 26),
            'spitter': load_scaled_image(["spitter.png", "acid_zombie.png"], 30, 30),
            'tank': load_scaled_image(["tank.png", "boss.png"], 50, 50)
        }

        self.keys = {'w': False, 'a': False, 's': False, 'd': False,
                     'Up': False, 'Left': False, 'Down': False, 'Right': False}
        self.mouse_x, self.mouse_y = WIDTH // 2, HEIGHT // 2
        self.is_shooting = False

        self.game_state = "MENU"

        self.weapons = {
            '1': {'name': 'Pistol', 'cooldown': 8, 'damage_mult': 1.0, 'speed': 14, 'pellets': 1, 'spread': 0.0, 'pierce': 1, 'color': '#fef08a', 'snd': 'shoot'},
            '2': {'name': 'Shotgun', 'cooldown': 22, 'damage_mult': 0.7, 'speed': 12, 'pellets': 5, 'spread': 0.28, 'pierce': 1, 'color': '#f97316', 'snd': 'shotgun'},
            '3': {'name': 'Rifle', 'cooldown': 3, 'damage_mult': 0.5, 'speed': 16, 'pellets': 1, 'spread': 0.08, 'pierce': 1, 'color': '#facc15', 'snd': 'shoot'},
            '4': {'name': 'Laser', 'cooldown': 5, 'damage_mult': 1.4, 'speed': 25, 'pellets': 1, 'spread': 0.0, 'pierce': 3, 'color': '#06b6d4', 'snd': 'laser'}
        }
        self.active_weapon = '1'
        self.shoot_cooldown = 0

        self.player_x = WIDTH // 2
        self.player_y = HEIGHT // 2
        self.hp = 100
        self.max_hp = 100
        self.speed = 5.0
        self.damage = 40

        self.bullets = []
        self.enemy_bullets = []
        self.zombies = []
        self.wave = 1
        self.score = 0
        self.spawn_timer = 0

        self.bind_controls()
        self.game_loop()

    def bind_controls(self):
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    def on_key_press(self, e):
        k = e.keysym.lower() if len(e.keysym) == 1 else e.keysym

        if self.game_state == "PLAYING" and k in ['1', '2', '3', '4']:
            self.active_weapon = k
            return

        if k in self.keys:
            self.keys[k] = True
        elif e.keysym == "space":
            self.handle_action()

    def on_key_release(self, e):
        k = e.keysym.lower() if len(e.keysym) == 1 else e.keysym
        if k in self.keys:
            self.keys[k] = False

    def on_mouse_move(self, e):
        self.mouse_x, self.mouse_y = e.x, e.y

    def on_mouse_drag(self, e):
        self.mouse_x, self.mouse_y = e.x, e.y

    def on_mouse_down(self, e):
        self.mouse_x, self.mouse_y = e.x, e.y
        self.is_shooting = True
        self.handle_action()

    def on_mouse_up(self, e):
        self.is_shooting = False

    def handle_action(self):
        if self.game_state in ["MENU", "GAMEOVER"]:
            self.start_game()

    def start_game(self):
        self.hp = 100
        self.max_hp = 100
        self.speed = 5.0
        self.damage = 40
        self.wave = 1
        self.score = 0
        self.active_weapon = '1'
        self.player_x = WIDTH // 2
        self.player_y = HEIGHT // 2
        self.bullets.clear()
        self.enemy_bullets.clear()
        self.zombies.clear()
        self.game_state = "PLAYING"

    def shoot_active_weapon(self):
        if self.shoot_cooldown > 0:
            return

        w = self.weapons[self.active_weapon]
        self.shoot_cooldown = w['cooldown']

        dx = self.mouse_x - self.player_x
        dy = self.mouse_y - self.player_y
        base_angle = math.atan2(dy, dx)

        for _ in range(w['pellets']):
            spread_angle = base_angle + random.uniform(-w['spread'], w['spread'])
            vx = math.cos(spread_angle) * w['speed']
            vy = math.sin(spread_angle) * w['speed']

            self.bullets.append({
                'x': self.player_x, 'y': self.player_y,
                'vx': vx, 'vy': vy,
                'damage': self.damage * w['damage_mult'],
                'pierce': w['pierce'],
                'color': w['color'],
                'type': w['name'],
                'hit_zombies': set()
            })

        play_sound(w['snd'])

    def spawn_zombie(self):
        edge = random.choice(['top', 'bottom', 'left', 'right'])
        if edge == 'top': zx, zy = random.randint(0, WIDTH), -20
        elif edge == 'bottom': zx, zy = random.randint(0, WIDTH), HEIGHT + 20
        elif edge == 'left': zx, zy = -20, random.randint(0, HEIGHT)
        else: zx, zy = WIDTH + 20, random.randint(0, HEIGHT)

        choices = ['walker', 'walker', 'runner']
        if self.wave >= 2: choices.append('spitter')
        if self.wave >= 3 and random.random() < 0.25: choices.append('tank')

        z_type = random.choice(choices)
        if z_type == 'runner':
            hp, speed, radius, color, damage, pts = 30 + (self.wave * 5), random.uniform(3.5, 4.3) + (self.wave * 0.1), 12, "#eab308", 0.8, 20
        elif z_type == 'spitter':
            hp, speed, radius, color, damage, pts = 40 + (self.wave * 8), random.uniform(1.6, 2.2), 14, "#a855f7", 0.6, 35
        elif z_type == 'tank':
            hp, speed, radius, color, damage, pts = 180 + (self.wave * 45), random.uniform(0.8, 1.2), 24, "#991b1b", 3.5, 100
        else:
            hp, speed, radius, color, damage, pts = 50 + (self.wave * 10), random.uniform(1.8, 2.4) + (self.wave * 0.1), 15, "#22c55e", 1.2, 25

        self.zombies.append({
            'x': zx, 'y': zy, 'type': z_type, 'hp': hp, 'max_hp': hp,
            'speed': speed, 'radius': radius, 'color': color,
            'damage': damage, 'pts': pts, 'shoot_cooldown': random.randint(30, 90)
        })

    def game_loop(self):
        if self.game_state == "PLAYING":
            self.update_game()

        self.draw_screen()
        self.root.after(GAME_FPS, self.game_loop)

    def update_game(self):
        # 1. Player Movement
        dx, dy = 0, 0
        if self.keys['w'] or self.keys['Up']: dy -= 1
        if self.keys['s'] or self.keys['Down']: dy += 1
        if self.keys['a'] or self.keys['Left']: dx -= 1
        if self.keys['d'] or self.keys['Right']: dx += 1

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        self.player_x = max(20, min(WIDTH - 20, self.player_x + dx * self.speed))
        self.player_y = max(60, min(HEIGHT - 20, self.player_y + dy * self.speed))

        # 2. Shooting Cooldown
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

        if self.is_shooting:
            self.shoot_active_weapon()

        # 3. Zombie Spawning & Wave Scaling
        self.spawn_timer += 1
        spawn_rate = max(12, 40 - (self.wave * 3))
        if self.spawn_timer >= spawn_rate and len(self.zombies) < 25:
            self.spawn_timer = 0
            self.spawn_zombie()

        if self.score > self.wave * 500:
            self.wave += 1

        # 4. Bullets Update
        for b in self.bullets[:]:
            b['x'] += b['vx']
            b['y'] += b['vy']
            if b['x'] < 0 or b['x'] > WIDTH or b['y'] < 0 or b['y'] > HEIGHT:
                self.bullets.remove(b)

        # 5. Spit Bullets
        for eb in self.enemy_bullets[:]:
            eb['x'] += eb['vx']
            eb['y'] += eb['vy']
            if math.hypot(eb['x'] - self.player_x, eb['y'] - self.player_y) < 18:
                self.hp -= 12
                self.enemy_bullets.remove(eb)
                play_sound("player_hit")
                if self.hp <= 0:
                    self.hp = 0
                    self.game_state = "GAMEOVER"
                    play_sound("gameover")
                    return
            elif eb['x'] < 0 or eb['x'] > WIDTH or eb['y'] < 0 or eb['y'] > HEIGHT:
                self.enemy_bullets.remove(eb)

        # 6. Zombie Behavior & Collisions
        for z in self.zombies[:]:
            z_dx = self.player_x - z['x']
            z_dy = self.player_y - z['y']
            dist = math.hypot(z_dx, z_dy)

            if z['type'] == 'spitter':
                z['shoot_cooldown'] -= 1
                if dist < 280 and z['shoot_cooldown'] <= 0:
                    z['shoot_cooldown'] = random.randint(60, 100)
                    self.enemy_bullets.append({
                        'x': z['x'], 'y': z['y'],
                        'vx': (z_dx / dist) * 7.5, 'vy': (z_dy / dist) * 7.5
                    })
                    play_sound("spit")

            if dist > 0 and not (z['type'] == 'spitter' and dist < 160):
                z['x'] += (z_dx / dist) * z['speed']
                z['y'] += (z_dy / dist) * z['speed']

            # Player Collision
            if dist < (z['radius'] + 10):
                self.hp -= z['damage']
                if self.hp <= 0:
                    self.hp = 0
                    self.game_state = "GAMEOVER"
                    play_sound("gameover")
                    return

            # Bullet Collision
            for b in self.bullets[:]:
                if id(z) not in b['hit_zombies'] and math.hypot(b['x'] - z['x'], b['y'] - z['y']) < (z['radius'] + 6):
                    b['hit_zombies'].add(id(z))
                    z['hp'] -= b['damage']
                    b['pierce'] -= 1

                    # Play the dedicated Zombie Hit sound effect
                    play_sound("zombie_hit")

                    if b['pierce'] <= 0 and b in self.bullets:
                        self.bullets.remove(b)

                    if z['hp'] <= 0:
                        if z in self.zombies:
                            self.zombies.remove(z)
                        self.score += z['pts']
                        break

    def draw_screen(self):
        self.canvas.delete("all")

        # Background
        if self.bg_img:
            self.canvas.create_image(WIDTH // 2, HEIGHT // 2, image=self.bg_img)
        else:
            for x in range(0, WIDTH, 50): self.canvas.create_line(x, 50, x, HEIGHT, fill="#1f2937")
            for y in range(50, HEIGHT, 50): self.canvas.create_line(0, y, WIDTH, y, fill="#1f2937")

        # Top HUD
        self.canvas.create_rectangle(0, 0, WIDTH, 50, fill="#0f172a", outline="")
        
        # HP Bar
        self.canvas.create_rectangle(15, 14, 165, 32, fill="#374151", outline="#4b5563")
        self.canvas.create_rectangle(15, 14, 15 + (150 * max(0, self.hp / self.max_hp)), 32, fill="#ef4444", outline="")
        self.canvas.create_text(90, 23, text=f"HP {int(self.hp)}/{self.max_hp}", font=("Arial", 9, "bold"), fill="#ffffff")

        self.canvas.create_text(260, 23, text=f"WAVE {self.wave}", font=("Arial", 12, "bold"), fill="#10b981")
        self.canvas.create_text(400, 23, text=f"SCORE {self.score}", font=("Arial", 12, "bold"), fill="#ffffff")

        # Weapon Bar
        if self.game_state == "PLAYING":
            self.canvas.create_rectangle(0, HEIGHT - 35, WIDTH, HEIGHT, fill="#0f172a", outline="")
            for key, w in self.weapons.items():
                bx = 30 + (int(key) - 1) * 115
                is_active = (self.active_weapon == key)
                bg_col = "#1e293b" if not is_active else "#334155"
                border_col = w['color'] if is_active else "#475569"

                self.canvas.create_rectangle(bx, HEIGHT - 30, bx + 105, HEIGHT - 8, fill=bg_col, outline=border_col, width=2 if is_active else 1)
                self.canvas.create_text(bx + 52, HEIGHT - 19, text=f"[{key}] {w['name']}", font=("Arial", 9, "bold" if is_active else "normal"), fill=w['color'] if is_active else "#94a3b8")

        if self.game_state in ["PLAYING", "GAMEOVER"]:
            # Bullets
            for b in self.bullets:
                if b['type'] == 'Laser':
                    self.canvas.create_line(b['x'], b['y'], b['x'] - b['vx'] * 1.5, b['y'] - b['vy'] * 1.5, fill=b['color'], width=4)
                elif b['type'] == 'Shotgun':
                    self.canvas.create_oval(b['x'] - 4, b['y'] - 4, b['x'] + 4, b['y'] + 4, fill=b['color'], outline="")
                else:
                    self.canvas.create_oval(b['x'] - 3, b['y'] - 3, b['x'] + 3, b['y'] + 3, fill=b['color'], outline="")

            for eb in self.enemy_bullets:
                self.canvas.create_oval(eb['x'] - 5, eb['y'] - 5, eb['x'] + 5, eb['y'] + 5, fill="#a855f7", outline="#86efac", width=2)

            # Zombies
            for z in self.zombies:
                img = self.zombie_imgs.get(z['type']) or self.zombie_imgs.get('walker')
                if img:
                    self.canvas.create_image(z['x'], z['y'], image=img)
                else:
                    r = z['radius']
                    self.canvas.create_oval(z['x'] - r, z['y'] - r, z['x'] + r, z['y'] + r, fill=z['color'], outline="#ffffff", width=2)

                z_hp_ratio = max(0, z['hp'] / z['max_hp'])
                bar_w = z['radius'] * 1.5
                self.canvas.create_rectangle(z['x'] - bar_w, z['y'] - z['radius'] - 8, z['x'] + bar_w, z['y'] - z['radius'] - 5, fill="#374151", outline="")
                self.canvas.create_rectangle(z['x'] - bar_w, z['y'] - z['radius'] - 8, z['x'] - bar_w + (bar_w * 2 * z_hp_ratio), z['y'] - z['radius'] - 5, fill="#ef4444", outline="")

            # Player
            if self.player_img:
                self.canvas.create_image(self.player_x, self.player_y, image=self.player_img)
            else:
                self.canvas.create_oval(self.player_x - 16, self.player_y - 16, self.player_x + 16, self.player_y + 16, fill="#3b82f6", outline="#ffffff", width=2)

            # Crosshair
            w_col = self.weapons[self.active_weapon]['color']
            self.canvas.create_line(self.player_x, self.player_y, self.mouse_x, self.mouse_y, fill=w_col, dash=(2, 4))

        # Overlays
        if self.game_state == "MENU":
            self.canvas.create_rectangle(40, 190, 460, 430, fill="#1e293b", outline="#3b82f6", width=3)
            self.canvas.create_text(WIDTH // 2, 230, text="ZOMBIE SURVIVAL", font=("Arial", 20, "bold"), fill="#ef4444")
            self.canvas.create_text(WIDTH // 2, 280, text="WASD / Arrows = Move\nMouse Hold = Fire Weapon\nKeys 1-4 = Switch Weapons", font=("Arial", 11), fill="#ffffff", justify="center")
            self.canvas.create_text(WIDTH // 2, 360, text="Click or Press SPACE to Start", font=("Arial", 12, "bold"), fill="#3b82f6")

        elif self.game_state == "GAMEOVER":
            self.canvas.create_rectangle(40, 200, 460, 420, fill="#1e293b", outline="#ef4444", width=3)
            self.canvas.create_text(WIDTH // 2, 240, text="YOU DIED", font=("Arial", 24, "bold"), fill="#ef4444")
            self.canvas.create_text(WIDTH // 2, 290, text=f"Waves Survived: {self.wave} | Score: {self.score}", font=("Arial", 13, "bold"), fill="#ffffff")
            self.canvas.create_text(WIDTH // 2, 350, text="Click or Press SPACE to Restart", font=("Arial", 12, "bold"), fill="#3b82f6")

if __name__ == "__main__":
    root = tk.Tk()
    game = ZombieRPGGame(root)
    root.mainloop()
