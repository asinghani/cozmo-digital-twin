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

@app.route("/data/<ax>,<ay>,<atheta>")
def dir(ax, ay, atheta):
    global x, y, theta
    x, y, theta = float(ax)/1000, float(ay)/1000, float(atheta)
    print(x, y, theta)
    return ""

scene = Scene(host="arenaxr.org", scene="cozmo-scene")

@scene.run_once
def arena_init():
    global cozmo

    cozmo = Box(
        object_id="cozmo",
        position=(0, 0, 0),
        scale=(0.02, 0.01, 0.01),
        persist=True,
        color=(0, 150, 0)
    )
    scene.add_object(cozmo)

@scene.run_forever(interval_ms=100)
def arena_update():
    global cozmo, x, y, theta

    cozmo.data.position.x = y
    cozmo.data.position.z = x
    cozmo.data.position.y = -0.01
    cozmo.data.rotation = Rotation(0, theta, 0)
    print("cozmo", cozmo.data.position)
    scene.update_object(cozmo)

def init_flask():
    app.run(host = "0.0.0.0", port=8000)

if __name__ == "__main__":
    threading.Thread(target=init_flask).start()
    scene.run_tasks()

