import math
from pymunk import Vec2d
import json, time
import os

def getFileNames():
    # 获取当前工作目录
    current_directory = os.getcwd()

    # 获取当前目录下的所有文件和文件夹
    all_files_and_folders = os.listdir(current_directory)

    # 筛选出只有文件的项
    files_only = [file for file in all_files_and_folders if os.path.isfile(os.path.join(current_directory, file))]

    return files_only

def collide_circle(pos1, radius1, pos2, radius2):
    pos1 = Vec2d(pos1[0], pos1[1])
    pos2 = Vec2d(pos2[0], pos2[1])

    distance = pos1.get_distance(pos2)
    if distance < radius1 + radius2:
        return True
    else:
        return False
