import cv2
import numpy as np
from cozmo_fsm import *
import os

os.system("mkdir -p images")

class calibrate(StateMachineProgram):
    def __init__(self):
        super().__init__(aruco=False, particle_filter=False, cam_viewer=True,
                         annotate_sdk=False)

        self.last = time.time()
        self.index = 0

    def start(self):
        dummy = numpy.array([[0]], dtype='uint8')
        super().start()

    def user_image(self, image, gray):
        print(image.shape)
        #cv2.imshow("image", image)
        #cv2.waitKey(1)
        if time.time() - self.last > 1:
            print("Image!")
            self.last = time.time()
            cv2.imwrite(f"images/image{self.index}.png", image)
            self.index += 1
