import pygame
import pymunk
import websockets
import asyncio
import json
import time
import copy
import random
from Engine import *
from typing import Union
import logging
import default

pygame.init()

log_name = f'{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}.log'
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
logging.basicConfig(filename=log_name,encoding='utf-8', level=logging.INFO, format=LOG_FORMAT, datefmt=DATE_FORMAT)

logging.info("logger init success")

gunType2name = {1: "machineGun", 2: "rifle", 3: "sniper", 4: "grenade"}

class Player:
    lib: any

    body: pymunk.Body
    hp: int
    name: str
    angle: int
    move_angle: int
    reloading: bool
    grenade: bool
    changeGun_CD: int
    changingGun: bool
    weapon_choice: int
    move_speed: float

    key_w: bool
    key_a: bool
    key_s: bool
    key_d: bool
    key_r: bool
    key_f: bool
    key_m1: bool
    key_1: bool
    key_2: bool
    key_3: bool
    key_4: bool

    radius: int
    mass: int
    moment: float
    body: pymunk.Body
    shape: pymunk.Circle

    space: pymunk.space

    weapon: any
    weaponList: list

    def __init__(self, name='v1an', weaponType=0):
        self.sandbox = None
        self.lib = default

        self.key_w = False
        self.key_a = False
        self.key_s = False
        self.key_d = False
        self.key_r = False
        self.key_f = False
        self.key_m1 = False
        self.key_1 = False
        self.key_2 = False
        self.key_3 = False
        self.key_4 = False

        self.angle = 0
        self.move_angle = 0
        self.hp = 100
        self.name = name
        self.reloading = False
        self.grenade = True
        self.changeGun_CD = 0
        self.changingGun = False
        self.weapon_choice = 1
        self.move_speed = 0

        self.filter = NewCollisionHandle()
        self.space = space

        # 创建角色
        self.radius = 20
        self.mass = 1
        self.moment = pymunk.moment_for_circle(self.mass, 0, self.radius)
        self.body = pymunk.Body(self.mass, self.moment)
        self.body.position = random.choice(spawnpoints)
        self.shape = pymunk.Circle(self.body, self.radius)
        self.shape.elasticity = 0.1
        self.shape.filter = self.filter

        self.space.add(self.body, self.shape)

        self.weaponList = [Weapon_machineGun(self), Weapon_rifle(self), Weapon_sniper(self), Grenade_grenade(self)]
        self.chooseWeapon(weaponType)

    def checkChoice(self, weaponType):
        if 1 <= weaponType <= len(self.weaponList):
            return True
        return False

    def chooseWeapon(self, weaponType):
        if self.checkChoice(weaponType):
            self.weapon = self.weaponList[weaponType - 1]
            self.weapon_choice = weaponType
            logging.info(f'Player {self.name} choose weapon: {weaponType} -> {self.weapon}')
        else:
            logging.warning(f'Player {self.name} choose weapon: {weaponType}, Unavailable weapon!')

    def position(self) -> tuple:
        return self.body.position.int_tuple

    def kill(self):
        self.reborn()

    def checkReload(self):
        return self.weapon.bulletLeft > 0 and self.weapon.bulletNow < self.weapon.bulletConstant and not self.reloading

    def reload(self):
        self.reloading = True
        self.weapon.reload_cd = self.weapon.reload_constant

    def reborn(self):
        self.reloading = False
        self.weaponList = [Weapon_machineGun(self), Weapon_rifle(self), Weapon_sniper(self), Grenade_grenade(self)]

        self.hp = 100
        self.body.position = random.choice(spawnpoints)
        self.chooseWeapon(self.weapon_choice)
        self.grenade = True


class Player_Sandbox:
    state_angle: int
    state_move_angle: int
    action_move: bool
    action_chooseWeapon: int
    action_reload: bool
    action_fire: bool

    def __init__(self, p: Player):
        self.update(p)

    def update(self, p: Player):
        self.body = p.body
        self.hp = p.hp
        self.name = p.name
        self.angle = p.angle
        self.move_angle = p.move_angle
        self.reloading = p.reloading
        self.grenade = p.grenade
        self.changeGun_CD = p.changeGun_CD
        self.changingGun = p.changingGun
        self.weapon_choice = p.weapon_choice
        self.move_speed = p.move_speed

        self.key_w = p.key_w
        self.key_a = p.key_a
        self.key_s = p.key_s
        self.key_d = p.key_d
        self.key_r = p.key_r
        self.key_f = p.key_f
        self.key_m1 = p.key_m1
        self.key_1 = p.key_1
        self.key_2 = p.key_2
        self.key_3 = p.key_3
        self.key_4 = p.key_4

        self.radius = p.radius
        self.mass = p.mass
        self.moment = p.moment
        self.space = copy.deepcopy(p.space)

        if p.weapon.type == 4:
            self.weapon = Grenade_Sandbox(p.weapon)
        else:
            self.weapon = Weapon_Sandbox(p.weapon)
        #self.weaponList = [Weapon_Sandbox(self, w) for w in p.weaponList]

        self.reset()

    def reset(self):
        self.state_angle = 0
        self.state_move_angle = 0
        self.action_move = False
        self.action_reload = False
        self.action_fire = False
        self.action_chooseWeapon = -1

    def position(self) -> tuple:
        return self.body.position.int_tuple

    def checkReload(self):
        return self.weapon.bulletLeft > 0 and self.weapon.bulletNow < self.weapon.bulletConstant and not self.reloading

    def chooseWeapon(self, weaponType):
        self.action_chooseWeapon = weaponType

    def reload(self):
        self.action_reload = True

    def fire(self):
        self.action_fire = True

    def move(self, angle):
        self.state_move_angle = angle


class Bullet:
    dead: bool
    by: str
    player: Player
    bullet_radius: int
    bullet_radius_collision: int
    bullet_mass: float
    bullet_speed: float
    bullet_body: pymunk.Body
    bullet_shape: pymunk.Circle

    def __init__(self, player: Player, bullet_radius: int, bullet_radius_collision: int, bullet_speed: int):
        global bullets
        self.dead = False

        self.by = player.name
        self.player = player
        player_body = player.body
        player_angle = player.angle

        self.bullet_radius = bullet_radius
        self.bullet_radius_collision = bullet_radius_collision

        self.bullet_mass = 0.1
        self.bullet_speed = bullet_speed * game_speed / space_tick

        self.bullet_body = pymunk.Body(self.bullet_mass,
                                       pymunk.moment_for_circle(self.bullet_mass, 0, self.bullet_radius))  # 使用合适的质量和惯性值
        self.bullet_body.position = player_body.position
        self.bullet_shape = pymunk.Circle(self.bullet_body, self.bullet_radius)

        spread_min, spread_max = self.player.weapon.spreadRange
        offset: int = self.player.weapon.spreadOffset
        spread_rate: float = self.player.body.velocity.length / move_speed_constant
        angle = player_angle

        if spread_rate < spread_min:
            angle = angle
        elif spread_min < spread_rate < spread_max:
            angle += random.randint(-offset, offset) * ((spread_rate - spread_min) / (spread_max - spread_min))
        else:
            angle += random.randint(-offset, offset)

        self.bullet_body.velocity = (self.bullet_speed * math.cos(math.radians(angle)),
                                     self.bullet_speed * math.sin(math.radians(angle)))

        self.fire()

    def fire(self):
        bullets.append(self)

    def position(self):
        return self.bullet_body.position.int_tuple


class Bullet_Sandbox:
    def __init__(self,b: Bullet):
        p_sandbox = b.player.sandbox
        self.dead = b.dead
        self.by = b.by
        self.player = p_sandbox
        self.bullet_radius = b.bullet_radius
        self.bullet_radius_collision = b.bullet_radius_collision
        self.bullet_mass = b.bullet_mass
        self.bullet_speed = b.bullet_speed
        self.bullet_body = copy.deepcopy(b.bullet_body)
        self.bullet_shape = copy.deepcopy(b.bullet_shape)

    def position(self):
        return self.bullet_body.position.int_tuple


def SortBulletByX(bullet: Bullet):
    return bullet.position()[0]


class Bullet_machineGun(Bullet):
    def __init__(self, player: Player):
        self.bullet_radius = 7
        self.bullet_radius_collision = 5
        self.bullet_speed = 1400
        Bullet.__init__(self, player, self.bullet_radius, self.bullet_radius_collision, self.bullet_speed)


class Bullet_rifle(Bullet):
    def __init__(self, player: Player):
        self.bullet_radius = 10
        self.bullet_radius_collision = 5
        self.bullet_speed = 1500
        Bullet.__init__(self, player, self.bullet_radius, self.bullet_radius_collision, self.bullet_speed)


class Bullet_sniper(Bullet):
    def __init__(self, player: Player):
        self.bullet_radius = 15
        self.bullet_radius_collision = 7
        self.bullet_speed = 1600
        Bullet.__init__(self, player, self.bullet_radius, self.bullet_radius_collision, self.bullet_speed)


class Weapon_Gun:
    shot_cd: int
    shot_cd_constant: int
    reload_cd: int  # tick
    reload_constant: int  # tick
    bulletNow: int
    bulletConstant: int
    bulletLeft: int
    player: Player
    bulletType: Bullet
    damage: int
    type: int
    changeGun_CD: int
    changeGun_CD_constant: int  # tick
    spreadRange: tuple
    spreadOffset: int

    def __init__(self, player: Player, bulletType: Union[Bullet_sniper, Bullet_rifle, Bullet_machineGun],
                 shot_cd_constant: int, bulletNow: int, bulletLeft: int, damage: int, gunType: int,
                 changeGun_CD_constant: int, reload_constant: int, spreadRange: tuple, spreadOffset: int):
        self.shot_cd = 0
        self.shot_cd_constant = shot_cd_constant  # tick
        self.reload_constant = reload_constant  # (second * tick): tick
        self.reload_cd = 0
        self.bulletNow = bulletNow
        self.bulletConstant = self.bulletNow
        self.bulletLeft = bulletLeft
        self.player = player
        self.bulletType = bulletType
        self.damage = damage
        self.type = gunType
        self.changeGun_CD = 0
        self.changeGun_CD_constant = changeGun_CD_constant  # tick
        self.spreadRange = spreadRange
        self.spreadOffset = spreadOffset

    def fire(self):
        self.shot_cd = self.shot_cd_constant
        self.bulletNow -= 1
        self.bulletType(self.player)


class Weapon_Sandbox:
    def __init__(self, w: Weapon_Gun):
        p_sandbox = w.player.sandbox
        self.shot_cd = w.shot_cd
        self.shot_cd_constant = w.shot_cd_constant
        self.reload_cd = w.reload_cd
        self.reload_constant = w.reload_constant
        self.bulletNow = w.bulletNow
        self.bulletConstant = w.bulletConstant
        self.bulletLeft = w.bulletLeft
        self.player = p_sandbox
        self.bulletType = w.bulletType
        self.damage = w.damage
        self.type = w.type
        self.changeGun_CD = w.changeGun_CD
        self.changeGun_CD_constant = w.changeGun_CD_constant
        self.spreadRange = w.spreadRange
        self.spreadOffset = w.spreadOffset


class Weapon_machineGun(Weapon_Gun):
    def __init__(self, player: Player):
        self.shot_cd_constant = int(1/10 * fps)
        self.bulletNow = 30
        self.bulletLeft = 180
        # self.bulletLeft = 9999
        self.damage = 10
        self.gunType = 1
        self.changeGun_CD_constant = int(0.5 * fps)
        self.reload_constant = int(1.5 * fps)
        self.spreadRange = (0.8, 0.9)
        self.spreadOffset = 10
        Weapon_Gun.__init__(self, player, Bullet_machineGun, self.shot_cd_constant, self.bulletNow, self.bulletLeft,
                            self.damage, self.gunType, self.changeGun_CD_constant, self.reload_constant,
                            self.spreadRange, self.spreadOffset)


class Weapon_rifle(Weapon_Gun):
    def __init__(self, player: Player):
        self.shot_cd_constant = int(1/8*fps)
        self.bulletNow = 15
        self.bulletLeft = 90
        # self.bulletLeft = 9999
        self.damage = 20
        self.gunType = 2
        self.changeGun_CD_constant = int(0.5 * fps)
        self.reload_constant = int(2 * fps)
        self.spreadRange = (0.5, 0.7)
        self.spreadOffset = 20
        Weapon_Gun.__init__(self, player, Bullet_rifle, self.shot_cd_constant, self.bulletNow, self.bulletLeft,
                            self.damage, self.gunType, self.changeGun_CD_constant, self.reload_constant,
                            self.spreadRange, self.spreadOffset)


class Weapon_sniper(Weapon_Gun):
    def __init__(self, player: Player):
        self.shot_cd_constant = int(1 * fps)
        self.bulletNow = 3
        self.bulletLeft = 18
        # self.bulletLeft = 9999
        self.damage = 100
        self.gunType = 3
        self.changeGun_CD_constant = int(1 * fps)
        self.reload_constant = int(2 * fps)
        self.spreadRange = (0.4, 0.6)
        self.spreadOffset = 30
        Weapon_Gun.__init__(self, player, Bullet_sniper, self.shot_cd_constant, self.bulletNow, self.bulletLeft,
                            self.damage, self.gunType, self.changeGun_CD_constant, self.reload_constant,
                            self.spreadRange, self.spreadOffset)


class Grenade:
    dead: bool
    shot_cd: int
    bulletNow: int
    bulletLeft: int
    reload_cd: int
    type: int
    changeGun_CD: int
    changeGun_CD_constant: int
    by: str
    player: Player
    grenade_radius: int
    grenade_mass: float
    grenade_speed: float

    grenade_body: pymunk.Body
    grenade_shape: pymunk.Circle

    def __init__(self, player: Player, grenade_radius: int, grenade_speed: int, gunType: int):
        global bullets
        self.dead = False
        self.shot_cd = 0
        self.bulletNow = 1
        self.bulletLeft = 0
        self.reload_cd = 0
        self.type = gunType
        self.changeGun_CD = 0
        self.changeGun_CD_constant = int(0.5 * fps)

        self.by = player.name
        self.player = player

        self.grenade_radius = grenade_radius
        self.grenade_mass = 0.1
        self.grenade_speed = grenade_speed * game_speed / space_tick

        self.grenade_body = pymunk.Body(self.grenade_mass,
                                        pymunk.moment_for_circle(self.grenade_mass, 0,
                                                                 self.grenade_radius))  # 使用合适的质量和惯性值

        self.grenade_shape = pymunk.Circle(self.grenade_body, self.grenade_radius)
        self.grenade_shape.filter = self.player.filter
        self.grenade_shape.elasticity = 1

    def fire(self):
        global space

        self.grenade_body.position = self.player.body.position
        self.grenade_body.velocity = (self.grenade_speed * math.cos(math.radians(self.player.angle)),
                                      self.grenade_speed * math.sin(math.radians(self.player.angle)))
        self.grenade_body.velocity += self.player.body.velocity

        self.bulletNow = 0
        self.player.chooseWeapon(1)
        self.player.changeGun_CD = self.player.weapon.changeGun_CD_constant
        self.player.changingGun = True
        self.player.weaponList.remove(self)
        space.add(self.grenade_body, self.grenade_shape)
        grenades.append(self)

    def update(self):
        pass

    def position(self):
        return self.grenade_body.position.int_tuple


class Grenade_Sandbox:
    def __init__(self,g: Grenade):
        p_sandbox = g.player.sandbox
        self.dead = g.dead
        self.shot_cd = g.shot_cd
        self.bulletNow = g.bulletNow
        self.bulletLeft = g.bulletLeft
        self.reload_cd = g.reload_cd
        self.type = g.type
        self.changeGun_CD = g.changeGun_CD
        self.changeGun_CD_constant = g.changeGun_CD_constant
        self.by = g.by
        self.player = p_sandbox
        self.grenade_radius = g.grenade_radius
        self.grenade_mass = g.grenade_mass
        self.grenade_speed = g.grenade_speed

        self.grenade_body = g.grenade_body
        self.grenade_shape = g.grenade_shape

    def position(self):
        return self.grenade_body.position.int_tuple


class Grenade_grenade(Grenade):
    def __init__(self, player: Player):
        self.grenade_radius = 5
        self.grenade_speed = 1000
        self.gunType = 4
        Grenade.__init__(self, player, self.grenade_radius, self.grenade_speed, self.gunType)

        self.cd = 1.5 * fps * space_tick
        self.damage = 50
        self.damage_radius = 300

    def update(self):
        if self.cd > 0:
            self.cd -= 1
        else:
            self.explode()

    def explode(self):
        global Players, space
        for currentPlayer in Players.values():
            currentPlayer: Player

            if collide_circle(self.position(), self.damage_radius, currentPlayer.position(),
                              currentPlayer.radius):
                damage = self.damage

                if currentPlayer.hp - damage > 0:
                    currentPlayer.hp -= damage
                else:
                    currentPlayer.kill()

        self.dead = True
        space.remove(self.grenade_body, self.grenade_shape)


with open('map.txt', 'r', encoding='utf-8') as f:
    map_info = f.read()

map_info: dict = json.loads(map_info)
map_width, map_height = map_info["size"]

# 设置窗口和物理空间
width, height = map_width, map_height

space = pymunk.Space()
space.gravity = (0, 0)  # 将重力设置为0
map_elasticity = 0.5

# 创建边界
barriers = [[(0, height), (width, height)], [(0, 0), (width, 0)], [(0, 0), (0, height)], [(width, 0), (width, height)]]
for i in barriers:
    ground = pymunk.Segment(space.static_body, i[0], i[1], 0.0)
    ground.filter = pymunk.ShapeFilter(group=1)  # map filter = 1
    ground.elasticity = map_elasticity
    space.add(ground)

game_speed = 1
fps = 60
space_tick = 5
tickcount = 0

move_speed_constant = 300 * game_speed / space_tick
move_speed_increase_rate = 10
ground_friction_rate = 0.15

bullets = []
bullets_message = []
bullets_sandbox = []

grenades = []
grenades_message = []
grenades_sandbox = []

connected_clients = {}
Players = {}
Players_sandbox = {}

timecostTotal = 0

# 1 for map
collision_handle_index = 2

map_image = pygame.Surface(size=(map_width, map_height))
map_image.fill((255, 255, 255))


def CreateMap():
    global map_image, map_info, spawnpoints

    spawnpoints = map_info["spawnpoint"]

    # 创建地图碰撞体
    for element in map_info["circle"]:

        element: list

        # 创建一个静态的圆形 Body
        position: tuple = element[0]
        radius: int = element[1]

        moment = pymunk.moment_for_circle(mass=1, inner_radius=0, outer_radius=radius)
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        body.position = position  # 设置圆心位置
        shape = pymunk.Circle(body, radius)
        shape.elasticity = map_elasticity
        space.add(body, shape)

        pygame.draw.circle(map_image, (0, 0, 0), center=position, radius=radius)
    for element in map_info["poly"]:

        # 定义多边形的顶点坐标
        vertices: list = element

        # 创建多边形的Body
        body = pymunk.Body(body_type=pymunk.Body.STATIC)
        # 创建多边形形状
        polygon = pymunk.Poly(body, vertices)
        polygon.elasticity = map_elasticity
        # 添加多边形到空间
        space.add(body, polygon)
        pygame.draw.polygon(map_image, (0, 0, 0), polygon.get_vertices())

    logging.info("Create Map Success")


def NewCollisionHandle():
    global collision_handle_index, space

    index = collision_handle_index
    handler = space.add_collision_handler(index, index)
    handler.pre_solve = lambda: False

    collision_handle_index += 1

    return pymunk.ShapeFilter(group=collision_handle_index - 1)


async def broadcast_message(message):
    for client in connected_clients.values():
        asyncio.create_task(client.send(message))


async def handle_client(websocket, path):
    global connected_clients, Players
    addr = websocket.remote_address
    connected_clients[addr] = websocket

    message = {"type": "map", "map": map_info}
    await websocket.send(json.dumps(message))

    try:
        data: str = await websocket.recv()
        data: dict = json.loads(data)

        if data['type'] == 'join':
            name = data['name']
            weaponType = data['weaponType']
            Players[name] = Player(name, weaponType)
            Players[name].sandbox = Player_Sandbox(Players[name])

            if f"{name}.py" in getFileNames():
                exec(f"import {name} as playerLib_{name}")
                exec(f"Players[name].lib = playerLib_{name}")
                logging.info(f"Got name {name}, import as playerLib_{name}")
            else:
                logging.info(f"No file named {name}.py, using default")

        currentPlayer: Player = Players[name]
    except Exception as e:
        logging.warning(f"ERROR occur when joining: {e}")

    try:
        while True:
            data: str = await websocket.recv()
            data: list = data.split(' ')

            keys = []
            for i in data[0]:
                if i == "1":
                    keys.append(True)
                elif i == "0":
                    keys.append(False)
            currentPlayer.key_w, currentPlayer.key_a, currentPlayer.key_s, currentPlayer.key_d, \
            currentPlayer.key_r, currentPlayer.key_f, currentPlayer.key_m1, \
            currentPlayer.key_1, currentPlayer.key_2, currentPlayer.key_3, currentPlayer.key_4 = keys

            currentPlayer.angle = int(data[1])
            currentPlayer.move_angle = int(data[2])


    except websockets.exceptions.ConnectionClosedError:
        # 处理连接关闭异常
        logging.info(f"Connection closed for {addr}")
        if addr in connected_clients:
            del connected_clients[addr]
        if name in Players:
            del Players[name]

    except Exception as e:
        logging.warning(f"ERROR occur when processing data, reason: {e}")
        if addr in connected_clients:
            del connected_clients[addr]
        if name in Players:
            del Players[name]


async def main():
    # 同时运行WebSocket服务器和Judge函数
    server = await websockets.serve(handle_client, "0.0.0.0", 11001)

    judge_task = asyncio.create_task(Judge())

    # 等待服务器关闭和Judge函数完成
    await asyncio.gather(server.wait_closed(), judge_task)


async def Judge():
    global tickcount, bullets, Players, bullets_message, grenades_message, grenades, Players_sandbox, bullets_sandbox, grenades_sandbox

    CreateMap()

    # 主循环
    running = True

    while running:

        s = time.time()
        tickcount += 1

        for currentPlayer in Players.values():
            currentPlayer: Player

            if currentPlayer.sandbox == None:
                currentPlayer.sandbox = Player_Sandbox(currentPlayer)

            currentPlayer_sandbox = currentPlayer.sandbox
            currentPlayer_sandbox.update(currentPlayer)

            Players_sandbox = {player.name: player.sandbox for player in Players.values()}

            currentPlayer_sandbox = currentPlayer.lib.update(currentPlayer_sandbox, Players_sandbox, Bullet_Sandbox,
                                                   Grenade_Sandbox)

            if tickcount % (10 * fps) == 0 and len(currentPlayer.weaponList) < 4:
                currentPlayer.weaponList.append(Grenade_grenade(currentPlayer))

            if not currentPlayer.changingGun:
                # 开火
                if currentPlayer_sandbox.action_fire:
                    if not currentPlayer.reloading:
                        if currentPlayer.weapon.shot_cd == 0 and currentPlayer.weapon.bulletNow > 0:
                            currentPlayer.weapon.fire()

                # 主动换弹
                if currentPlayer_sandbox.action_reload:
                    if currentPlayer.checkReload():
                        currentPlayer.reload()

                # 处理换弹过程
                if currentPlayer.reloading:
                    if currentPlayer.weapon.reload_cd > 0:
                        currentPlayer.weapon.reload_cd -= 1
                    else:
                        # 换弹完成
                        currentPlayer.weapon.reload_cd = 0
                        currentPlayer.reloading = False
                        changeBullet: int = min(currentPlayer.weapon.bulletLeft,
                                                currentPlayer.weapon.bulletConstant - currentPlayer.weapon.bulletNow)
                        currentPlayer.weapon.bulletNow += changeBullet
                        currentPlayer.weapon.bulletLeft -= changeBullet

            # 切枪
            if currentPlayer_sandbox.action_chooseWeapon != -1:
                choice = currentPlayer_sandbox.action_chooseWeapon

                if choice != currentPlayer.weapon_choice and currentPlayer.checkChoice(choice):
                    if currentPlayer.reloading:
                        currentPlayer.weapon.reload_cd = 0
                        currentPlayer.reloading = False

                    currentPlayer.chooseWeapon(choice)
                    currentPlayer.changeGun_CD = currentPlayer.weapon.changeGun_CD_constant
                    currentPlayer.changingGun = True

            # 处理切枪过程
            if currentPlayer.changingGun:
                if currentPlayer.changeGun_CD > 0:
                    currentPlayer.changeGun_CD -= 1
                else:
                    # 切枪完成
                    currentPlayer.changeGun_CD = 0
                    currentPlayer.changingGun = False

            # 处理开火间隔
            if currentPlayer.weapon.shot_cd > 0:
                currentPlayer.weapon.shot_cd -= 1

            # 移动加速度
            if currentPlayer_sandbox.action_move:
                radius = move_speed_constant
                angle_r = math.radians(currentPlayer_sandbox.state_move_angle)
                x_velocity = math.cos(angle_r) * radius
                y_velocity = math.sin(angle_r) * radius
                force = Vec2d(x_velocity, y_velocity) * move_speed_increase_rate
                currentPlayer.body.apply_force_at_world_point(force,
                                                              currentPlayer.body.position)

            currentPlayer.body.velocity -= currentPlayer.body.velocity * ground_friction_rate

            if currentPlayer.body.velocity.length > move_speed_constant:
                currentPlayer.body.velocity *= move_speed_constant / currentPlayer.body.velocity.length

        # 更新物理空间
        for i in range(space_tick):  # 看似客户端的gap很大，其实每个gap之间都有space_tick次判定，精度很高
            dt = 1.0 / fps
            space.step(dt)

            # 更新子弹
            new_bullets = []
            new_bullets_message = []
            new_bullets_sandbox = []

            bullets.sort(key=SortBulletByX)
            # print(bullets)
            index = -1
            for bullet in bullets:
                bullet: Bullet
                index += 1

                if bullet.dead:
                    continue

                bullet_body = bullet.bullet_body
                bullet_shape = bullet.bullet_shape

                # 子弹移动
                bullet_body.position += bullet_body.velocity * (1.0 / fps)

                # 玩家碰撞
                collide_player = []
                for currentPlayer in Players.values():
                    currentPlayer: Player

                    # 自己发射的子弹不判定
                    if currentPlayer.name == bullet.by:
                        continue

                    if collide_circle(bullet_body.position, bullet.bullet_radius, currentPlayer.position(),
                                      currentPlayer.radius):
                        collide_player.append(currentPlayer)

                if collide_player:
                    # print(collide_player)
                    for currentPlayer in collide_player:
                        currentPlayer: Player
                        by = bullet.by
                        damage = Players[by].weapon.damage
                        if currentPlayer.hp - damage > 0:
                            currentPlayer.hp -= damage
                        else:
                            currentPlayer.kill()
                    continue

                # 子弹对撞
                left_index = index
                right_index = index

                while left_index - 1 >= 0:
                    left_index -= 1
                    # print(left_index)
                    other_bullet = bullets[left_index]
                    if other_bullet.dead:
                        continue
                    if other_bullet.by == bullet.by:
                        continue

                    my_radius = bullet.bullet_radius_collision
                    my_position = bullet.position()

                    other_body = other_bullet.bullet_body
                    other_radius = other_bullet.bullet_radius_collision
                    other_position = other_body.position

                    if abs(other_position.x - my_position[0]) > other_radius + my_radius:
                        break

                    if collide_circle(my_position, my_radius, other_position,
                                      other_radius):
                        bullet.dead = True
                        other_bullet.dead = True

                while right_index + 1 < len(bullets):
                    right_index += 1
                    # print(right_index)
                    other_bullet = bullets[right_index]
                    if other_bullet.dead:
                        continue
                    if other_bullet.by == bullet.by:
                        continue

                    my_radius = bullet.bullet_radius_collision
                    my_position = bullet.position()

                    other_body = other_bullet.bullet_body
                    other_radius = other_bullet.bullet_radius_collision
                    other_position = other_body.position

                    if abs(other_position.x - my_position[0]) > other_radius + my_radius:
                        break

                    if collide_circle(my_position, my_radius, other_position,
                                      other_radius):
                        bullet.dead = True
                        other_bullet.dead = True

                if bullet.dead:
                    continue

                # 边缘碰撞
                if not 0 < bullet_body.position.x < width or not 0 < bullet_body.position.y < height:
                    # 子弹到达边缘消失
                    continue

                # 地图碰撞
                if map_image.get_at((int(bullet_body.position.x), int(bullet_body.position.y))) != (255, 255, 255, 255):
                    # 子弹碰到障碍物时消失
                    continue

                # 不消失，添加回去
                new_bullets.append(bullet)
                x, y = bullet_body.position.int_tuple
                new_bullets_message.append([x, y, bullet.bullet_radius])
                new_bullets_sandbox.append(Bullet_Sandbox(bullet))

            bullets = new_bullets
            bullets_message = new_bullets_message
            bullets_sandbox = new_bullets_sandbox

            new_grenades = []
            new_grenades_message = []
            new_grenades_sandbox = []

            for grenade in grenades:
                grenade: Grenade_grenade
                grenade.update()

                if grenade.dead:
                    continue

                x, y = grenade.position()
                new_grenades.append(grenade)
                new_grenades_message.append([x, y, grenade.grenade_radius, grenade.damage_radius])
                new_grenades_sandbox.append(Grenade_Sandbox(grenade))

            grenades = new_grenades
            grenades_message = new_grenades_message
            grenades_sandbox = new_grenades_sandbox

        players_message = {
            currentPlayer.name:
                [currentPlayer.position(), currentPlayer.hp,
                 currentPlayer.weapon.bulletNow, currentPlayer.weapon.bulletLeft, currentPlayer.weapon.gunType,
                 max(currentPlayer.weapon.reload_cd, currentPlayer.changeGun_CD)]

            for currentPlayer in Players.values()}

        message = {"type": "info",
                   "players": players_message,
                   "bullets": bullets_message,
                   "grenades": grenades_message}
        # print(message)
        await broadcast_message(json.dumps(message))

        if tickcount % 8 == 0:
            players_message = {}
            for currentPlayer in Players.values():
                players_message[currentPlayer.name] = [weapon.gunType for weapon in currentPlayer.weaponList]

            message = {"type": "weaponList",
                       "players": players_message}
            await broadcast_message(json.dumps(message))

        timecost = time.time() - s
        print(f"timecost:{timecost}")
        timesleep = 1 / fps - (time.time() - s)

        if timesleep <= 0:
            logging.error(f"ERROR: timesleep = {timesleep}")
            pass
        else:
            print(f"timesleep: {timesleep}")
            await asyncio.sleep(timesleep)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
