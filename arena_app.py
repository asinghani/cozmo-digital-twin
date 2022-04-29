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
from scipy.spatial.transform import Rotation as R

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

ARUCO_MARKER_HEIGHT = 0.035 # meters
ARUCO_MARKERS = [(0, 0.035), (0.1, 0.035), (0.25, 0.2), (0.25, 0.3)]
ARUCO_COLOR = (0, 170, 170) # small circle in center of marker

ARENA_HOST = "arenaxr.org"
ARENA_SCENE = "cozmo-new"

# Whether to use the user's camera to place destination markers
USE_RAYCAST = True

# Used for immersive mode; system scale doesn't match world scale
WORLD_SCALE = 1.0

HTTP_PORT = 8000

scene = Scene(host=ARENA_HOST, scene=ARENA_SCENE)

"""
    Main dictionary of objects maintained on this end of the system
    x (meters), y (meters), theta (degrees), visible (boolean)
"""
objects = {"cozmo": (0, 0, 0, False), "cube1": (0, 0, 0, False),
           "cube2": (0, 0, 0, False), "cube3": (0, 0, 0, False)}

arena_objects = {}

waypoint = None

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

    return "OK"

"""
    Get the latest waypoint (if one exists)
"""
@app.route("/get_waypoint")
def get_waypoint():
    if waypoint:
        return f"{waypoint[0]},{waypoint[1]}"
    else:
        return "NONE"

"""
    Acknowledge that the robot finished navigation
"""
@app.route("/reset_waypoint")
def reset_waypoint():
    global waypoint
    waypoint = None
    return "OK"

"""
    Handler for incoming messages from ARENA
"""
def on_message(scene, evt, msg):
    oid = msg.get("object_id")
    if USE_RAYCAST:
        if not oid.startswith("camera"): return
        # Get the position and orientation of the user's head
        pos = msg["data"]["position"]
        rot = msg["data"]["rotation"]
        rot = R.from_quat([rot["x"], rot["y"], rot["z"], rot["w"]])

        # Compute a raycast from the user's head to the ground plane
        vec = rot.apply([0, 0, -1])
        res = (0 - pos["y"]) / vec[1]
        x = pos["x"] + res*vec[0]
        z = pos["z"] + res*vec[2]

        if waypoint is None:
            # Move the pushpin so it feels like the user is controlling it by moving their head
            arena_objects["pushpin"].data.position = Position(x, 0, z)
            arena_objects["pushpin"].data.color = Color(0, 180, 0)
            scene.update_object(arena_objects["pushpin"])
    else:
        if not oid.startswith("handRight"): return

        if waypoint is None:
            pos = msg["data"]["position"]

            # Edge case when the hand is moving in and out of the frame
            if pos["x"] == 0 and pos["z"] == 0:
                return

            # If the object was put into the ground
            if pos["y"] < 0.4:
                arena_objects["pushpin"].data.position = Position(pos["x"], 0.4, pos["z"])
                scene.update_object(arena_objects["pushpin"])
                set_nav_pos()
            else:
                arena_objects["pushpin"].data.position = Position(pos["x"], pos["y"] - 0.2, pos["z"])
                arena_objects["pushpin"].data.color = Color(0, 180, 0)
                scene.update_object(arena_objects["pushpin"])


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
        position=(0, APRILTAG_HEIGHT*WORLD_SCALE, 0),
        scale=(ORIGIN_SCALE*WORLD_SCALE,)*3,
        rotation=(-90, 0, 0),
        persist=True
    )

    if WORLD_SCALE == 1:
        origin.data["armarker"] = {
            "markerid": "1",
            "markertype": "apriltag_36h11",
            "size": 50,
            "buildable": False,
            "dynamic": False
        }

    scene.add_object(origin)

    # Add a small marker on each AruCo marker
    for i in range(len(ARUCO_MARKERS)):
        x, z = ARUCO_MARKERS[i]
        y = ARUCO_MARKER_HEIGHT
        color = ARUCO_COLOR

        sphere = Sphere(
            object_id=f"aruco{i}",
            position=(x*WORLD_SCALE, y*WORLD_SCALE, z*WORLD_SCALE),
            scale=(0.005*WORLD_SCALE,)*3,
            rotation=(0, 0, 0),
            color=color,
            persist=True
        )

        scene.add_object(sphere)

    # Create cozmo and the cubes
    arena_objects["cozmo"] = GLTF(
        object_id="cozmo",
        url=COZMO_GLB,
        position=(999, 999, 999),
        rotation=(90, 180, 90),
        scale=(.01*WORLD_SCALE,) * 3,
        persist=True
    )
    scene.add_object(arena_objects["cozmo"])

    for cube in ("cube1", "cube2", "cube3"):
        arena_objects[cube] = Box(
            object_id=cube,
            position=(999, 999, 999),
            scale=(CUBE_DIM*WORLD_SCALE,) * 3,
            persist=True,
            color=CUBE_COLOR
        )
        scene.add_object(arena_objects[cube])

    if USE_RAYCAST:
        # Create the pushpin object as a thin flat disk which acts like a "navigation target"
        arena_objects["pushpin"] = Cylinder(
            object_id="pushpin",
            position=(999, 999, 999),
            rotation=(0, 0, 0),
            scale=(.023, .005, .023),
            color=(0, 120, 0),
            persist=True,
            clickable=True,
            evt_handler=click_handler
        )
        scene.add_object(arena_objects["pushpin"])
    else:
        # Create the pushpin object as a "stake" which can be placed into the ground
        arena_objects["pushpin"] = Cylinder(
            object_id="pushpin",
            position=(999, 999, 999),
            rotation=(0, 0, 0),
            scale=(.015, .8, .015),
            color=(0, 120, 0),
            persist=True,
            clickable=True,
            evt_handler=click_handler
        )
        scene.add_object(arena_objects["pushpin"])

    scene.on_msg_callback = on_message

"""
    Event handler for when the pushpin is clicked
"""
def click_handler(scene, evt, msg):
    if evt.type == "mousedown":
        set_nav_pos()

"""
    Send a new waypoint based on the pushpin position
"""
def set_nav_pos():
    global waypoint
    if waypoint is None:
        pos = arena_objects["pushpin"].data.position
        waypoint = (pos["z"] / WORLD_SCALE, pos["x"] / WORLD_SCALE)
        print("Navigating to", waypoint)
        arena_objects["pushpin"].data.color = Color(240, 10, 0)
        scene.update_object(arena_objects["pushpin"])

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

        arena_objects[obj].data.position.x = y * WORLD_SCALE
        arena_objects[obj].data.position.z = x * WORLD_SCALE
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

