import asyncio
import websockets
import time
import pygame
import math
import json
from pymunk import Vec2d

pygame.init()

# 设置窗口和物理空间
width, height = 800, 600

name = input("Name?")
weaponType = int(input("Weapon Type? (1: Machine Gun, 2: Rifle, 3: Sniper)"))

screen = pygame.display.set_mode((width, height), pygame.SRCALPHA | pygame.RESIZABLE)

# 主循环
running = True
game_speed = 1
fps = 60

gunType2name = {1: "machineGun", 2: "rifle", 3: "sniper", 4: "grenade"}


class Resources:
    def __init__(self):
        self.image = {}
        self.ratio = (4, 1)
        self.base = 25

    def add_image(self, path, name=None, ratio=(1, 1), base=0):
        if name == None:
            name = path

        if ratio == 0:
            ratio = self.ratio
        if base == 0:
            base = self.base

        size = (ratio[0] * base, ratio[1] * base)

        image_path = f"image/{path}.png"
        loaded_image = pygame.image.load(image_path).convert_alpha()

        loaded_image = pygame.transform.scale(loaded_image, size)
        loaded_image.set_colorkey((255, 255, 255))

        self.image[name] = loaded_image

    def get_image(self, name):
        return self.image[name]


RES = Resources()
RES.add_image("machineGun", ratio=(4, 2), base=10)
RES.add_image("rifle", ratio=(4, 1), base=10)
RES.add_image("sniper", ratio=(6, 1), base=15)
RES.add_image("grenade", ratio=(1, 1))

bullets = []
Players = {}

angle = 0


class TextBliter:
    def __init__(self, screen, color: pygame.Color):
        self.screen = screen
        self.color = color

    def blit(self, string, position, size=30):
        textFont = pygame.font.Font(None, size)
        textRender = textFont.render(string, True, self.color)
        textRect = textRender.get_rect()
        textRect.center = position
        self.screen.blit(textRender, textRect)


class ImageBliter:
    def __init__(self, screen):
        self.screen = screen

    def blit(self, image, position):
        Rect = image.get_rect()
        Rect.center = position
        self.screen.blit(image, Rect)


textBliter = TextBliter(screen, pygame.Color(0, 0, 0))
imageBliter = ImageBliter(screen)


def CreateMap(map_info):
    global map_image

    # 创建地图碰撞体
    for element in map_info["circle"]:
        element: list

        position: tuple = element[0]
        radius: int = element[1]

        pygame.draw.circle(map_image, (255, 0, 0), center=position, radius=radius)
    for element in map_info["poly"]:

        vertices: list = element
        pygame.draw.polygon(map_image, (255, 0, 0), vertices)


async def main():
    global server, angle, running, map_image
    uri = f"ws://v1an.xyz:11001"
    server = await websockets.connect(uri)

    data: str = await server.recv()
    print(data)
    data: dict = json.loads(data)

    if data['type'] == 'map':
        map_info = data['map']
        map_width, map_height = map_info["size"]

        map_image = pygame.Surface(size=map_info["size"])
        map_image.fill((255, 255, 255))
        CreateMap(map_info)

        barriers = [[(0, map_height), (map_width, map_height)], [(0, 0), (map_width, 0)], [(0, 0), (0, map_height)],
                    [(map_width, 0), (map_width, map_height)]]

    message = {"type": "join", "name": name, "weaponType": weaponType}
    await server.send(json.dumps(message))

    key_w, key_a, key_s, key_d, key_r, key_f, key_m1, key_1, key_2, key_3, key_4 = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    angle = 0
    move_angle = 0
    Players = {}
    Player_weapons = {}

    while running:
        data: str = await server.recv()
        print(data)
        data: dict = json.loads(data)

        if data['type'] == 'info':
            Players: dict = data['players']
            bullets: list = data['bullets']
            grenades: list = data['grenades']
        elif data['type'] == 'weaponList':
            print(data)
            Player_weapons = data['players']

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                key_m1 = 1
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                key_m1 = 0

        keys = pygame.key.get_pressed()

        if keys[pygame.K_w]:
            key_w = 1
        else:
            key_w = 0
        if keys[pygame.K_a]:
            key_a = 1
        else:
            key_a = 0
        if keys[pygame.K_s]:
            key_s = 1
        else:
            key_s = 0
        if keys[pygame.K_d]:
            key_d = 1
        else:
            key_d = 0
        if keys[pygame.K_r]:
            key_r = 1
        else:
            key_r = 0
        if keys[pygame.K_f]:
            key_f = 1
        else:
            key_f = 0
        if keys[pygame.K_1]:
            key_1 = 1
        else:
            key_1 = 0
        if keys[pygame.K_2]:
            key_2 = 1
        else:
            key_2 = 0
        if keys[pygame.K_3]:
            key_3 = 1
        else:
            key_3 = 0
        if keys[pygame.K_4]:
            key_4 = 1
        else:
            key_4 = 0

        if key_d:
            move_angle = 0
            if key_w:
                move_angle = -45
            elif key_s:
                move_angle = 45

        if key_a:
            move_angle = 180
            if key_w:
                move_angle = 225
            elif key_s:
                move_angle = 135

        if key_w and not key_a and not key_d:
            move_angle = -90

        if key_s and not key_a and not key_d:
            move_angle = 90

        try:

            width, height = pygame.display.get_surface().get_size()

            a = (width // 2, height // 2)
            b = Players[name][0]

            cameraOffset = (a[0] - b[0], a[1] - b[1])

            x, y = b
            direction = pygame.mouse.get_pos() - Vec2d(x, y) - cameraOffset
            angle_h = math.atan2(direction.y, direction.x)
            angle = math.degrees(angle_h)
            print(angle, angle_h)

            # 清屏
            screen.fill((255, 255, 255))

            # 绘制地图

            screen.blit(map_image, cameraOffset)
            # 边界
            for i in barriers:
                c = (i[0][0] + cameraOffset[0], i[0][1] + cameraOffset[1])
                d = (i[1][0] + cameraOffset[0], i[1][1] + cameraOffset[1])
                pygame.draw.line(screen, (255, 0, 0), c, d)

            # 玩家
            for currentPlayer in Players.values():
                position = currentPlayer[0]
                hp = currentPlayer[1]
                bulletNow, bulletLeft, gunType, reloadCD = currentPlayer[2:6]

                position_offset = (position[0] + cameraOffset[0], position[1] + cameraOffset[1])
                pygame.draw.circle(screen, (0, 0, 255), position_offset, 20)

                hp_offset = (position_offset[0], position_offset[1] - 30)
                ammo_offset = (position_offset[0], position_offset[1] + 30)
                textBliter.blit(str(hp), hp_offset)
                if reloadCD == 0:
                    textBliter.blit(f"{bulletNow}/{bulletLeft}", ammo_offset, size=20)
                else:
                    reloadSecond = reloadCD / fps
                    textBliter.blit("%.1f s" % reloadSecond, ammo_offset, size=20)

                gun_name = gunType2name[gunType]
                gun_image = RES.get_image(gun_name)
                gun_offset = (position_offset[0], position_offset[1] + 50)
                imageBliter.blit(gun_image, gun_offset)

            # 绘制子弹
            for x, y, radius in bullets:
                position_offset = (x + cameraOffset[0], y + cameraOffset[1])
                pygame.draw.circle(screen, (0, 255, 0), position_offset, radius)

            # 绘制投掷物
            for x, y, radius, damage_radius in grenades:
                center_offset = (x + cameraOffset[0], y + cameraOffset[1])
                damage_offset = (x + cameraOffset[0] - damage_radius, y + cameraOffset[1] - damage_radius)

                # 范围
                circle_surface = pygame.Surface((damage_radius * 2, damage_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(circle_surface, (255, 0, 0, 100), circle_surface.get_rect().center, damage_radius)

                screen.blit(circle_surface, damage_offset)

                # 中心点
                grenade_image = RES.get_image("grenade")
                imageBliter.blit(grenade_image,center_offset)

            pygame.display.flip()
        except Exception as e:
            print(e)

        message = f"{key_w}{key_a}{key_s}{key_d}{key_r}{key_f}{key_m1}{key_1}{key_2}{key_3}{key_4} {int(angle)} {int(move_angle)}"
        print(message)
        await server.send(message)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
