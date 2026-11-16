import tkinter as tk
import random
import math
import os
import sys

# 1. Resolve Script Directory Path
try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_DIR = os.getcwd()

# 2. Try importing Pillow for full PNG transparency and resizing
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# 3. Try importing winsound for sound effects on Windows
try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

# ==============================================================================
# CONFIGURATION - ASSET PATHS
# ==============================================================================
BUG_IMAGE_PATH = os.path.join(SCRIPT_DIR, "bug.png")
HAMMER_IMAGE_PATH = os.path.join(SCRIPT_DIR, "hammer.png")
CRACK_IMAGE_PATH = os.path.join(SCRIPT_DIR, "crack.png")

SQUASH_SOUND_PATH = os.path.join(SCRIPT_DIR, "squash.wav")
SMASH_SOUND_PATH = os.path.join(SCRIPT_DIR, "smash.wav")
# ==============================================================================


def load_image(file_path, target_size=(60, 60)):
    if not os.path.exists(file_path):
        return None
    try:
        if HAS_PIL:
            pil_img = Image.open(file_path)
            pil_img = pil_img.resize(target_size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(pil_img)
        else:
            return tk.PhotoImage(file=file_path)
    except Exception as e:
        print(f"Warning: Could not load image {file_path}. Error: {e}")
        return None


class DesktopDestroyer:
    def __init__(self, root):
        self.root = root
        self.root.title("Desktop Destroyer")

        self.width = self.root.winfo_screenwidth()
        self.height = self.root.winfo_screenheight()
        self.root.geometry(f"{self.width}x{self.height}+0+0")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        trans_color = "gray15"
        self.root.config(bg=trans_color)
        self.root.wm_attributes("-transparentcolor", trans_color)

        self.canvas = tk.Canvas(self.root, bg=trans_color, highlightthickness=0, cursor="none")
        self.canvas.pack(fill="both", expand=True)

        self.bugs = []
        self.image_refs = []
        self.running = True

        self.load_assets()

        self.canvas.bind("<Motion>", self.move_hammer)
        self.canvas.bind("<Button-1>", self.whack)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self.create_hammer_icon()

        for _ in range(10):
            self.spawn_bug()

        self.update_game()

    def load_assets(self):
        self.bug_img = load_image(BUG_IMAGE_PATH, target_size=(60, 60))
        self.hammer_img = load_image(HAMMER_IMAGE_PATH, target_size=(70, 70))
        self.crack_img = load_image(CRACK_IMAGE_PATH, target_size=(120, 120))
        self.image_refs.extend([self.bug_img, self.hammer_img, self.crack_img])

    def play_sound(self, sound_path):
        """Plays WAV sound with error reporting to the IDLE Shell"""
        if not HAS_SOUND:
            print("Sound error: winsound module not available.")
            return
            
        if os.path.exists(sound_path):
            try:
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e:
                print(f"Failed to play sound '{os.path.basename(sound_path)}'. Ensure it is a valid PCM .wav file. Error: {e}")
        else:
            print(f"Sound file not found: {sound_path}")

    def create_hammer_icon(self):
        if self.hammer_img:
            self.hammer_id = self.canvas.create_image(0, 0, image=self.hammer_img, anchor="center")
        else:
            self.hammer_head = self.canvas.create_rectangle(-15, -25, 15, -10, fill="silver", outline="black")
            self.hammer_handle = self.canvas.create_line(0, -10, 0, 25, fill="brown", width=6)
            self.hammer_id = "fallback_hammer"

    def move_hammer(self, event):
        x, y = event.x, event.y
        if self.hammer_img:
            self.canvas.coords(self.hammer_id, x, y)
            self.canvas.tag_raise(self.hammer_id)
        else:
            self.canvas.coords(self.hammer_head, x - 15, y - 25, x + 15, y - 10)
            self.canvas.coords(self.hammer_handle, x, y - 10, x, y + 25)
            self.canvas.tag_raise(self.hammer_head)
            self.canvas.tag_raise(self.hammer_handle)

    def animate_hammer_swing(self, x, y):
        if self.hammer_img:
            self.canvas.coords(self.hammer_id, x + 12, y + 12)
            self.root.after(70, lambda: self.canvas.coords(self.hammer_id, x, y))

    def spawn_bug(self):
        x = random.randint(100, self.width - 100)
        y = random.randint(100, self.height - 100)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 4)

        if self.bug_img:
            bug_obj = self.canvas.create_image(x, y, image=self.bug_img)
            head_obj = None
        else:
            bug_obj = self.canvas.create_oval(x - 16, y - 20, x + 16, y + 20, fill="#1c1c1c", outline="#ff2222", width=2)
            head_obj = self.canvas.create_oval(x - 10, y - 28, x + 10, y - 14, fill="#8b0000")

        self.bugs.append({
            "body": bug_obj,
            "head": head_obj,
            "x": x,
            "y": y,
            "dx": math.cos(angle) * speed,
            "dy": math.sin(angle) * speed,
            "alive": True,
            "radius": 35
        })

    def draw_glass_crack(self, x, y):
        if self.crack_img:
            crack_id = self.canvas.create_image(x, y, image=self.crack_img)
            self.canvas.tag_lower(crack_id)
        else:
            for _ in range(random.randint(7, 10)):
                angle = random.uniform(0, 2 * math.pi)
                length = random.randint(50, 130)
                end_x = x + length * math.cos(angle)
                end_y = y + length * math.sin(angle)
                l1 = self.canvas.create_line(x, y, end_x, end_y, fill="white", width=2)
                l2 = self.canvas.create_line(x + 1, y + 1, end_x + 1, end_y + 1, fill="black", width=1)
                self.canvas.tag_lower(l1)
                self.canvas.tag_lower(l2)

    def whack(self, event):
        click_x, click_y = event.x, event.y
        self.animate_hammer_swing(click_x, click_y)

        hit_bug = False

        for bug in self.bugs:
            if bug["alive"]:
                dist = math.hypot(bug["x"] - click_x, bug["y"] - click_y)
                if dist <= bug["radius"]:
                    bug["alive"] = False
                    self.canvas.delete(bug["body"])
                    if bug["head"]:
                        self.canvas.delete(bug["head"])

                    splat = self.canvas.create_oval(
                        click_x - 22, click_y - 20, 
                        click_x + 22, click_y + 20, 
                        fill="#cc0000", outline="#550000", width=2
                    )
                    self.canvas.tag_lower(splat)

                    self.play_sound(SQUASH_SOUND_PATH)
                    hit_bug = True
                    break

        if not hit_bug:
            self.draw_glass_crack(click_x, click_y)
            self.play_sound(SMASH_SOUND_PATH)

    def update_game(self):
        for bug in self.bugs:
            if bug["alive"]:
                bug="alive" # placeholder check
                bug_dict = bug if isinstance(bug, dict) else None
                # standard coordinate update loop
                pass

        for b in self.bugs:
            if b["alive"]:
                b["x"] += b["dx"]
                b["y"] += b["dy"]

                if b["x"] <= 30 or b["x"] >= self.width - 30:
                    b["dx"] *= -1
                if b["y"] <= 30 or b["y"] >= self.height - 30:
                    b["dy"] *= -1

                if self.bug_img:
                    self.canvas.coords(b["body"], b["x"], b["y"])
                else:
                    self.canvas.coords(b["body"], b["x"] - 16, b["y"] - 20, b["x"] + 16, b["y"] + 20)
                    self.canvas.coords(b["head"], b["x"] - 10, b["y"] - 28, b["x"] + 10, b["y"] - 14)

        if self.running:
            self.root.after(30, self.update_game)

if __name__ == "__main__":
    root = tk.Tk()
    game = DesktopDestroyer(root)
    root.mainloop()
