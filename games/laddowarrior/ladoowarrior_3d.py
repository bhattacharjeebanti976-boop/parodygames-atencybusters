import pygame
import math
import random
import os
import sys

# ==========================================
# CONFIGURATION & ASSET SLOTS
# ==========================================
WIDTH, HEIGHT = 1024, 768
FOV = 480  # 3D Perspective Projection Focal Length
FOG_DISTANCE = 18.0  # Max view distance for fog shading

WEAPON_IMAGE_FILE = "weapon.png"

MONSTER_CONFIG = [
    {"name": "Bitter Gourd Creeper", "hp": 120, "atk": 8,  "speed": 0.03, "image": "monster1.png", "ability": "1: Ladoo Throw"},
    {"name": "Salty Enderman",       "hp": 200, "atk": 12, "speed": 0.04, "image": "monster2.png", "ability": "2: Sugar Shield (Heal)"},
    {"name": "Spicy Blaze Goblin",   "hp": 300, "atk": 18, "speed": 0.05, "image": "monster3.png", "ability": "3: Cardamom Burst (Heavy)"},
    {"name": "Sour Ice Golem",       "hp": 450, "atk": 24, "speed": 0.06, "image": "monster4.png", "ability": "4: Syrup Freeze (Stun)"},
    {"name": "Wither Phantom",       "hp": 600, "atk": 32, "speed": 0.07, "image": "monster5.png", "ability": "5: Ghee Rage (2x Damage)"},
    {"name": "BOSS: KING GULAB JAMUN", "hp": 1100, "atk": 45, "speed": 0.08, "image": "boss.png", "ability": "6: MAHA BLAST (Ultimate)"}
]

AUDIO_FILES = {
    "attack": "attack.wav",
    "monster_hit": "hit.wav",
    "heal": "heal.wav",
    "win": "win.wav"
}

# ==========================================
# MINECRAFT TEXTURE GENERATOR (PROCEDURAL)
# ==========================================
def generate_mc_textures():
    """Generates procedural 16x16 pixelated Minecraft textures."""
    textures = {}
    
    # Sand Texture (Yellow Desert Sand)
    sand = pygame.Surface((16, 16))
    sand.fill((225, 215, 145))
    for x in range(16):
        for y in range(16):
            if random.random() < 0.3:
                sand.set_at((x, y), (240, 230, 160))
            elif random.random() < 0.15:
                sand.set_at((x, y), (200, 190, 125))
    textures["sand"] = sand

    # Stone Block Texture
    stone = pygame.Surface((16, 16))
    stone.fill((125, 125, 125))
    for x in range(16):
        for y in range(16):
            v = random.randint(-25, 25)
            c = max(0, min(255, 125 + v))
            stone.set_at((x, y), (c, c, c))
    textures["stone"] = stone

    # Oak Wood Log Texture
    wood = pygame.Surface((16, 16))
    wood.fill((102, 76, 40))
    for y in range(16):
        for x in range(16):
            if x in [0, 4, 8, 12] or random.random() < 0.1:
                wood.set_at((x, y), (70, 50, 25))
    textures["wood"] = wood

    return textures

# ==========================================
# SOUND MANAGER
# ==========================================
class SoundManager:
    def __init__(self):
        pygame.mixer.init()
        self.sounds = {}
        for key, path in AUDIO_FILES.items():
            if os.path.exists(path):
                try:
                    self.sounds[key] = pygame.mixer.Sound(path)
                except Exception:
                    pass

    def play(self, key):
        if key in self.sounds:
            self.sounds[key].play()
        else:
            print(f"[AUDIO EVENT]: {key}")

# ==========================================
# 3D VOXEL PARTICLE SYSTEM
# ==========================================
class VoxelParticle3D:
    def __init__(self, x, y, z, color, vx, vy, vz, size=0.2):
        self.x, self.y, self.z = x, y, z
        self.color = color
        self.vx, self.vy, self.vz = vx, vy, vz
        self.size = size
        self.life = 1.0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.z += self.vz
        self.vy -= 0.01  # Gravity effect
        self.life -= 0.03

# ==========================================
# MAIN 3D MINECRAFT ACTION ENGINE
# ==========================================
class LadooWarriorMinecraft:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("LadooWarrior 3D - Sand Arena Edition")
        self.clock = pygame.time.Clock()

        # Mouse capture for 1st-person camera
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)

        self.sound = SoundManager()
        self.font = pygame.font.SysFont("Impact", 20)
        self.title_font = pygame.font.SysFont("Impact", 36)
        self.hud_font = pygame.font.SysFont("Arial", 14, bold=True)

        # Generate Minecraft Procedural Textures
        self.mc_textures = generate_mc_textures()

        # Player State
        self.px, self.py, self.pz = 0.0, 0.5, -7.0  # Player Position
        self.yaw = 0.0                              # Camera Yaw Rotation
        self.pitch = 0.0                            # Vertical Pitch
        self.player_max_hp = 20  # 20 Health Points (10 Minecraft Hearts)
        self.player_hp = 20
        self.buff_multiplier = 1.0

        # Animation states
        self.swing_angle = 0.0
        self.is_swinging = False

        # Round & Cooldown state
        self.round_num = 0
        self.cooldowns = {"heal": 0, "heavy": 0, "stun": 0, "buff": 0, "ult": 0}

        # Monster State
        self.mx, self.my, self.mz = 0.0, 0.5, 5.0
        self.monster_hp = 100
        self.monster_max_hp = 100
        self.monster_stunned_timer = 0
        self.monster_attack_cooldown = 0
        self.monster_recoil = 0.0

        # Minecraft Environment Elements
        self.clouds = [{"x": random.uniform(-30, 30), "z": random.uniform(-10, 40), "w": random.uniform(6, 12)} for _ in range(12)]

        # Build 3D Arena Map (Voxel Coordinates)
        self.build_arena_world()

        # Load Custom Textures/Images
        self.load_assets()

        self.particles = []
        self.combat_log = "WELCOME TO LADOO WARRIOR - DESERT SAND ARENA!"
        self.log_timer = 180

        self.start_round(0)

    def build_arena_world(self):
        """Constructs a 3D Minecraft Voxel Arena map with Sand floor and Stone walls."""
        self.blocks = []
        arena_size = 8

        # Floor (Sand Blocks)
        for x in range(-arena_size, arena_size + 1):
            for z in range(-arena_size, arena_size + 1):
                self.blocks.append({"pos": (x, -0.5, z), "type": "sand"})

        # Border Walls (Stone Blocks)
        for x in range(-arena_size, arena_size + 1):
            for z in range(-arena_size, arena_size + 1):
                if abs(x) == arena_size or abs(z) == arena_size:
                    self.blocks.append({"pos": (x, 0.5, z), "type": "stone"})
                    self.blocks.append({"pos": (x, 1.5, z), "type": "stone"})

        # Corner Pillars (Oak Log)
        for cx in [-arena_size, arena_size]:
            for cz in [-arena_size, arena_size]:
                for h in range(3):
                    self.blocks.append({"pos": (cx, h + 0.5, cz), "type": "wood"})

    def load_assets(self):
        self.monster_sprites = {}
        self.weapon_texture = None

        if os.path.exists(WEAPON_IMAGE_FILE):
            try:
                img = pygame.image.load(WEAPON_IMAGE_FILE).convert_alpha()
                self.weapon_texture = pygame.transform.scale(img, (240, 240))
            except Exception as e:
                print(f"Could not load custom weapon: {e}")

        for i, m in enumerate(MONSTER_CONFIG):
            if os.path.exists(m["image"]):
                try:
                    img = pygame.image.load(m["image"]).convert_alpha()
                    self.monster_sprites[i] = img
                except Exception as e:
                    print(f"Could not load monster image {m['image']}: {e}")

    def start_round(self, r_index):
        self.round_num = r_index
        cfg = MONSTER_CONFIG[r_index]
        self.mx, self.my, self.mz = 0.0, 0.5, 6.0
        self.monster_hp = cfg["hp"]
        self.monster_max_hp = cfg["hp"]
        self.monster_stunned_timer = 0
        
        self.px, self.py, self.pz = 0.0, 0.5, -6.0
        self.yaw = 0.0

        self.combat_log = f"ROUND {r_index + 1}: {cfg['name']} SPAWNED! UNLOCKED: {cfg['ability']}"
        self.log_timer = 200

    # ==========================================
    # 3D PERSPECTIVE PROJECTION & CAMERA ENGINE
    # ==========================================
    def project_3d(self, x, y, z):
        """Transforms 3D World space (X, Y, Z) to 2D Screen Space with Pitch & Yaw."""
        dx = x - self.px
        dy = y - self.py
        dz = z - self.pz

        # Horizontal Yaw Rotation
        cos_y, sin_y = math.cos(self.yaw), math.sin(self.yaw)
        rx = dx * cos_y - dz * sin_y
        rz = dx * sin_y + dz * cos_y

        # Vertical Pitch Rotation
        cos_p, sin_p = math.cos(self.pitch), math.sin(self.pitch)
        ry = dy * cos_p - rz * sin_p
        rz_final = dy * sin_p + rz * cos_p

        if rz_final <= 0.1:
            return None, None, rz_final

        screen_x = int(WIDTH / 2 + (rx / rz_final) * FOV)
        screen_y = int(HEIGHT / 2 - (ry / rz_final) * FOV)
        return screen_x, screen_y, rz_final

    # ==========================================
    # MINECRAFT CUBE / VOXEL RENDERER
    # ==========================================
    def draw_3d_cube(self, bx, by, bz, b_type):
        """Renders a shaded 3D Minecraft voxel block centered at (bx, by, bz)."""
        dist = math.sqrt((bx - self.px)**2 + (by - self.py)**2 + (bz - self.pz)**2)
        if dist > FOG_DISTANCE:
            return

        # Fog shading factor
        fog = max(0.1, min(1.0, 1.0 - (dist / FOG_DISTANCE)))

        # Block corners (unit cube offset = 0.5)
        h = 0.5
        v = [
            (bx - h, by + h, bz - h), (bx + h, by + h, bz - h),
            (bx + h, by + h, bz + h), (bx - h, by + h, bz + h),
            (bx - h, by - h, bz - h), (bx + h, by - h, bz - h),
            (bx + h, by - h, bz + h), (bx - h, by - h, bz + h)
        ]

        proj = [self.project_3d(pt[0], pt[1], pt[2]) for pt in v]

        # Base block colors with Sand & Stone palette
        if b_type == "sand":
            top_col = (int(225 * fog), int(215 * fog), int(145 * fog))
            side_col = (int(200 * fog), int(190 * fog), int(125 * fog))
        elif b_type == "stone":
            top_col = side_col = (int(125 * fog), int(125 * fog), int(125 * fog))
        else: # Wood
            top_col = side_col = (int(102 * fog), int(76 * fog), int(40 * fog))

        # Face definition indices & Directional Shading
        faces = [
            ([0, 1, 2, 3], top_col, 1.0),                               # Top Face
            ([4, 5, 1, 0], tuple(int(c * 0.8) for c in side_col), 0.8), # Front Face
            ([5, 6, 2, 1], tuple(int(c * 0.6) for c in side_col), 0.6), # Right Face
            ([6, 7, 3, 2], tuple(int(c * 0.8) for c in side_col), 0.8), # Back Face
            ([7, 4, 0, 3], tuple(int(c * 0.6) for c in side_col), 0.6), # Left Face
        ]

        for indices, col, shade in faces:
            pts = [proj[i][:2] for i in indices]
            if all(p[0] is not None for p in pts):
                # Backface Culling check
                vec1 = (pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
                vec2 = (pts[2][0] - pts[0][0], pts[2][1] - pts[0][1])
                cross = vec1[0] * vec2[1] - vec1[1] * vec2[0]
                if cross > 0:
                    pygame.draw.polygon(self.screen, col, pts)
                    pygame.draw.polygon(self.screen, (int(col[0]*0.7), int(col[1]*0.7), int(col[2]*0.7)), pts, 1)

    # ==========================================
    # INPUT & MOVEMENT LOGIC
    # ==========================================
    def handle_input(self):
        keys = pygame.key.get_pressed()
        move_speed = 0.12

        dx = math.sin(self.yaw) * move_speed
        dz = math.cos(self.yaw) * move_speed

        if keys[pygame.K_w]:
            self.px += dx
            self.pz += dz
        if keys[pygame.K_s]:
            self.px -= dx
            self.pz -= dz
        if keys[pygame.K_a]:
            self.px -= dz
            self.pz += dx
        if keys[pygame.K_d]:
            self.px += dz
            self.pz -= dx

        self.px = max(-7.0, min(7.0, self.px))
        self.pz = max(-7.0, min(7.0, self.pz))

        mouse_dx, mouse_dy = pygame.mouse.get_rel()
        self.yaw += mouse_dx * 0.003
        self.pitch = max(-0.5, min(0.5, self.pitch - mouse_dy * 0.003))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key in [pygame.K_1, pygame.K_SPACE]:
                    self.use_attack()
                elif event.key == pygame.K_2 and self.round_num >= 1:
                    self.use_heal()
                elif event.key == pygame.K_3 and self.round_num >= 2:
                    self.use_heavy()
                elif event.key == pygame.K_4 and self.round_num >= 3:
                    self.use_stun()
                elif event.key == pygame.K_5 and self.round_num >= 4:
                    self.use_buff()
                elif event.key == pygame.K_6 and self.round_num >= 5:
                    self.use_ult()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.use_attack()

        return True

    # ==========================================
    # COMBAT & ABILITY SYSTEM
    # ==========================================
    def trigger_attack(self, damage, log_text, color=(255, 215, 0)):
        self.is_swinging = True
        self.swing_angle = 45.0
        self.sound.play("attack")
        
        final_damage = int(damage * self.buff_multiplier)
        self.buff_multiplier = 1.0

        dist = math.sqrt((self.px - self.mx)**2 + (self.pz - self.mz)**2)
        if dist < 9.0:
            self.monster_hp -= final_damage
            self.monster_recoil = 0.4
            self.combat_log = f"{log_text}! Dealt {final_damage} damage!"
            self.log_timer = 150

            for _ in range(16):
                self.particles.append(VoxelParticle3D(
                    self.mx, self.my, self.mz, color,
                    random.uniform(-0.2, 0.2), random.uniform(0.1, 0.3), random.uniform(-0.2, 0.2)
                ))

            if self.monster_hp <= 0:
                self.sound.play("win")
                if self.round_num == 5:
                    self.combat_log = "VICTORY! KING GULAB JAMUN VANQUISHED!"
                else:
                    self.start_round(self.round_num + 1)
        else:
            self.combat_log = "Target out of reach!"
            self.log_timer = 100

    def use_attack(self):
        self.trigger_attack(25, "Ladoo Sword Slash", (255, 170, 0))

    def use_heal(self):
        if self.cooldowns["heal"] <= 0:
            self.sound.play("heal")
            self.player_hp = min(self.player_max_hp, self.player_hp + 6)
            self.cooldowns["heal"] = 180
            self.combat_log = "Golden Apple Shield! Restored Hearts."
            self.log_timer = 150

    def use_heavy(self):
        if self.cooldowns["heavy"] <= 0:
            self.cooldowns["heavy"] = 240
            self.trigger_attack(65, "CARDAMOM CRIT HIT", (255, 50, 50))

    def use_stun(self):
        if self.cooldowns["stun"] <= 0:
            self.cooldowns["stun"] = 300
            self.monster_stunned_timer = 180
            self.trigger_attack(20, "ICE FREEZE STUN!", (100, 200, 255))

    def use_buff(self):
        if self.cooldowns["buff"] <= 0:
            self.cooldowns["buff"] = 360
            self.buff_multiplier = 2.0
            self.combat_log = "Ghee Strength II Potion! DOUBLE DAMAGE."
            self.log_timer = 150

    def use_ult(self):
        if self.cooldowns["ult"] <= 0:
            self.cooldowns["ult"] = 450
            self.trigger_attack(200, "MAHA LADOO BLAST ULTIMATE", (255, 215, 0))

    # ==========================================
    # UPDATE ENGINE
    # ==========================================
    def update(self):
        for k in self.cooldowns:
            if self.cooldowns[k] > 0:
                self.cooldowns[k] -= 1

        if self.is_swinging:
            self.swing_angle -= 4.0
            if self.swing_angle <= 0:
                self.swing_angle = 0
                self.is_swinging = False

        if self.monster_recoil > 0:
            self.monster_recoil -= 0.05

        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

        for c in self.clouds:
            c["x"] += 0.01
            if c["x"] > 30:
                c["x"] = -30

        if self.monster_hp > 0:
            cfg = MONSTER_CONFIG[self.round_num]
            if self.monster_stunned_timer > 0:
                self.monster_stunned_timer -= 1
            else:
                dx = self.px - self.mx
                dz = self.pz - self.mz
                dist = math.sqrt(dx*dx + dz*dz)

                if dist > 1.8:
                    self.mx += (dx / dist) * cfg["speed"]
                    self.mz += (dz / dist) * cfg["speed"]

                self.monster_attack_cooldown += 1
                if self.monster_attack_cooldown >= 90:
                    self.monster_attack_cooldown = 0
                    if dist < 2.5:
                        self.sound.play("monster_hit")
                        self.player_hp -= max(1, cfg["atk"] // 5)
                        self.combat_log = f"{cfg['name']} attacked you!"
                        self.log_timer = 120

    # ==========================================
    # MINECRAFT RENDERING ENGINE
    # ==========================================
    def render(self):
        pitch_offset = int(self.pitch * FOV)
        horizon_y = HEIGHT // 2 + pitch_offset

        # 1. Sky Top Fill (Desert Sky Blue)
        self.screen.fill((135, 206, 235))
        
        # 2. Ground Background Fill (Desert Sand Color)
        if horizon_y < HEIGHT:
            pygame.draw.rect(self.screen, (180, 165, 110), (0, max(0, horizon_y), WIDTH, HEIGHT - max(0, horizon_y)))

        # 3. Square Minecraft Sun
        sun_x, sun_y, _ = self.project_3d(10, 18, 25)
        if sun_x:
            pygame.draw.rect(self.screen, (255, 255, 200), (sun_x - 35, sun_y - 35, 70, 70))

        # 4. Floating Pixel Clouds
        for c in self.clouds:
            cx, cy, _ = self.project_3d(c["x"], 8, c["z"])
            if cx:
                pygame.draw.rect(self.screen, (255, 255, 255), (cx - 40, cy - 10, int(c["w"] * 12), 20))

        # 5. Painter's Algorithm Depth-Sorting
        render_queue = []

        # Queue 3D Voxel Blocks
        for b in self.blocks:
            bx, by, bz = b["pos"]
            dist = (bx - self.px)**2 + (by - self.py)**2 + (bz - self.pz)**2
            render_queue.append(("block", dist, b))

        # Queue 3D Monster
        m_dist = (self.mx - self.px)**2 + (self.my - self.py)**2 + (self.mz - self.pz)**2
        render_queue.append(("monster", m_dist, None))

        # Queue 3D Particles
        for p in self.particles:
            p_dist = (p.x - self.px)**2 + (p.y - self.py)**2 + (p.z - self.pz)**2
            render_queue.append(("particle", p_dist, p))

        # Sort queue from Furthest to Closest
        render_queue.sort(key=lambda item: item[1], reverse=True)

        # Render Queued 3D Objects
        for item_type, _, data in render_queue:
            if item_type == "block":
                self.draw_3d_cube(data["pos"][0], data["pos"][1], data["pos"][2], data["type"])
            elif item_type == "particle":
                sx, sy, rz = self.project_3d(data.x, data.y, data.z)
                if sx and rz > 0.5:
                    sz = max(2, int(FOV / rz * data.size))
                    pygame.draw.rect(self.screen, data.color, (sx - sz//2, sy - sz//2, sz, sz))
            elif item_type == "monster":
                self.render_monster()

        # 6. 1st Person Weapon
        self.render_weapon()

        # 7. Minecraft HUD & Crosshair
        self.render_hud()

        pygame.display.flip()

    def render_monster(self):
        """Renders the 3D Billboard Sprite scaled to human/player proportions while maintaining aspect ratio."""
        sx, sy, rz = self.project_3d(self.mx, self.my, self.mz)
        if sx and rz > 0.5:
            # Match player height (1.8 units high; boss is 2.3 units high)
            world_height = 2.3 if self.round_num == 5 else 1.8
            h = max(10, int((world_height / rz) * FOV))

            if self.round_num in self.monster_sprites:
                img_orig = self.monster_sprites[self.round_num]
                # Dynamic width keeping original image aspect ratio
                aspect_ratio = img_orig.get_width() / img_orig.get_height()
                w = max(10, int(h * aspect_ratio))

                img = pygame.transform.scale(img_orig, (w, h))
                self.screen.blit(img, (sx - w // 2, sy - h // 2))
            else:
                # Procedural Blocky Fallback (Player-sized aspect ratio 1:2)
                w = max(10, int(h * 0.5))
                colors = [(200, 100, 40), (40, 40, 60), (220, 60, 60), (100, 200, 255), (160, 50, 160), (255, 30, 30)]
                m_color = colors[self.round_num] if not self.monster_stunned_timer else (100, 200, 255)
                
                # Blocky Body
                pygame.draw.rect(self.screen, m_color, (sx - w // 2, sy - h // 2, w, h))
                pygame.draw.rect(self.screen, (0, 0, 0), (sx - w // 2, sy - h // 2, w, h), 2)
                
                # Monster Eyes
                eye_sz = max(2, w // 5)
                pygame.draw.rect(self.screen, (255, 255, 0), (sx - eye_sz*1.5, sy - h // 4, eye_sz, eye_sz))
                pygame.draw.rect(self.screen, (255, 255, 0), (sx + eye_sz*0.5, sy - h // 4, eye_sz, eye_sz))

    def render_weapon(self):
        """Renders 1st-person pixelated Diamond Ladoo Sword with swinging physics."""
        w_x = WIDTH - 280
        w_y = HEIGHT - 240

        if self.weapon_texture:
            self.screen.blit(self.weapon_texture, (w_x, w_y))
        else:
            sword_surf = pygame.Surface((180, 180), pygame.SRCALPHA)
            pygame.draw.polygon(sword_surf, (80, 220, 220), [(90, 20), (160, 90), (140, 110), (70, 40)])
            pygame.draw.polygon(sword_surf, (40, 160, 160), [(90, 20), (160, 90), (150, 100), (80, 30)])
            pygame.draw.rect(sword_surf, (255, 215, 0), (60, 100, 30, 30))
            pygame.draw.rect(sword_surf, (102, 76, 40), (40, 120, 25, 25))
            pygame.draw.circle(sword_surf, (255, 170, 0), (75, 115), 12)

            rotated_sword = pygame.transform.rotate(sword_surf, self.swing_angle)
            self.screen.blit(rotated_sword, (w_x - int(self.swing_angle*1.5), w_y + int(self.swing_angle)))

    def render_hud(self):
        # 1. Crosshair
        pygame.draw.rect(self.screen, (255, 255, 255), (WIDTH // 2 - 6, HEIGHT // 2 - 6, 12, 12), 2)

        # 2. Boss / Enemy Health Bar
        cfg = MONSTER_CONFIG[self.round_num]
        txt_m_name = self.hud_font.render(f"{cfg['name']} (Round {self.round_num + 1}/6)", True, (255, 255, 255))
        self.screen.blit(txt_m_name, (WIDTH // 2 - txt_m_name.get_width() // 2, 12))

        bar_w = 400
        bar_x = WIDTH // 2 - bar_w // 2
        pygame.draw.rect(self.screen, (40, 40, 40), (bar_x, 32, bar_w, 16))
        hp_ratio = max(0.0, self.monster_hp / self.monster_max_hp)
        pygame.draw.rect(self.screen, (200, 40, 200) if self.round_num == 5 else (220, 40, 40), (bar_x, 32, int(bar_w * hp_ratio), 16))
        pygame.draw.rect(self.screen, (255, 255, 255), (bar_x, 32, bar_w, 16), 2)

        # 3. Minecraft Player Health (Hearts Bar)
        start_x = WIDTH // 2 - 180
        heart_y = HEIGHT - 80
        for i in range(10):
            x = start_x + i * 20
            pygame.draw.rect(self.screen, (0, 0, 0), (x, heart_y, 16, 16))
            if self.player_hp >= (i + 1) * 2:
                pygame.draw.rect(self.screen, (220, 20, 20), (x + 2, heart_y + 2, 12, 12))
            elif self.player_hp >= (i * 2) + 1:
                pygame.draw.rect(self.screen, (220, 20, 20), (x + 2, heart_y + 2, 6, 12))
            else:
                pygame.draw.rect(self.screen, (60, 60, 60), (x + 2, heart_y + 2, 12, 12))

        # 4. Minecraft Inventory Hotbar
        hotbar_w = 6 * 50 + 10
        hotbar_x = WIDTH // 2 - hotbar_w // 2
        hotbar_y = HEIGHT - 50

        pygame.draw.rect(self.screen, (100, 100, 100), (hotbar_x, hotbar_y, hotbar_w, 44))
        pygame.draw.rect(self.screen, (0, 0, 0), (hotbar_x, hotbar_y, hotbar_w, 44), 3)

        abilities = ["Ladoo", "Shield", "Burst", "Freeze", "Rage", "MAHA"]
        for i in range(6):
            bx = hotbar_x + 5 + i * 50
            unlocked = self.round_num >= i
            cd_keys = ["", "heal", "heavy", "stun", "buff", "ult"]
            cd = self.cooldowns.get(cd_keys[i], 0)

            cell_col = (180, 180, 180) if unlocked and cd == 0 else (60, 60, 60)
            pygame.draw.rect(self.screen, cell_col, (bx, hotbar_y + 4, 44, 36))
            pygame.draw.rect(self.screen, (255, 255, 255) if unlocked else (100, 100, 100), (bx, hotbar_y + 4, 44, 36), 2)

            txt_num = self.hud_font.render(str(i + 1), True, (255, 255, 0) if unlocked else (150, 150, 150))
            self.screen.blit(txt_num, (bx + 3, hotbar_y + 6))

            if unlocked:
                if cd > 0:
                    txt_cd = self.hud_font.render(f"{cd//60}s", True, (255, 50, 50))
                    self.screen.blit(txt_cd, (bx + 12, hotbar_y + 16))
                else:
                    txt_ab = self.hud_font.render(abilities[i][:4], True, (0, 0, 0))
                    self.screen.blit(txt_ab, (bx + 6, hotbar_y + 18))

        # 5. Combat Log Notification Banner
        if self.log_timer > 0:
            self.log_timer -= 1
            txt_log = self.font.render(self.combat_log, True, (255, 255, 255))
            self.screen.blit(txt_log, (WIDTH // 2 - txt_log.get_width() // 2, 70))

    # ==========================================
    # RUN GAME LOOP
    # ==========================================
    def run(self):
        running = True
        while running:
            running = self.handle_input()
            if self.player_hp <= 0:
                print("Game Over! You were defeated.")
                break
            self.update()
            self.render()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = LadooWarriorMinecraft()
    game.run()
