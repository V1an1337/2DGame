import math
import pymunk
from typing import Union

flag_jiting = 0


class Player:
    body: pymunk.Body
    hp: int
    name: str
    angle: int  # degree
    move_angle: int  # degree
    side: str
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

    filter: pymunk.ShapeFilter

    radius: int
    mass: int
    moment: float
    body: pymunk.Body
    shape: pymunk.Circle

    space: pymunk.space

    weapon: any
    weaponList: list

    state_angle: int
    state_move_angle: int
    action_move: bool
    action_chooseWeapon: int
    action_reload: bool
    action_fire: bool

    def __init__(self):
        self.state_angle = 0
        self.state_move_angle = 0
        self.action_reload = False
        self.action_fire = False
        self.action_move = False
        self.action_chooseWeapon = -1

    def checkChoice(self, weaponType):
        if 1 <= weaponType <= len(self.weaponList):
            return True
        return False

    def chooseWeapon(self, weaponType):
        self.action_chooseWeapon = weaponType

    def position(self) -> tuple:
        return self.body.position.int_tuple

    def checkReload(self):
        return self.weapon.bulletLeft > 0 and self.weapon.bulletNow < self.weapon.bulletConstant and not self.reloading

    def reload(self):
        self.action_reload = True

    def fire(self):
        self.action_fire = True


def move(p, angle):
    p.action_move = True
    p.state_move_angle = angle


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


def update(currentPlayer: Player, Players, Bullets, Grenades):
    global flag_jiting

    # 移动
    if currentPlayer.key_a or currentPlayer.key_w or currentPlayer.key_s or currentPlayer.key_d:
        move_angle = currentPlayer.move_angle
        move(currentPlayer, move_angle)

    if not currentPlayer.changingGun:
        # 开火
        if currentPlayer.key_m1:
            if not currentPlayer.reloading:
                if currentPlayer.weapon.shot_cd == 0 and currentPlayer.weapon.bulletNow > 0:
                    currentPlayer.fire()

        # 主动换弹
        if currentPlayer.key_r:
            if currentPlayer.checkReload():
                currentPlayer.reload()

    # 切枪
    if currentPlayer.key_1 or currentPlayer.key_2 or currentPlayer.key_3 or currentPlayer.key_4:
        if currentPlayer.key_1:
            choice = 1
        elif currentPlayer.key_2:
            choice = 2
        elif currentPlayer.key_3:
            choice = 3
        elif currentPlayer.key_4:
            choice = 4
        else:
            choice = 0

        if choice != currentPlayer.weapon_choice:
            currentPlayer.chooseWeapon(choice)

    #print(currentPlayer.move_angle, currentPlayer.action_move, flag_jiting)
    return currentPlayer
