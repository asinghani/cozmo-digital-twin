#!/usr/bin/env python3
"""
    This file is the main ARENA app which takes data coming in from cozmo-tools over HTTP requests
    and sends it on to ARENA, and also makes any incoming events from ARENA available to cozmo-tools
    in a polling manner. The reason for the use of HTTP requests and this multi-process system (as
    opposed to directly connecting to ARENA from the cozmo program) is primarily for flexibility;
    this system allows the cozmo library to be swapped out or even run on a different computer from
    the ARENA program without interruptions. Furthermore, it improves the startup time of the cozmo
    program because connecting to ARENA can be slightly slow.

    Tested and working with arenaxr.org platform as of 04/28/2022 (ARENA-core e57f42d).
"""

from flask import Flask
import math, time, threading
from arena import *

# Reduce verbosity of Flask built-in logging
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

"""
    Configuration parameters
    Most of these should probably not need to change
"""
COZMO_GLB = "store/users/asinghan/cozmo.glb"
COZMO_SCALE = 0.01 # relative to GLB file

ORIGIN_GLB = "store/public/origin.glb"
ORIGIN_SCALE = 0.03 # relative to GLB file

CUBE_COLOR = (255, 0, 0) # RGB
CUBE_DIM = 0.045 # meters

APRILTAG_SIZE = 50 # mm
APRILTAG_HEIGHT = 0.07 # meters

ARENA_HOST = "arenaxr.org"
ARENA_SCENE = "cozmo-new"

HTTP_PORT = 8000

scene = Scene(host=ARENA_HOST, scene=ARENA_SCENE)

"""
    Main dictionary of objects maintained on this end of the system
    x (meters), y (meters), theta (degrees), visible (boolean)
"""
objects = {"cozmo": (0, 0, 0, False), "cube1": (0, 0, 0, False),
           "cube2": (0, 0, 0, False), "cube3": (0, 0, 0, False)}

arena_objects = {}

"""
    Recieve updated location of an object
"""
@app.route("/update_obj/<obj>/<x>,<y>,<theta>,<visible>")
def update_obj(obj, x, y, theta, visible):
    global objects

    if obj not in objects:
        print("Unknown object", obj)
        return "ERROR_UNKNOWN_OBJECT"

    objects[obj] = (float(x), float(y), float(theta), int(visible))
    print(objects[obj])

    return "OK"

"""
    Set up the 3D objects in ARENA with placeholder positions
"""
@scene.run_once
def arena_init():
    global arena_objects

    # Create the origin apriltag for the cozmo "world"
    origin = GLTF(
        object_id="origin",
        url=ORIGIN_GLB,
        position=(0, APRILTAG_HEIGHT, 0),
        scale=(ORIGIN_SCALE, ORIGIN_SCALE, ORIGIN_SCALE),
        rotation=(-90, 0, 0),
        persist=True
    )
    origin.data["armarker"] = {
        "markerid": "1",
        "markertype": "apriltag_36h11",
        "size": 50,
        "buildable": False,
        "dynamic": False
    }
    scene.add_object(origin)


    # Create cozmo and the cubes
    arena_objects["cozmo"] = GLTF(
        object_id="cozmo",
        url="store/users/asinghan/cozmo.glb",
        position=(999, 999, 999),
        rotation=(90, 180, 90),
        scale=(.01, .01, .01),
        persist=True
    )
    scene.add_object(arena_objects["cozmo"])

    for cube in ("cube1", "cube2", "cube3"):
        arena_objects[cube] = Box(
            object_id=cube,
            position=(999, 999, 999),
            scale=(CUBE_DIM, CUBE_DIM, CUBE_DIM),
            persist=True,
            color=CUBE_COLOR
        )
        scene.add_object(arena_objects[cube])

"""
    Invoked in a loop once ARENA is connected, pushes updates to ARENA objects
"""
@scene.run_forever(interval_ms=100)
def arena_update():
    global objects, arena_objects

    for obj in objects:
        x, y, theta, visible = objects[obj]

        # Really big coordinates ~ invisible (in ARENA at least)
        if not visible:
            x, y = 999, 999

        arena_objects[obj].data.position.x = y
        arena_objects[obj].data.position.z = x
        arena_objects[obj].data.position.y = 0

        if obj == "cozmo":
            arena_objects[obj].data.rotation = Rotation(90, 180, theta+90)
        else:
            arena_objects[obj].data.rotation = Rotation(0, theta, 0)

        scene.update_object(arena_objects[obj])

if __name__ == "__main__":
    # Start the HTTP server thread and the ARENA asyncio loop
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=HTTP_PORT)).start()
    scene.run_tasks()

