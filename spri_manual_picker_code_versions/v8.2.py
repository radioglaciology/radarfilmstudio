"""
Changes:
- basic batch processing is implemented
    - paste in the folder path to the `path` variable the "running code" section
        - the folder has contain only TIFF radargrams; else program will crash (BUG)

BUGS:
- you may need to cycle SHIFT + A for lines to show up in edge view
- tweaking sliders after right-clicking produces undesirable results 

TODO:
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

import os                               # comes with Python 
from copy import deepcopy               # comes with Python 
from itertools import zip_longest       # comes with Python 
from functools import partial           # comes with Python 
import time                             # comes with Python ; used for optimisation/debuging
import csv                              # comes with Python ; outputs averaged points to csv files

import cv2                              # install OpenCV 
import numpy as np                      # install Numpy 


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
    def blur(strength: int, image:cv2.Mat):
        """
        Creates a blurred version of the given image using the given blur strength value.
        - `strength`: value of the intensity of the blur (number)
        - `image`: the image to be blurred (read-in cv2 image, not path)
        """

        # if self.DEBUG: print("Calculating blur")
        print("Calculating blur")
        # return cv2.bilateralFilter(image,5,strength,strength)
        # return cv2.GaussianBlur(image, (strength,strength), 0) #blur recalculation
        # return cv2.GaussianBlur(image,(strength,strength),0)
        # return cv2.medianBlur(image,ksize=strength)
        return cv2.blur(image, (strength, strength))

        
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
    Window object to show images on, a canvas of sorts.\n
    This class stores info regarding a window, its displayed image, and alternate versions of that image.
    """

    def __init__(self, windowName: str, image: Image = None, drawable=False, detail=10, drawColourSurface: tuple = (0, 0, 255), drawColourBed: tuple = (0, 255, 0),DEBUG: bool = False):
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

        # Images:
        self.image = image
        self.sourceImage = None
        if image != None:
            self.sourceImage = image.img # copy of the un-altered image
        self.edgeImage = Image.edgeC(50,self.sourceImage) # copy of the un-altered image with edge filter 

        self.displayedImage = None # the image that is displayed on the window, which may include lines, polys, overlays etc

        self.TOGGLEedge = False # toggles between showing the normal image vs image with edge filter 
        self.threshold = 50
        self.blurAmount = 10

        cv2.namedWindow(windowName, cv2.WINDOW_NORMAL) # Create window
        

        if drawable: # creates the necessary drawing components 
            self.polyDrawerSurface = PolygonDrawer(self, drawColourSurface,DEBUG= self.DEBUG) # creates polyDraw obj to select the edge region
            self.polyDrawerBed = PolygonDrawer(self, drawColourBed, DEBUG= self.DEBUG) # creates polyDraw obj to select the edge region
            self.drawDone = True
            self.detail = detail

            
    def filterImage(self, image:cv2.Mat):
        """
        Applies the filters based on current trackbar values.
        - `image`: image to be processed.
        """
        if self.TOGGLEedge:
            image = Image.edgeC(self.threshold,(Image.blur(self.blurAmount, image)))
            cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        else:
            image = Image.blur(self.blurAmount, image)


        if not self.drawDone:
            cv2.polylines(image, np.array([self.polyDrawerSurface.points]), False, self.polyDrawerSurface.colour, 3) # create the temp-poly lines

        return image

        





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
            
    
    def blurOnChange(self, val: int, image):
        """
        Helper method for blur trackbars.\n
        DO NOT USE WITHOUT A TRACKBAR.\n
        ONLY USE WITH A PARTIAL FUNCTION CALL.
        - `val`: blur strength value given by the trackbar.
        - `image`: image to be manipulated (not image path, not image object, read-in image. ie: image.img)
        """
        self.blurAmount= val
        self.refresh(self.filterImage(self.sourceImage))

        

    def edgeOnChange(self, val: int, image):
        """
        Helper method for edgeC trackbars.\n
        DO NOT USE WITHOUT A TRACKBAR.\n
        ONLY USE WITH A PARTIAL FUNCTION CALL.
        - `val`: edge threshold value given by the trackbar.
        - `image`: image to be manipulated (not image path, not image object, read-in image. ie: image.img)
        """
        self.threshold = val
        self.refresh(self.filterImage(self.sourceImage))

    def setDetailOnChange(self, val:int):
        """
        Helper method for detail trackbars.\n
        DO NOT USE WITHOUT A TRACKBAR.
        - `val`: the percision of the surface/bed line. (higher = more accurate + SLOWER)
        """
        self.detail = val




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
            
            # create lines
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
        #debug window
        win = Window("debug")

        # Prep: cropping the image to only the horizonatal
        # subsection that we will work in; using the min/max 
        # y locations of the polydrawer's points as a basic optimisation

        ylist = np.array(sorted(self.points, key=lambda y: y[1])) # a list of the polypoints in ascending y values
        xlist = np.array(sorted(self.points, key=lambda y: y[0])) # a list of the polypoints in ascending x values

        self.window.TOGGLEedge = True
        img = self.window.filterImage(self.window.sourceImage)
        img = Image.mask(img, cv2.cvtColor(self.stencil, cv2.COLOR_BGR2GRAY)) # make everything black, except for the poly-filled region

        workingImage = img[ylist[0][1]:ylist[-1][1],xlist[0][0]:xlist[-1][0]] # crop the image based the min/max y vals
        win.refresh(workingImage)
        

        if self.DEBUG:
            print(ylist) # prints the sorted list of y vals

            print("dim y: " + str(workingImage.shape[0]))
            print("dim x: " + str(workingImage.shape[1]))

        
        start = time.time() # time keeping for optimisation purposes
        # =======
        # Calulating averages:
        whitePoints = []

        # Find all the white points
        workingImage= cv2.cvtColor(workingImage, cv2.COLOR_GRAY2BGR) #convert to a BGR image
        Y, X = np.where(np.all(workingImage==[255,255,255],axis=2)) #retrive white points
        whitePoints = np.column_stack((X,Y)) #put the points in an array
        # --------------


        whitePoints = np.array(sorted(whitePoints, key=lambda y: y[0]))

        print(whitePoints)

        averagedPoints = []

        averagedPoints.append((0, whitePoints[0][1])) #add the left-most point using the left-most whitePoint's y coord

        # attempt 1-----
        # FIXME: NESTED FOR LOOPS == BAD ; REPLACE WITH NUMPY METHODS
        for n in range(detail): # for each subsection
            x0 = (workingImage.shape[1]/detail) * n # the starting x coordinate of each subsection
            x1 = x0 + (workingImage.shape[1]/detail) # the end x coordinate of each subsection
            print("ranges x0: " + str(x0) + " , x1: " +str(x1))


            currAverage = [0,0] #stores the aveage x, y coord of the current subsection, which will be used as a point after the computations below are complete
            pointsInRange = 0


            # attempt 1.1---
            for point in whitePoints: # loop thru the white points
                if  x0 < point[0] <= x1: # the point's x coord is within the range of the current subsection, add it to the average of the 
                    pointsInRange+=1
                    currAverage[0] += point[0]
                    currAverage[1] += point[1]
            # --------------

            # attempt 1.2--- FIXME
            # np.where()
            # --------------


                
            
            if pointsInRange != 0:
                currAverage = np.array(currAverage)/pointsInRange
            else:
                continue

            averagedPoints.append((int(currAverage[0]),int(currAverage[1]))) #after the average is computed, it's stored in a list of other avareged points
        # --------------

        # attempt 2-----

        # --------------


        averagedPoints.append((workingImage.shape[1], whitePoints[-1][1])) #add the right-most point using the right-most whitePoint's y coord


        #=======
        # drawing the lines that connect the averaged points
        print(averagedPoints)

        # attempt 1-----
        for n in range(len(averagedPoints)): # take back the average points to the basis of the original sourceImage
            # averagedPoints[n][1] + ylist[0][1]
            # averagedPoints[n][0] + xlist[0][0]

            averagedPoints[n] = (averagedPoints[n][0]  + xlist[0][0], averagedPoints[n][1] + ylist[0][1])
        # --------------

        # attempt 2----- DOESNT WORK :'(
        # np.array(averagedPoints) + (xlist[0][0], 0) + (0, ylist[0][1])
        # --------------

        print(averagedPoints)
        self.writeToCSV(averagedPoints)



        end = time.time() # time keeping for optimisation purposes
        if self.DEBUG: print("Average point line computed with (DETAIL=" + str(self.window.detail) + ") for (" + str(int(end - start)) + ") secs.") # time keeping for optimisation purposes
        
        
        self.window.displayedImage = self.window.sourceImage

        cv2.polylines(self.window.displayedImage, np.array([averagedPoints]), False, (0,0,255), 1) 
        # cv2.polylines(workingImage, np.array([averagedPoints]), False, (0,0,255), 1) 

        self.window.refresh(self.window.displayedImage)

    def writeToCSV(self, data):
        """
        Writes the averaged points to a CSV file.\n
        - `data`: the averaged points to be displayed
        """
        if self.DEBUG: print("Writing to CSV.")

        depths = [] # list that stores the pixel depths of each averaged point

        # retrieve the depth data from the averaged point
        img = cv2.cvtColor((self.window.sourceImage), cv2.COLOR_BGR2GRAY)
        for point in data:
            depths.append((point[0],point[1], img[point[1]-1, point[0]-1]))
        
        # prep for writing into csv
        depths = np.column_stack(depths)

        imgName = (self.window.image.imgPath.split("/")[-1]).split(".")[0] # extract the file name from the image path string 

        # writing into the file
        export_data = zip_longest(*depths, fillvalue = '')
        with open(imgName + ".csv", 'w', encoding="ISO-8859-1", newline='') as file:
            write = csv.writer(file)
            write.writerow(("avg points for: ", imgName, "Crop Values: ", self.window.image.cropVals[0],self.window.image.cropVals[1])) #header
            write.writerow(['x','y', 'depth']) #header
            write.writerows(export_data) # pixel coord data
            


    #FIXME: this implementation of undo is sketchy/jank
    def undoPoint(self):
        """
        Pops the last point in `self.points` if CTRL+Z is pressed.
        - `input`: the key-press of the keyboard
        """

        while True:
            input = cv2.waitKey(0)
            if self.DEBUG & input != -1: print("Key pressed: " + str(input))
            

            if input ==  CTRLZ: #pop the latest point from `self.points` if ctrlZ is pressed
                polyOverlay = deepcopy(self.window.sourceImage) # create a copy of the image. This copy will be the version that will be drawn over.
                polyOverlay = self.window.filterImage(polyOverlay)
                
                removed = self.points.pop()
                if self.DEBUG: print("Removed point: " + str(removed))
                
                polyOverlay = self.window.filterImage(polyOverlay)

                cv2.polylines(polyOverlay, np.array([self.points]), False, self.colour, 3) # draw the lines

                self.window.refresh(polyOverlay) # display the image onto the window with the polylines
                
            
            if input == ESC | self.done: #terminate drawing if ESC or rMouse is clicked
                if self.DEBUG: print("Undo disabled")
                break

            #additional: if shift+A is pressed, the edge detection filter is toggled
            if input == ord("A"):
                polyOverlay = deepcopy(self.window.sourceImage) # create a copy of the source image. This copy will be the version that will be drawn over.
                

                self.window.TOGGLEedge = np.bitwise_xor(self.window.TOGGLEedge, True) #bitwise toggle for the boolean variable
                if self.DEBUG: print("edge Toggle: " + str(self.window.TOGGLEedge))

                
                if self.window.TOGGLEedge: #if the edge filter is toggled
                    polyOverlay = self.window.filterImage(polyOverlay)
                    polyOverlay = cv2.cvtColor(polyOverlay, cv2.COLOR_GRAY2BGR) # convert the BW image to Color

                    if not self.done:
                        cv2.polylines(polyOverlay, np.array([self.points]), False, self.colour, 3) # draw the lines
                    self.window.refresh(polyOverlay) #display the image
                    
                else:
                    polyOverlay = self.window.filterImage(polyOverlay)

                    self.window.refresh(polyOverlay)
                    cv2.polylines(polyOverlay, np.array([self.points]), False, self.colour, 3) # draw the lines
                    self.window.refresh(polyOverlay)








# ====================================

# running code
if __name__ == "__main__":

    # iterate thru the images within the indicated folder
    # Get the list of all files and directories
    path = "C:/Users/LENOVO/Desktop/TIFFS"
    dir_list = os.listdir(path)
    
    print("Files and directories in '", path, "' :")
    
    # prints all files
    print(dir_list)



    for tiff in dir_list:
        DEBUG = True #global debug switch
        DETAIL = 100 #initial detail value

        # imgPath = "C:/Users/LENOVO/Desktop/test.png"

        imgPath = path + "/" + tiff #compose the image path from the folder and the items within

        # base image:=========================
        # image = Image(imgPath, (0,824), DEBUG=DEBUG)
        image = Image(imgPath, (460, 1780), DEBUG=DEBUG)

        # creating windows
        winRef = Window("Reference", drawable=True, detail=DETAIL, image=image, DEBUG=DEBUG)

        # initial displaying images onto windows
        winRef.refresh(Image.blur(10, winRef.sourceImage))
        # ===================================






        # trackbars:==========================
        # blur: 
        winRef.addTrackbar("Blur", (0, 100), partial(winRef.blurOnChange, image=image.img)) # creates blur trackbar on reference window
        winRef.setTrackbar("Blur", 10) # sets the trackbar's initial value 

        # edge
        winRef.addTrackbar("Threshold", (0,100), partial(winRef.edgeOnChange, image=Image.blur(winRef.blurAmount,winRef.sourceImage)))
        winRef.setTrackbar("Threshold", 25) # sets the trackbar's initial value 

        # detail:
        winRef.addTrackbar("Detail", (0, 1000) , winRef.setDetailOnChange)
        winRef.setTrackbar("Detail", 100) # sets the trackbar's initial value 
        # ===================================






        # ===================================
        # BUG: this function must be called for undo to work
        winRef.polyDrawerBed.undoPoint()
        # BUG: required to make the windows not instantly close
        Window.closeOnESC()
        # ===================================





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