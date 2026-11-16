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

TARGET_IMAGE_PATH = os.path.join(BASE_DIR, "mole.png")

# ==========================================
# CONFIGURATION
# ==========================================
WIDTH, HEIGHT = 400, 550
GAME_DURATION = 30  # Seconds per round
MOLE_POP_SPEED = 800  # Milliseconds mole stays up

HOLE_COORDS = [
    (80, 160),  (200, 160),  (320, 160),
    (80, 270),  (200, 270),  (320, 270),
    (80, 380),  (200, 380),  (320, 380)
]
HOLE_RADIUS_X, HOLE_RADIUS_Y = 45, 25

# ==========================================
# ADVANCED SOUND PLAYER (MULTI-PLATFORM)
# ==========================================
def trigger_fallback_beep(sound_type):
    """Fallback sound trigger if audio engines fail or files are missing."""
    try:
        if platform.system() == "Windows":
            import winsound
            freq = 1000 if sound_type == "whack" else 350
            winsound.Beep(freq, 80)
        else:
            print('\a', end='', flush=True)  # System bell
    except Exception:
        pass

def play_sound(sound_type):
    """
    Scans folder for audio files matching sound_type ('whack' or 'miss').
    Tries native players across Android (Pydroid 3), Windows, macOS, and Linux.
    """
    possible_names = []
    if sound_type == "whack":
        possible_names = ["whack", "hit", "pop", "punch", "smash", "click"]
    elif sound_type == "miss":
        possible_names = ["miss", "fail", "whoosh", "swish", "error"]
    else:
        possible_names = [sound_type]

    supported_exts = [".wav", ".mp3", ".ogg", ".m4a"]
    target_file = None

    try:
        files_in_dir = os.listdir(BASE_DIR)
    except Exception:
        files_in_dir = []

    # Case-insensitive file finder
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
        print(f"[SOUND LOG] No sound file found for '{sound_type}'. Searched folder for: {possible_names}")
        trigger_fallback_beep(sound_type)
        return

    print(f"[SOUND LOG] Playing: {os.path.basename(target_file)}")
    played = False

    # 1. Android Native MediaPlayer (Pydroid 3)
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

    # 2. Windows Native Players (winsound for WAV, MCI for MP3)
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

    # 3. macOS Native Player
    if not played and platform.system() == "Darwin":
        if os.system(f'afplay "{target_file}" &') == 0:
            played = True

    # 4. Linux / Shell Player Fallbacks
    if not played:
        for cmd in [f'aplay -q "{target_file}" &', f'paplay "{target_file}" &', f'ffplay -nodisp -autoexit "{target_file}" >/dev/null 2>&1 &']:
            if os.system(cmd) == 0:
                played = True
                break

    if not played:
        print(f"[SOUND LOG] Playback failed for '{os.path.basename(target_file)}'. Using fallback beep.")
        trigger_fallback_beep(sound_type)

# ==========================================
# GAME CLASS
# ==========================================
class WhackAMoleGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Whack-a-Mole Custom")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#4ade80", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.mole_photo = self.load_mole_png()
        
        self.game_state = "MENU"
        self.score = 0
        self.time_left = GAME_DURATION
        self.current_hole_index = None
        self.pop_job = None
        self.timer_job = None

        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.draw_screen()

    def load_mole_png(self):
        if not os.path.exists(TARGET_IMAGE_PATH):
            print(f"[IMAGE LOG] mole.png NOT found at: {TARGET_IMAGE_PATH}")
            return None

        try:
            from PIL import Image, ImageTk
            pil_img = Image.open(TARGET_IMAGE_PATH).resize((70, 70))
            print("[IMAGE LOG] Loaded mole.png using Pillow!")
            return ImageTk.PhotoImage(pil_img)
        except Exception:
            pass

        try:
            native_img = tk.PhotoImage(file=TARGET_IMAGE_PATH)
            scale_x = max(1, native_img.width() // 70)
            scale_y = max(1, native_img.height() // 70)
            scaled_img = native_img.subsample(scale_x, scale_y)
            print("[IMAGE LOG] Loaded mole.png natively!")
            return scaled_img
        except Exception as e:
            print(f"[IMAGE LOG] Native load failed: {e}")
            return None

    def start_game(self):
        self.score = 0
        self.time_left = GAME_DURATION
        self.game_state = "PLAYING"
        self.schedule_next_mole()
        self.update_timer()

    def update_timer(self):
        if self.game_state != "PLAYING":
            return

        if self.time_left > 0:
            self.time_left -= 1
            self.draw_screen()
            self.timer_job = self.root.after(1000, self.update_timer)
        else:
            self.end_game()

    def schedule_next_mole(self):
        if self.game_state != "PLAYING":
            return

        available_holes = [i for i in range(len(HOLE_COORDS)) if i != self.current_hole_index]
        self.current_hole_index = random.choice(available_holes)
        self.draw_screen()

        self.pop_job = self.root.after(MOLE_POP_SPEED, self.hide_mole_and_repeat)

    def hide_mole_and_repeat(self):
        self.current_hole_index = None
        self.draw_screen()
        delay = random.randint(200, 600)
        self.pop_job = self.root.after(delay, self.schedule_next_mole)

    def on_canvas_click(self, event):
        if self.game_state in ["MENU", "GAMEOVER"]:
            if self.pop_job:
                self.root.after_cancel(self.pop_job)
            if self.timer_job:
                self.root.after_cancel(self.timer_job)
            self.start_game()
            return

        if self.game_state == "PLAYING":
            hit = False
            if self.current_hole_index is not None:
                hx, hy = HOLE_COORDS[self.current_hole_index]
                distance = ((event.x - hx)**2 + (event.y - hy)**2)**0.5
                if distance <= 40:
                    hit = True

            if hit:
                self.score += 1
                play_sound("whack")
                if self.pop_job:
                    self.root.after_cancel(self.pop_job)
                self.current_hole_index = None
                self.draw_screen()
                self.pop_job = self.root.after(150, self.schedule_next_mole)
            else:
                play_sound("miss")

    def end_game(self):
        self.game_state = "GAMEOVER"
        self.current_hole_index = None
        if self.pop_job:
            self.root.after_cancel(self.pop_job)
        self.draw_screen()

    def draw_screen(self):
        self.canvas.delete("all")

        # Header Bar
        self.canvas.create_rectangle(0, 0, WIDTH, 80, fill="#15803d", outline="")
        self.canvas.create_text(80, 40, text=f"Score: {self.score}", font=("Impact", 22), fill="#ffffff")
        self.canvas.create_text(300, 40, text=f"Time: {self.time_left}s", font=("Impact", 22), fill="#ffffff")

        # Holes
        for x, y in HOLE_COORDS:
            self.canvas.create_oval(x - HOLE_RADIUS_X - 4, y - HOLE_RADIUS_Y - 4,
                                    x + HOLE_RADIUS_X + 4, y + HOLE_RADIUS_Y + 4,
                                    fill="#78350f", outline="")
            self.canvas.create_rectangle(x - HOLE_RADIUS_X, y - HOLE_RADIUS_Y,
                                    x + HOLE_RADIUS_X, y + HOLE_RADIUS_Y,
                                    fill="#271c19", outline="")

        # Active Mole
        if self.current_hole_index is not None:
            hx, hy = HOLE_COORDS[self.current_hole_index]
            mole_y = hy - 25

            if self.mole_photo:
                self.canvas.create_image(hx, mole_y, image=self.mole_photo)
            else:
                self.canvas.create_oval(hx - 30, mole_y - 30, hx + 30, mole_y + 30, fill="#b45309", outline="#000", width=2)
                self.canvas.create_oval(hx - 12, mole_y - 10, hx - 4, mole_y - 2, fill="#fff")
                self.canvas.create_oval(hx + 4, mole_y - 10, hx + 12, mole_y - 2, fill="#fff")
                self.canvas.create_oval(hx - 10, mole_y - 8, hx - 6, mole_y - 4, fill="#000")
                self.canvas.create_oval(hx + 6, mole_y - 8, hx + 10, mole_y - 4, fill="#000")
                self.canvas.create_oval(hx - 8, mole_y + 2, hx + 8, mole_y + 12, fill="#fbcfe8")

        # Overlays
        if self.game_state == "MENU":
            self.canvas.create_rectangle(40, 180, 360, 380, fill="#ffffff", outline="#15803d", width=4)
            self.canvas.create_text(WIDTH // 2, 230, text="WHACK-A-MOLE", font=("Impact", 28), fill="#15803d")
            self.canvas.create_text(WIDTH // 2, 290, text="Tap anywhere to Start!", font=("Arial", 14, "bold"), fill="#000000")
            self.canvas.create_text(WIDTH // 2, 330, text=f"{GAME_DURATION} Seconds Round", font=("Arial", 11), fill="#666666")

        elif self.game_state == "GAMEOVER":
            self.canvas.create_rectangle(40, 180, 360, 380, fill="#ffffff", outline="#ef4444", width=4)
            self.canvas.create_text(WIDTH // 2, 220, text="TIME'S UP!", font=("Impact", 28), fill="#ef4444")
            self.canvas.create_text(WIDTH // 2, 270, text=f"Final Score: {self.score}", font=("Arial", 18, "bold"), fill="#000000")
            self.canvas.create_text(WIDTH // 2, 320, text="Tap anywhere to Play Again", font=("Arial", 14, "bold"), fill="#15803d")

if __name__ == "__main__":
    root = tk.Tk()
    game = WhackAMoleGame(root)
    root.mainloop()
