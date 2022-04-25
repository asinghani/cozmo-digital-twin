#!/usr/bin/env python3

from flask import Flask
from subprocess import call
import math
import time
import threading
from arena import *
import threading

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

x = 0
y = 0
theta = 0

cube_x = 0
cube_y = 0
cube_theta = 0

@app.route("/data/<ax>,<ay>,<atheta>,<cx>,<cy>,<ctheta>")
def dir(ax, ay, atheta, cx, cy, ctheta):
    global x, y, theta, cube_x, cube_y, cube_theta
    x, y, theta = float(ax)/1000, float(ay)/1000, float(atheta)
    cube_x, cube_y, cube_theta = float(cx)/1000, float(cy)/1000, float(ctheta)
    print(x, y, theta, cube_x, cube_y, cube_theta)
    return ""

scene = Scene(host="arenaxr.org", scene="cozmo-scene")

@scene.run_once
def arena_init():
    global cozmo, cozmo2, cube1

    cozmo2 = Box(
        object_id="cozmo2",
        position=(0, 0, 0),
        scale=(0.02, 0.01, 0.01),
        persist=True,
        color=(0, 150, 0)
    )
    cozmo = GLTF(
        object_id="cozmo",
        url="store/users/asinghan/cozmo.glb",
        position=(0, 0, 0),
        rotation=(90, 180, 90),
        scale=(.01, .01, .01),
        persist=True
    )
    scene.add_object(cozmo)
    scene.add_object(cozmo2)

    cube1 = Box(
        object_id="cube1",
        position=(0, 0, 0),
        scale=(0.045, 0.045, 0.045),
        persist=True,
        color=(120, 120, 0)
    )
    scene.add_object(cube1)

@scene.run_forever(interval_ms=100)
def arena_update():
    global cozmo, cozmo2, x, y, theta, cube_x, cube_y, cube_theta

    cozmo.data.position.x = y
    cozmo.data.position.z = x
    cozmo.data.position.y = -0.08
    cozmo.data.rotation = Rotation(90, 180, theta+90)

    cozmo2.data.position.x = y
    cozmo2.data.position.z = x
    cozmo2.data.position.y = -0.01
    cozmo2.data.rotation = Rotation(0, theta, 0)

    cube1.data.position.x = cube_y
    cube1.data.position.z = cube_x
    cube1.data.position.y = -0.0475
    cube1.data.rotation = Rotation(0, cube_theta, 0)


    print("cozmo", cozmo.data.position)
    scene.update_object(cozmo)
    scene.update_object(cozmo2)
    scene.update_object(cube1)

def init_flask():
    app.run(host = "0.0.0.0", port=8000)

if __name__ == "__main__":
    threading.Thread(target=init_flask).start()
    scene.run_tasks()

