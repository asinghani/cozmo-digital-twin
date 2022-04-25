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
z = 0

@app.route("/data/<a>,<b>,<c>")
def dir(a, b, c):
    global x, y, z
    x, y, z = float(a)/1000, float(b)/1000, float(c)/1000
    print(x, y, z)
    return ""

scene = Scene(host="arenaxr.org", scene="cozmo-kine")

@scene.run_once
def arena_init():
    global cozmo2

    cozmo2 = Box(
        object_id="m_box",
        position=(0, 0, 0),
        scale=(0.003, 0.003, 0.003),
        persist=True,
        color=(0, 150, 0)
    )
    scene.add_object(cozmo2)

@scene.run_forever(interval_ms=100)
def arena_update():
    global cozmo2, x, y, z

    cozmo2.data.position.x = x
    cozmo2.data.position.z = y
    cozmo2.data.position.y = z

    scene.update_object(cozmo2)

def init_flask():
    app.run(host = "0.0.0.0", port=8000)

if __name__ == "__main__":
    threading.Thread(target=init_flask).start()
    scene.run_tasks()

