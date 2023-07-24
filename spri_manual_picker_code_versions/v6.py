"""
Changes:
-polyDraw:
    - right-clicking after selecting an area calculates a line of the average points of those regions, specifed by the DETAIL value in the `main` class

BUGS:
- tweaking sliders after right-clicking may remove the selection area

TODO:
- multistep linear regression for surface/bed line generation
- implement multi-poly drawing
    - trackbar switch for surface/bed


MINOR BUGS:
- weird amount of ESC presses to close the program 
- windows are destroyed with ESC in the order that they appear in the code, not depending on which is active
- windows close on any keyboard press, not ESC
MINOR TODOS:
- find alternative to partial functions for trackbar callback function 
    - potential refactoring for the structure of the classes/methods
"""

from copy import deepcopy
import cv2
from cv2 import pointPolygonTest
import numpy as np
from functools import partial # needed to make trackbar callbacks work


# Text-input defintions to make code more readable
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
        - `DEBUG`: enables console logs (bool)
        """

        self.DEBUG = DEBUG # Debug switch for this object
        if self.DEBUG: print("Creating new image object with params: " + str(imgPath) + " , " + str(cropVals))

        self.imgPath = imgPath # where on the computer the source image is stored
        self.cropVals = cropVals # tuple of pixel values for a vertical crop (y0, y1)
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

    @staticmethod
    def mask(image1: cv2.Mat, image2: cv2.Mat):
        """
        Covers `image1` with black pixels, except for the area(s) spanned by `image2`.
        - `image1`: source image
        - `image2`: mask shape
        """
        print("Calculating mask")
        return cv2.bitwise_and(image1, image2) # compute the mask with the given shape: fill everything with black except the provided shape
        



# ====================================





class Window:
    """
    Window object to show images on, a canvas of sorts.
    """

    def __init__(self, windowName: str, image: cv2.Mat = None, drawable=False, detail=10, drawColourSurface: tuple = (0, 0, 255), drawColourBed: tuple = (0, 255, 0),DEBUG: bool = False):
        """
        Creates a resizable window.
        - `windowName`: the name of the window (string)
        - `drawColourSurface`: colour of surfave polyDraw (3tuple: (B, G, R)) (Default = RED)
        - `drawColourBed`: colour of bed polyDraw (3tuple: (B, G, R)) (Default = GREEN)
        - `DEBUG`: enables console logs (bool)
        """
        self.DEBUG = DEBUG # Debug switch for this object
        if self.DEBUG: print("Creating new window object with params: " + windowName + " " + str(drawColourSurface) + " " + str(drawColourBed)) 

        self.windowName = windowName

        self.sourceImage = image # copy of the un-altered image
        self.displayedImage = 0 # the image that is displayed on the window, which may include lines, polys, overlays etc

        cv2.namedWindow(windowName, cv2.WINDOW_NORMAL) # Create window

        
        if drawable: # creates the necessary drawing components 
            self.polyDrawerSurface = PolygonDrawer(self, drawColourSurface,DEBUG= self.DEBUG) # creates polyDraw obj to select the edge region
            self.polyDrawerBed = PolygonDrawer(self, drawColourBed, DEBUG= self.DEBUG) # creates polyDraw obj to select the edge region
            self.drawDone = True
            self.detail = detail

            



    def surfaceBedSwitch (self, switch):
        """
        Determines whether to draw the surface or bed,
        based on the trackbar values (0, 1), (surface, bed) respectively.
        """
        if switch == 0: # enables drawing and undos for the surface
            if self.DEBUG: print("Drawing surface")
            
            self.polyDrawerSurface.done = False
            self.polyDrawerBed.done = True
            
            self.polyDrawerSurface.undoPoint()

        else:  # enables drawing and undos for the bed
            if self.DEBUG: print("Drawing bed")

            self.polyDrawerSurface.done = True
            self.polyDrawerBed.done = False

            self.polyDrawerBed.undoPoint()


            
   
    def refresh(self, image: cv2.Mat):
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

    @staticmethod
    def closeOnESC():
        """
        Destroys the window when ESC is pressed.
        """

        # FIXME: does not close only on ESC; any button works
        cv2.waitKey(0)
        cv2.destroyAllWindows()
            
    
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

#https://stackoverflow.com/questions/37099262/drawing-filled-polygon-using-mouse-events-in-open-cv-using-python
class PolygonDrawer():
    """
    Draws a polygonal object via mouse clicks on the window.
    """


    def __init__(self, window: Window, colour: tuple,  DEBUG = False):
        """
        Constructor. Chooses which window will respond to the clicks and draw the points.
        - `window`: the window to be drawn in (window obj)
        - `colour`: colour of the lines/fill (3tuple (B,G,R))
        - `extraParams`: additional parameters to be considered for mouse events.
        - `DEBUG`: enables console logs (bool)
        """
        self.DEBUG = DEBUG
        if self.DEBUG: print("Creating polyDrawer for window " + window.windowName)

        self.window = window
        self.colour = colour # BGR colour
        self.done = False # Flag signalling we're done
        self.position = (0, 0) # Current position, so we can draw the line-in-progress
        self.points = [] # List of points defining our polygon

        self.stencil = np.zeros(window.sourceImage.shape).astype(window.sourceImage.dtype) # creates a new layer (with the dimensions of the source image) on which the poly will be shaped


        cv2.setMouseCallback(self.window.windowName, self.on_mouse) # makes cv2 listen to mouse inputs



    def on_mouse(self, event, x, y, buttons, user_param):
        """
        Mouse callback function that gets called for every mouse event (i.e. moving, clicking, etc.).
        Args are given by `cv2.setMouseCallback` (Args shouldn't be passed manually)
        - Captures mouse's location and clicks.
        - Saves the mouse's location on when clicked to self.points array/list
        - Method terminates on right-click.
        """

        # polyOverlay = deepcopy(self.window.sourceImage) # create a copy of the image. This copy will be the version that will be drawn over.

        if self.done: # Nothing more to do
            return
        
        if event == cv2.EVENT_MOUSEMOVE: # on MOUSE:MOVE, save the new position 
            # We want to be able to draw the line-in-progress, so update current mouse position
            self.position = (x, y)

        elif event == cv2.EVENT_LBUTTONDOWN: # on MOUSE:L CLICK, create a new point
            # Left click means adding a point at current position to the list of points
            if self.DEBUG: print("Adding point #%d with position(%d,%d) to poly with colour (%d, %d, %d)" % (len(self.points), x, y, self.colour[0],self.colour[1],self.colour[2]))
            
            self.points.append((x, y)) # adds the mouse location to the points list
            cv2.polylines(self.window.displayedImage, np.array([self.points]), False, self.colour, 3) # create the temp-poly lines
            self.window.refresh(self.window.displayedImage)# display the new temp-poly


        elif event == cv2.EVENT_RBUTTONDOWN: # on MOUSE:R CLICK, complete/close the polygon
            # Right click means we're done
            if self.DEBUG: print("Completing polygon with %d points." % len(self.points))
            
            # create selection
            cv2.fillPoly(self.stencil, np.array([self.points]), (255,255,255)) #fill the stencil with white given the provided shape
            self.window.displayedImage = Image.mask(Image.edgeC(65,self.window.sourceImage), cv2.cvtColor(self.stencil, cv2.COLOR_BGR2GRAY)) # make everything black, except for the poly-filled region

            # create lin reg
            #FIXME: make detail value parametrised
            self.createAvgLine(detail=self.window.detail)

            self.window.refresh(self.window.displayedImage) # display the poly-filled region
            self.done = True # shape drawing is completed



    def createAvgLine(self, detail:int):
        """
        Creates a line by finding the point location within a given image subsection. 
        The spacing between subsections is determined by the `detail` value
        - `detail`: the number of subsections to calculate the average

        How it works:
        - Divide the image into `n=detail` vertical subsections
        - Within each subsection, calculate the average location of the points, and make that into a new point
        - Draw a line from each subsection to the other, using the points as verticies for the line.
        """

        # =========
        # Prep: cropping the image to only the horizonatal
        # subsection that we will work in; using the min/max 
        # y locations of the polydrawer's points as a basic optimisation

        ylist = np.array(sorted(self.points, key=lambda y: y[1])) # a list of the polypoints in ascending y values
        workingImage = deepcopy(self.window.displayedImage[ylist[0][1]:ylist[-1][1],]) # crop the image based the min/max y vals
        
        if self.DEBUG:
            print(ylist) # prints the sorted list of y vals

            print("dim y: " + str(workingImage.shape[0]))
            print("dim x: " + str(workingImage.shape[1]))

    
        # =======
        # Calulating averages:
        whitePoints = []
        tempImage = deepcopy(workingImage) 

        # Find all the white points
        # FIXME: THIS IS VERY VERY INEFFICIENT/SLOW
        for y in range(workingImage.shape[0]): #loop thru the rows
            for x in range(workingImage.shape[1]): #loop thru the columns
                # workingImage[y%workingImage.shape[0], x%workingImage.shape[1]] = (255/2) # DEBUG: fill in every pixel that is travesed
                # print(x%workingImage.shape[1], y%workingImage.shape[0])
                if (workingImage[y%workingImage.shape[0], x%workingImage.shape[1]] == 255): # save the position of every white pixel
                    whitePoints.append((x, y))
                    # print([y, x])

        whitePoints = np.array(sorted(whitePoints, key=lambda y: y[0]))

        print(whitePoints)

        averagedPoints = []

        averagedPoints.append((0, whitePoints[0][1])) #add the left-most point using the left-most whitePoint's y coord

        for n in range(detail): # for each subsection
            x0 = (workingImage.shape[1]/detail) * n # the starting x coordinate of each subsection
            x1 = x0 + (workingImage.shape[1]/detail) # the end x coordinate of each subsection
            print("ranges x0: " + str(x0) + " , x1: " +str(x1))


            currAverage = [0,0] #stores the aveage x, y coord of the current subsection, which will be used as a point after the computations below are complete
            pointsInRange = 0

            for point in whitePoints: # loop thru the white points
                if  x0 < point[0] <= x1: # the point's x coord is within the range of the current subsection, add it to the average of the 
                    pointsInRange+=1
                    currAverage[0] += point[0]
                    currAverage[1] += point[1]
            
            if pointsInRange != 0:
                currAverage[0] /= pointsInRange
                currAverage[1] /= pointsInRange
            else:
                continue

            averagedPoints.append((int(currAverage[0]),int(currAverage[1]))) #after the average is computed, it's stored in a list of other avareged points

        averagedPoints.append((workingImage.shape[1], whitePoints[-1][1])) #add the right-most point using the right-most whitePoint's y coord


        #=======
        # drawing the lines that connect the averaged points
        print(averagedPoints)

        for n in range(len(averagedPoints)): # take back the average points to the basis of the original sourceImage
            averagedPoints[n][1] + ylist[0][1]

            averagedPoints[n] = (averagedPoints[n][0], averagedPoints[n][1] + ylist[0][1])

        print(averagedPoints)
        
        
        workingImage = cv2.cvtColor(workingImage, cv2.COLOR_GRAY2BGR)

        self.window.displayedImage = self.window.sourceImage

        cv2.polylines(self.window.displayedImage, np.array([averagedPoints]), False, (0,0,255), 1) 
        # cv2.polylines(workingImage, np.array([averagedPoints]), False, (0,0,255), 1) 

        self.window.refresh(self.window.displayedImage)

    #FIXME: this implementation of undo is sketchy/jank
    def undoPoint(self):
        """
        Pops the last point in `self.points` if CTRL+Z is pressed.
        - `input`: the key-press of the keyboard
        """

        while True:
            input = cv2.waitKey(0)
            if self.DEBUG & input != -1: print("Key pressed: " + str(input))
            

            if input ==  CTRLZ: #pop if ctrlZ is pressed
                polyOverlay = deepcopy(self.window.sourceImage) # create a copy of the image. This copy will be the version that will be drawn over.
                
                removed = self.points.pop()
                if self.DEBUG: print("Removed point: " + str(removed))
                
                cv2.polylines(polyOverlay, np.array([self.points]), False, self.colour, 3) # create the temp-poly # create a copy of the image. This copy will be the version that will be drawn over.
                self.window.refresh(polyOverlay) # display the image onto the window with the polylines
                
            
            if input == ESC | self.done: #terminate drawing if ESC or rMouse is clicked
                if self.DEBUG: print("Undo disabled")
                break

# ====================================


# running code
if __name__ == "__main__":
    DEBUG = True #global debug switch
    DETAIL = 10

    imgPath = "C:/Users/LENOVO/Desktop/test.png"
    # base image
    # image = Image(imgPath, (460, 1780), DEBUG=DEBUG)
    image = Image(imgPath, (0,824), DEBUG=DEBUG)

    # creating windows
    winRef = Window("Reference", drawable=True, image=image.img, detail=DETAIL, DEBUG=DEBUG)

    # initial displaying images onto windows
    winRef.refresh(image.img)

    # blur: 
    winRef.addTrackbar("Blur", (0, 100), partial(winRef.blurOnChange, image=image.img)) # creates blur trackbar on reference window
    winRef.setTrackbar("Blur", 100) # sets the trackbar's initial value 
    
    winRef.polyDrawerBed.undoPoint()



    # BUG: required to make the windows not instantly close
    Window.closeOnESC()









"""
END GOAL: (program is not here yet)

1:
select folder with the TIFF files

2:
select the reigon of surface, right click
select the reigon of bed, right click

3.
adjust threshold if needed

4. 
click done
repeat until the while set of TIFF files is done.

5.
click finished, 
image is saved in the same directory as the code file, with stitched TIFF files
"""