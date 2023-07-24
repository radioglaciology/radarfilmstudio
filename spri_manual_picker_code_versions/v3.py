"""
BUGS:
- windows are destroyed with ESC in the order that they appear in the code, not depending on which is active
- windows close on any keyboard press, not ESC

TODO:
- poly draw 
    - ctrl+z

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


class Image:
    """
    Contains an image and helpful methods for alternative displays of the image.
    """

    
    def __init__ (self, imgPath, cropVals, DEBUG = False):
        """
        Constructor. Creates the Image object with the given values.
        Params:
        - imgPath: the directory of the image to be read (string)
        - cropVals: tuple of pixel values for a vertical crop (y0, y1)
        """

        self.DEBUG = DEBUG # Debug switch for this object
        if self.DEBUG: print("Creating new image object with params: " + str(imgPath) + " , " + str(cropVals))

        self.imgPath = imgPath
        self.cropVals = cropVals
        self.img = cv2.imread(imgPath) # image is read in by cv2
        self.img = self.img[cropVals[0]:cropVals[1], ] # crops the image so only the section we care about is interpreted


    #KEEP IN MIND
    @staticmethod
    def blur(strength, image):
        """
        Creates a blurred version of the given image using the given blur strength value.
        - strength: value of the intensity of the blur (number)
        - image: the image to be blurred (read-in cv2 image, not path)
        """

        # if self.DEBUG: print("Calculating blur")
        print("Calculating blur")
        return cv2.bilateralFilter(image,5,strength,strength)
        # return cv2.GaussianBlur(image, (strength,strength), 0) #blur recalculation

        
    @staticmethod
    def edgeC(threshold, image):
        """
        Creates an edges version of the given image using the given blur strength value.
        - threshold: value of the intensity of the edge-detection (number)
        - image: the image to be edge-detected (read-in cv2 image, not path)
        """

        # if self.DEBUG: print("Calculating edges")
        print("Calculating edges")
        return cv2.Canny(image=image, threshold1=threshold, threshold2=threshold) # CannyEdge calculation
        
    #FIXME
    # #https://stackoverflow.com/questions/37099262/drawing-filled-polygon-using-mouse-events-in-open-cv-using-python
    # class PolygonDrawer():
    #     """
    #     Draws a polygonal object via mouse clicks on the window.
    #     """


    #     def __init__(self, window_name, colour,  DEBUG = False):
    #         """
    #         Constructor. Chooses which window will respond to the clicks and draw the points.
    #         - window_name: name of the window to be drawn in (string)
    #         """

    #         self.window_name = window_name # Name for our window
    #         self.colour = colour
    #         self.done = False # Flag signalling we're done
    #         self.current = (0, 0) # Current position, so we can draw the line-in-progress
    #         self.points = [] # List of points defining our polygon


    #     def on_mouse(self, event, x, y, buttons, user_param):
    #         """
    #         Mouse callback function that gets called for every mouse event (i.e. moving, clicking, etc.).
    #         Args are given by cv2.setMouseCallback (Args shouldn't be passed manually)
    #         - Captures mouse's location and clicks.
    #         - Saves the mouse's location on when clicked to self.points array/list
    #         - Method terminates on right-click.
    #         """

    #         if self.done: # Nothing more to do
    #             return

    #         if event == cv2.EVENT_MOUSEMOVE:
    #             # We want to be able to draw the line-in-progress, so update current mouse position
    #             self.current = (x, y)

    #         elif event == cv2.EVENT_LBUTTONDOWN:
    #             # Left click means adding a point at current position to the list of points
    #             if self.DEBUG: print("Adding point #%d with position(%d,%d)" % (len(self.points), x, y))

    #             self.points.append((x, y))

    #         elif event == cv2.EVENT_RBUTTONDOWN:
    #             # Right click means we're done
    #             if self.DEBUG: print("Completing polygon with %d points." % len(self.points))

    #             self.done = True


    #     # def on_keyboard(self, event, user_param):


    #     def run(self,window_name):
    #         # Let's create our working window and set a mouse callback to handle events
    #         cv2.waitKey(1)
    #         cv2.cv.SetMouseCallback(window_name, self.on_mouse)

    #         while(not self.done):
    #             # This is our drawing loop, we just continuously draw new images
    #             # and show them in the named window
    #             if (len(self.points) > 0):
    #                 # Draw all the current polygon segments
    #                 cv2.polylines(canvas, np.array([self.points]), False, FINAL_LINE_COLOR, 1)
    #                 # And  also show what the current segment would look like
    #                 cv2.line(canvas, self.points[-1], self.current, WORKING_LINE_COLOR)
    #             # Update the window
    #             cv2.imshow(self.window_name, canvas)
    #             # And wait 50ms before next iteration (this will pump window messages meanwhile)
    #             if cv2.waitKey(50) == 27: # ESC hit
    #                 self.done = True

    #         # User finised entering the polygon points, so let's make the final drawing
    #         canvas = np.zeros(CANVAS_SIZE, np.uint8)
    #         # of a filled polygon
    #         if (len(self.points) > 0):
    #             cv2.fillPoly(canvas, np.array([self.points]), FINAL_LINE_COLOR)
    #         # And show it
    #         cv2.imshow(self.window_name, canvas)
    #         # Waiting for the user to press any key
    #         cv2.waitKey()

    #         cv2.destroyWindow(self.window_name)
    #         return canvas



# ====================================



class Window:
    """
    Window object to show images on, a canvas of sorts.
    """

    def __init__(self, windowName, DEBUG = False):
        """
        Creates a resizable window.
        - windowName: the name of the window (string)
        """
        self.DEBUG = DEBUG # Debug switch for this object
        if self.DEBUG: print("Creating new window object with params: " + (windowName))

        self.windowName = windowName
        self.displayedImage = 0
        cv2.namedWindow(windowName, cv2.WINDOW_NORMAL) # Create window


   
    def refresh(self, image):
        """
        Shows the image on the window.
        - image: image to show on the window (read-in cv2 image, not path)
        """
        if self.DEBUG: print("Re-displaying image onto window " + self.windowName)

        self.displayedImage = image
        cv2.imshow(self.windowName, image) # (re)Display the image
        
        # while True: # closes the window if ESC is pressed
        #     k = cv2.waitKey(1) & 0xFF 
        #     if k == ESC: # close all windows when ESC is pressed
        #         break
        # cv2.destroyWindow(self.windowName)

        
    def addTrackbar(self, label, range, callback):
        """
        Creates a trackbar onto the window.
        - label: Label of the trackbar. (string)
        - range: start and end values of the trackbar. (tuple:(y0, y1))
        - callback: the function to be called everytime the trackbar is changed. (function)
        """
        if self.DEBUG: print("Creating trackbar " + label +" with range (" + str(range[0]) + " , " + str(range[1]) + ") on window " + self.windowName)

        cv2.createTrackbar(label, self.windowName, range[0], range[1], callback) # Creates trackbar


    def setTrackbar(self, name, val):
        """
        Sets the position of the trackbar.
        - name: the name/label of the trackbar. (string)
        - val: desired value to be set. (int)
        """
        cv2.setTrackbarPos(name, self.windowName, val)


    def closeOnESC(self):
        """
        Destroys the window when ESC is pressed.
        """

        if self.DEBUG: print("waiting for key input for " + self.windowName)
        cv2.waitKey(0)

        if self.DEBUG: print("Destroying window " + self.windowName)
        cv2.destroyWindow(self.windowName)
            
    

    def foo(self, a):
        """
        DEBUG METHOD, DO NOT USE
        """
        print(self.DEBUG, a)


    def blurOnChange(self, val, image, valB=0):
        """
        Helper method for blur trackbars.\n
        DO NOT USE WITHOUT A TRACKBAR.\n
        ONLY USE WITH A PARTIAL FUNCTION CALL.
        - val: blur strength value given by the trackbar.
        - image: image to be manipulated (not image path, not image object, read-in image. ie: image.img)
        - valB: value for re-calulating edges with the given blur
        """
        updated = Image.blur(val,image) # calculates the image with new blur values 
        self.refresh(updated) # displays the new image on the window
        
        #BUG
        # self.edgeOnChange(valB) # recalculates the edges with new blur values


    def edgeOnChange(self, val, image):
        """
        Helper method for edgeC trackbars.\n
        DO NOT USE WITHOUT A TRACKBAR.\n
        ONLY USE WITH A PARTIAL FUNCTION CALL.
        - val: edge threshold value given by the trackbar.
        """
        updated = Image.edgeC(val, image) # calculates the image with new threshold values
        self.refresh(updated) # redisplays the image 



# ====================================

# ====================================

def foo(a=0, b=0, c=0):
    print(a,b,c)


# running code
if __name__ == "__main__":


    imgPath = "C:/Users/LENOVO/Desktop/uni/summer 2022/EAS Research/code/BedPickerTest/flight_141_30_0006351_0006375-reel_begin_end_TIFF.tiff"
    
    image = Image(imgPath, (460, 1780), True)

    # creating windows
    winRef = Window("Reference", True)
    winEdge = Window("Edge", True)
    # winRef2 = Window("Reference2", True)


    # initial displaying images onto windows
    winRef.refresh(image.img)
    winEdge.refresh(image.edgeC(80, image.blur(50, image.img)))

    # trackbar setup
    # blur: 
    winRef.addTrackbar("Blur", (0, 100), partial(winRef.blurOnChange, image=image.img)) #creates blur trackbar on reference window
    winRef.setTrackbar("Blur", 10) # sets the trackbar's initial value to 10
    # edge:
    # winEdge.addTrackbar("Threshold", (0, 50), winEdge.edgeOnChange) # creates threshold trackbar on edge window
    winEdge.addTrackbar("Threshold", (0, 100), partial(winEdge.edgeOnChange, image=winRef.displayedImage)) # creates threshold trackbar on edge window
    winEdge.setTrackbar("Threshold", 10) # sets the trackbar's initial value to 10




    # BUG: required to make the windows not instantly close
    winRef.closeOnESC()
    winEdge.closeOnESC()
    # winRef2.closeOnESC()