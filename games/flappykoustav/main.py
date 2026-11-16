import tkinter as tk
import random
import os
import platform

# ==========================================
# SCRIPT PATH RESOLUTION
# ==========================================
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.getcwd()

BIRD_IMAGE_PATH = os.path.join(BASE_DIR, "bird.png")

# ==========================================
# CONFIGURATION
# ==========================================
WIDTH, HEIGHT = 400, 600
GROUND_Y = 550
GRAVITY = 0.5
JUMP_STRENGTH = -8.5
PIPE_SPEED = 3
PIPE_GAP = 150
SPAWN_INTERVAL = 90

# ==========================================
# MULTI-PLATFORM AUDIO PLAYER (NO PYGAME)
# ==========================================
def play_sound(filename_base):
    """Plays WAV, MP3, or OGG sounds on Android (Pydroid 3), Windows, Mac, and Linux."""
    target_file = None
    for ext in [".wav", ".mp3", ".ogg"]:
        path = os.path.join(BASE_DIR, filename_base + ext)
        if os.path.exists(path):
            target_file = path
            break

    if not target_file:
        print(f"[DEBUG Sound] '{filename_base}' (.wav/.mp3) NOT found in: {BASE_DIR}")
        return

    # 1. Android Native Media Player (Pydroid 3)
    try:
        from jnius import autoclass
        MediaPlayer = autoclass('android.media.MediaPlayer')
        mp = MediaPlayer()
        mp.setDataSource(target_file)
        mp.prepare()
        mp.start()
        print(f"[SUCCESS Sound] Playing '{filename_base}' on Android!")
        return
    except Exception:
        pass

    # 2. Windows Native Player
    sys_name = platform.system()
    if sys_name == "Windows":
        try:
            if target_file.endswith(".wav"):
                import winsound
                winsound.PlaySound(target_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                import ctypes
                alias = f"snd_{random.randint(1000, 9999)}"
                ctypes.windll.winmm.mciSendStringW(f'open "{target_file}" alias {alias}', None, 0, 0)
                ctypes.windll.winmm.mciSendStringW(f'play {alias} from 0', None, 0, 0)
            print(f"[SUCCESS Sound] Playing '{filename_base}' on Windows!")
            return
        except Exception as e:
            print(f"[ERROR Sound Windows]: {e}")

    # 3. macOS Native Player
    elif sys_name == "Darwin":
        os.system(f'afplay "{target_file}" &')
        return

    # 4. Linux / System Commands Fallback
    for cmd in [f'paplay "{target_file}" &', f'aplay -q "{target_file}" &', f'ffplay -nodisp -autoexit "{target_file}" >/dev/null 2>&1 &']:
        if os.system(cmd) == 0:
            print(f"[SUCCESS Sound] Playing '{filename_base}' on Linux!")
            return

# ==========================================
# GAME CLASS
# ==========================================
class FlappyBirdGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Flappy Bird")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#70c5ce", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.bird_photo = self.load_bird_png()

        # Controls
        self.root.bind("<space>", self.on_action)
        self.root.bind("<Button-1>", self.on_action)

        self.game_state = "MENU"
        self.bird_x = 80
        self.bird_y = HEIGHT // 2
        self.bird_vy = 0
        self.pipes = []
        self.score = 0
        self.frame_count = 0

        self.game_loop()

    def load_bird_png(self):
        if not os.path.exists(BIRD_IMAGE_PATH):
            print(f"[DEBUG Image] bird.png NOT found at: {BIRD_IMAGE_PATH}")
            return None

        try:
            from PIL import Image, ImageTk
            pil_img = Image.open(BIRD_IMAGE_PATH).resize((40, 30))
            print("[SUCCESS Image] Loaded bird.png using Pillow!")
            return ImageTk.PhotoImage(pil_img)
        except Exception:
            pass

        try:
            native_img = tk.PhotoImage(file=BIRD_IMAGE_PATH)
            scale_x = max(1, native_img.width() // 40)
            scale_y = max(1, native_img.height() // 30)
            scaled_img = native_img.subsample(scale_x, scale_y)
            print("[SUCCESS Image] Loaded bird.png using Tkinter native!")
            return scaled_img
        except Exception as e:
            print(f"[ERROR Image] Native load failed: {e}")
            return None

    def reset_game(self):
        self.bird_y = HEIGHT // 2
        self.bird_vy = 0
        self.pipes.clear()
        self.score = 0
        self.frame_count = 0
        self.game_state = "PLAYING"

    def on_action(self, event=None):
        if self.game_state == "MENU":
            self.reset_game()
        elif self.game_state == "PLAYING":
            self.bird_vy = JUMP_STRENGTH
            play_sound("jump")
        elif self.game_state == "GAMEOVER":
            self.reset_game()

    def spawn_pipe(self):
        gap_y = random.randint(120, GROUND_Y - 120 - PIPE_GAP)
        self.pipes.append({
            "x": WIDTH,
            "gap_y": gap_y,
            "passed": False
        })

    def update_physics(self):
        if self.game_state != "PLAYING":
            return

        self.bird_vy += GRAVITY
        self.bird_y += self.bird_vy

        self.frame_count += 1
        if self.frame_count >= SPAWN_INTERVAL:
            self.spawn_pipe()
            self.frame_count = 0

        for p in self.pipes:
            p["x"] -= PIPE_SPEED
            if not p["passed"] and p["x"] + 60 < self.bird_x:
                self.score += 1
                p["passed"] = True

        self.pipes = [p for p in self.pipes if p["x"] > -70]

        if self.check_collision():
            self.game_state = "GAMEOVER"
            play_sound("die")

    def check_collision(self):
        bird_radius = 14
        if self.bird_y + bird_radius >= GROUND_Y or self.bird_y - bird_radius <= 0:
            return True

        b_left = self.bird_x - bird_radius
        b_right = self.bird_x + bird_radius
        b_top = self.bird_y - bird_radius
        b_bot = self.bird_y + bird_radius

        for p in self.pipes:
            px1 = p["x"]
            px2 = p["x"] + 60
            top_pipe_bottom = p["gap_y"]
            bot_pipe_top = p["gap_y"] + PIPE_GAP

            if b_right > px1 and b_left < px2:
                if b_top < top_pipe_bottom or b_bot > bot_pipe_top:
                    return True

        return False

    def draw(self):
        self.canvas.delete("all")

        # Draw Pipes
        for p in self.pipes:
            px = p["x"]
            gap_y = p["gap_y"]
            self.canvas.create_rectangle(px, 0, px + 60, gap_y, fill="#73bf2e", outline="#538c1f", width=3)
            self.canvas.create_rectangle(px, gap_y + PIPE_GAP, px + 60, GROUND_Y, fill="#73bf2e", outline="#538c1f", width=3)

        # Draw Ground
        self.canvas.create_rectangle(0, GROUND_Y, WIDTH, HEIGHT, fill="#ded895", outline="")
        self.canvas.create_line(0, GROUND_Y, WIDTH, GROUND_Y, fill="#000000", width=2)

        # Draw Bird
        if self.bird_photo:
            self.canvas.create_image(self.bird_x, int(self.bird_y), image=self.bird_photo)
        else:
            self.canvas.create_oval(
                self.bird_x - 15, int(self.bird_y) - 15,
                self.bird_x + 15, int(self.bird_y) + 15,
                fill="#facc15", outline="#000000", width=2
            )
            self.canvas.create_oval(self.bird_x + 5, int(self.bird_y) - 6, self.bird_x + 10, int(self.bird_y) - 1, fill="#000000")

        # HUD
        if self.game_state == "PLAYING":
            self.canvas.create_text(WIDTH // 2, 40, text=str(self.score), font=("Impact", 36), fill="#ffffff")
        elif self.game_state == "MENU":
            self.canvas.create_text(WIDTH // 2, 180, text="FLAPPY BIRD", font=("Impact", 32), fill="#ffffff")
            self.canvas.create_text(WIDTH // 2, 240, text="Tap or press Space to Start", font=("Arial", 14, "bold"), fill="#000000")
        elif self.game_state == "GAMEOVER":
            self.canvas.create_text(WIDTH // 2, 160, text="GAME OVER", font=("Impact", 34), fill="#ef4444")
            self.canvas.create_text(WIDTH // 2, 220, text=f"Score: {self.score}", font=("Arial", 16, "bold"), fill="#ffffff")
            self.canvas.create_text(WIDTH // 2, 270, text="Tap or press Space to Restart", font=("Arial", 14, "bold"), fill="#000000")

    def game_loop(self):
        self.update_physics()
        self.draw()
        self.root.after(20, self.game_loop)

if __name__ == "__main__":
    root = tk.Tk()
    game = FlappyBirdGame(root)
    root.mainloop()
