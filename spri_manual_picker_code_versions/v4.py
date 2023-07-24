"""
Changes:
- Poly draw actually draws polygons:
    - lClick to add points
    - rClick to fill points
    - mash ESC to close the application

BUGS:
- poly draw 
    - undo does not erase. drawing creates irreversible damage

MINOR BUGS:
- windows are destroyed with ESC in the order that they appear in the code, not depending on which is active
- windows close on any keyboard press, not ESC
MINOR TODOS:
- find alternative to partial functions for trackbar callback function 
    - potential refactoring for the structure of the classes/methods
"""

import cv2
import numpy as np
from functools import partial


# Text-input modifer defintions to make code more readable
SHIFT = 16
CTRL = 17
ALT = 18
ESC = 27
CTRLZ = 26


class Image:
    """
    Contains an image and helpful methods for alternative displays of the image.
    """
    
    def __init__ (self, imgPath: str, cropVals: tuple, DEBUG: bool = False):
        """
        Constructor. Creates the Image object with the given values.
        Params:
        - `imgPath`: the directory of the image to be read (string)
        - `cropVals`: tuple of pixel values for a vertical crop (y0, y1)
        """

        self.DEBUG = DEBUG # Debug switch for this object
        if self.DEBUG: print("Creating new image object with params: " + str(imgPath) + " , " + str(cropVals))

        self.imgPath = imgPath
        self.cropVals = cropVals
        self.img = cv2.imread(imgPath) # image is read in by cv2
        self.img = self.img[cropVals[0]:cropVals[1], ] # crops the image so only the section we care about is interpreted


    @staticmethod
    def blur(strength: int, image):
        """
        Creates a blurred version of the given image using the given blur strength value.
        - `strength`: value of the intensity of the blur (number)
        - `image`: the image to be blurred (read-in cv2 image, not path)
        """

        # if self.DEBUG: print("Calculating blur")
        print("Calculating blur")
        return cv2.bilateralFilter(image,5,strength,strength)
        # return cv2.GaussianBlur(image, (strength,strength), 0) #blur recalculation

        
    @staticmethod
    def edgeC(threshold: int, image):
        """
        Creates an edges version of the given image using the given blur strength value.
        - `threshold`: value of the intensity of the edge-detection (number)
        - `image`: the image to be edge-detected (read-in cv2 image, not path)
        """

        # if self.DEBUG: print("Calculating edges")
        print("Calculating edges")
        return cv2.Canny(image=image, threshold1=threshold, threshold2=threshold) # CannyEdge calculation


# ====================================





class Window:
    """
    Window object to show images on, a canvas of sorts.
    """

    def __init__(self, windowName: str, DEBUG: bool = False, drawColour: tuple = (0, 0, 255)):
        """
        Creates a resizable window.
        - `windowName`: the name of the window (string)
        - `DEBUG`: enables console logs (bool)
        - `drawColour`: colour of polyDraw (3tuple: (B, G, R)) 
        """
        self.DEBUG = DEBUG # Debug switch for this object
        if self.DEBUG: print("Creating new window object with params: " + windowName + " " + str(drawColour))

        self.windowName = windowName
        self.displayedImage = 0
        cv2.namedWindow(windowName, cv2.WINDOW_NORMAL) # Create window
        
        self.polyDrawer = PolygonDrawer(self, drawColour, self.DEBUG) # creates polyDraw obj to select the edge region



   
    def refresh(self, image):
        """
        Shows the image on the window.
        - `image`: image to show on the window (read-in cv2 image, not path)
        """
        if self.DEBUG: print("Re-displaying image onto window " + self.windowName)

        self.displayedImage = image
        cv2.imshow(self.windowName, image) # (re)Display the image
        
        # while True: # closes the window if ESC is pressed
        #     k = cv2.waitKey(1) & 0xFF 
        #     if k == ESC: # close all windows when ESC is pressed
        #         break
        # cv2.destroyWindow(self.windowName)

        
    def addTrackbar(self, label: str, range: tuple, callback):
        """
        Creates a trackbar onto the window.
        - `label`: Label of the trackbar. (string)
        - `range`: start and end values of the trackbar. (tuple:(y0, y1))
        - `callback`: the function to be called everytime the trackbar is changed. (function)
        """
        if self.DEBUG: print("Creating trackbar " + label +" with range (" + str(range[0]) + " , " + str(range[1]) + ") on window " + self.windowName)

        cv2.createTrackbar(label, self.windowName, range[0], range[1], callback) # Creates trackbar


    def setTrackbar(self, name: str, val: int):
        """
        Sets the position of the trackbar.
        - `name`: the name/label of the trackbar. (string)
        - `val`: desired value to be set. (int)
        """
        cv2.setTrackbarPos(name, self.windowName, val)


    def closeOnESC(self):
        """
        Destroys the window when ESC is pressed.
        """

        # FIXME: does not close only on ESC
        if self.DEBUG: print("waiting for key input for " + self.windowName)
        cv2.waitKey(0)

        if self.DEBUG: print("Destroying window " + self.windowName)
        cv2.destroyWindow(self.windowName)
            
    
    def blurOnChange(self, val: int, image, valB=0):
        """
        Helper method for blur trackbars.\n
        DO NOT USE WITHOUT A TRACKBAR.\n
        ONLY USE WITH A PARTIAL FUNCTION CALL.
        - `val`: blur strength value given by the trackbar.
        - `image`: image to be manipulated (not image path, not image object, read-in image. ie: image.img)
        - `valB`: value for re-calulating edges with the given blur
        """
        updated = Image.blur(val,image) # calculates the image with new blur values 
        self.refresh(updated) # displays the new image on the window
        
        #BUG
        # self.edgeOnChange(valB) # recalculates the edges with new blur values


    def edgeOnChange(self, val: int, image):
        """
        Helper method for edgeC trackbars.\n
        DO NOT USE WITHOUT A TRACKBAR.\n
        ONLY USE WITH A PARTIAL FUNCTION CALL.
        - `val`: edge threshold value given by the trackbar.
        - `image`: image to be manipulated (not image path, not image object, read-in image. ie: image.img)
        """
        updated = Image.edgeC(val, image) # calculates the image with new threshold values
        self.refresh(updated) # redisplays the image 

# ====================================

#FIXME
#https://stackoverflow.com/questions/37099262/drawing-filled-polygon-using-mouse-events-in-open-cv-using-python
class PolygonDrawer():
    """
    Draws a polygonal object via mouse clicks on the window.
    """


    def __init__(self, window: Window, colour: tuple, DEBUG = False):
        """
        Constructor. Chooses which window will respond to the clicks and draw the points.
        - `window`: the window to be drawn in (window obj)
        """
        self.DEBUG = DEBUG
        if self.DEBUG: print("Creating polyDrawer for window " + window.windowName)

        self.window = window
        self.colour = colour # BGR colour
        self.done = False # Flag signalling we're done
        self.position = (0, 0) # Current position, so we can draw the line-in-progress
        self.points = [] # List of points defining our polygon


        cv2.setMouseCallback(self.window.windowName, self.on_mouse) # makes cv2 listen to mouse inputs



    def on_mouse(self, event, x, y, buttons, user_param):
        """
        Mouse callback function that gets called for every mouse event (i.e. moving, clicking, etc.).
        Args are given by cv2.setMouseCallback (Args shouldn't be passed manually)
        - Captures mouse's location and clicks.
        - Saves the mouse's location on when clicked to self.points array/list
        - Method terminates on right-click.
        """

        if self.done: # Nothing more to do
            return
        
        if event == cv2.EVENT_MOUSEMOVE: # on MOUSE:MOVE, save the new position 
            # We want to be able to draw the line-in-progress, so update current mouse position
            self.position = (x, y)

        elif event == cv2.EVENT_LBUTTONDOWN: # on MOUSE:L CLICK, create a new point
            # Left click means adding a point at current position to the list of points
            if self.DEBUG: print("Adding point #%d with position(%d,%d)" % (len(self.points), x, y))

            self.points.append((x, y)) # adds the mouse location to the points list
            cv2.polylines(self.window.displayedImage, np.array([self.points]), False, self.colour, 3) # create the temp-poly 
            self.window.refresh(self.window.displayedImage)# display the new temp-poly


        elif event == cv2.EVENT_RBUTTONDOWN: # on MOUSE:R CLICK, complete/close the polygon
            # Right click means we're done
            if self.DEBUG: print("Completing polygon with %d points." % len(self.points))
            cv2.fillPoly(self.window.displayedImage, np.array([self.points]), self.colour)
            self.window.refresh(self.window.displayedImage)# display the new temp-poly
            self.done = True

    def undoPoint(self):
        """
        Pops the last point in `self.points` if CTRL+Z is pressed.
        - `input`: the key-press of the keyboard
        """
        while True:
            input = cv2.waitKey(0)
            if self.DEBUG & input != -1: print("Key pressed: " + str(input))
            
            if input ==  CTRLZ:
                removed = self.points.pop()
                if self.DEBUG: print("Removed point: " + str(removed))
            
            elif input == ESC | self.done:
                if self.DEBUG: print("Undo disabled")
                break

# ====================================


# running code
if __name__ == "__main__":

    imgPath = "C:/Users/LENOVO/Desktop/uni/summer 2022/EAS Research/code/BedPickerTest/flight_141_30_0006351_0006375-reel_begin_end_TIFF.tiff"
    
    image = Image(imgPath, (460, 1780), True)

    # creating windows
    winRef = Window("Reference", True)
    winEdge = Window("Edge", True)


    # initial displaying images onto windows
    winRef.refresh(image.img)
    winEdge.refresh(image.edgeC(80, image.blur(50, image.img)))

    # trackbar setup
    # blur: 
    winRef.addTrackbar("Blur", (0, 100), partial(winRef.blurOnChange, image=image.img)) #creates blur trackbar on reference window
    winRef.setTrackbar("Blur", 100) # sets the trackbar's initial value 
    # edge:
    # winEdge.addTrackbar("Threshold", (0, 50), winEdge.edgeOnChange) # creates threshold trackbar on edge window
    winEdge.addTrackbar("Threshold", (0, 100), partial(winEdge.edgeOnChange, image=winRef.displayedImage)) # creates threshold trackbar on edge window
    winEdge.setTrackbar("Threshold", 65) # sets the trackbar's initial value 

    winRef.polyDrawer.undoPoint()




    # BUG: required to make the windows not instantly close
    winRef.closeOnESC()
    winEdge.closeOnESC()