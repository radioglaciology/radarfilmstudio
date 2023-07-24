"""
Changes:
- image stitching is implemented
- variable batch size for stitching TIFFs
- Surface and bed are logged in sperate CSV files

BUGS:
- all images must match exactly in vertical dimensions; else stitching will not work (see cropVals)
- tweaking sliders after right-clicking produces undesirable results 
- make sure to close EXCEL when calculating average lines for surface/bed
- the folder may only contain TIFF radargrams (images files) ; else program will crash 

TODO:
- CSV
    - log normal view AND edges view pixel depth the csv
    - log surface AND bed data

- Modify a selection and parameters after creating a line

- have a max threshold for interpolation between points
    - (see testImages/ 3.png)



MINOR BUGS:
- windows close on any keyboard press, not ESC
MINOR TODOS:
- find alternative to partial functions for trackbar callback functions
    - potential refactoring for the structure of the classes/methods
"""

import os
from copy import deepcopy
from itertools import zip_longest
from functools import partial
import time
import csv

import cv2                              # install OpenCV 
import numpy as np                      # install Numpy 


# Text-input defintions to make code more readable
SHIFT = 16
CTRL = 17
ALT = 18
ESC = 27
CTRLZ = 26 



# ====================================




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
        image1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
        # image2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)

        return cv2.bitwise_and(image1, image2) # compute the mask with the given shape: fill everything with black except the provided shape


    @staticmethod
    def stitch(listOfimages):
        """
        Takes in an array/list of images, and stitches them horizontally.
        - `listOfImages`: the array of images that will be stitched into a singular wide image.
        """
        result = listOfimages[0]
        for image in range(1, len(listOfimages)):
            result = np.concatenate((result,listOfimages[image]), axis=1)

        return result



# ====================================





class Window:
    """
    Window object to show images on, a canvas of sorts.\n
    This class stores info regarding a window, its displayed image, and alternate versions of that image.
    """

    def __init__(self, windowName: str, image: Image = None, drawable=False, detail=10, drawColourSurface= (255, 0, 0), drawColourBed = (0, 255, 0), DEBUG = False):
        """
        Creates a resizable window.
        - `windowName`: the name of the window (string)
        - `image`: image to be associated with this window.
        - `drawable`: enables polydraw on this window
        - `detail`: accuracy of the average average line
        - `drawColourSurface`: colour of surface polyDraw (3tuple: (B, G, R)) (Default = BLUE)
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
        self.resultImage = deepcopy(self.sourceImage) # the image that the average lines will be drawn on 

        self.displayedImage = None # the image that is displayed on the window, which may include lines, polys, overlays etc

        # Toggles:
        self.displayToggle = 0 # toggles the different displays (0: Source, 1: Blur, 2: Edge(Blur))
        self.active = 0 # keeps track of what's active (surface or bed)
        
        # 
        self.threshold = 50
        self.blurAmount = 10

        # Create window
        cv2.namedWindow(windowName, cv2.WINDOW_NORMAL) 
        

        if drawable: # creates the necessary drawing components 
            self.polyDrawerBed = PolygonDrawer(self, drawColourBed, DEBUG= self.DEBUG) # creates polyDraw obj to select the edge region
            self.polyDrawerSurface = PolygonDrawer(self, drawColourSurface,DEBUG= self.DEBUG) # creates polyDraw obj to select the edge region
            self.drawDone = False
            self.detail = detail

            


            
    def filterImage(self, image:cv2.Mat):
        """
        Applies the filters based on current trackbar values.
        - `image`: image to be processed.
        """
        if self.displayToggle == 1:
            image = Image.blur(self.blurAmount, image) 

        elif self.displayToggle == 2:
            image = Image.edgeC(self.threshold,(Image.blur(self.blurAmount, image)))
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        else:
            image = deepcopy(image)

        if not self.drawDone:
            cv2.polylines(image, np.array([self.polyDrawerSurface.points]), False, self.polyDrawerSurface.colour, 3) # create the temp-poly lines
            cv2.polylines(image, np.array([self.polyDrawerBed.points]), False, self.polyDrawerBed.colour, 3) # create the temp-poly lines

        return image

        





    def surfaceBedSwitch (self, switch):
        """
        Determines whether to draw the surface or bed,
        based on the trackbar values (0, 1), (surface, bed) respectively.
        """
        self.active = switch # save the value of whats active
        if switch == 0: # enables drawing and undos for the surface

            if self.DEBUG: print("Drawing surface")
            
            self.polyDrawerSurface.done = False
            self.polyDrawerBed.done = True

            cv2.setMouseCallback(self.windowName, self.polyDrawerSurface.on_mouse) # makes cv2 listen to mouse inputs

            # self.polyDrawerSurface.undoPoint()

        else:  # enables drawing and undos for the bed
    
            if self.DEBUG: print("Drawing bed")

            self.polyDrawerSurface.done = True
            self.polyDrawerBed.done = False

            cv2.setMouseCallback(self.windowName, self.polyDrawerBed.on_mouse) # makes cv2 listen to mouse inputs

            # self.polyDrawerBed.undoPoint()


            
   
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
        self.blurAmount= val+1
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

    def drawLines (self):
        """
        Draws the surface and bed average lines then displays the result.
        """
        start = time.time() # time keeping for optimisation purposes

        # draw surface avg line
        #TODO: Multiprocess thread1 start here
        if self.DEBUG: print("Completing polygon with %d points." % len(self.polyDrawerSurface.points))
        if len(self.polyDrawerSurface.points) >= 3: # make sure there are enough points for create an avg line selection
            cv2.fillPoly(self.polyDrawerSurface.stencil, np.array([self.polyDrawerSurface.points]), (255,255,255)) #fill the stencil with white given the provided shape
            self.polyDrawerSurface.createAvgLine(detail=self.detail, area="Surface")
        
        # draw bed avg line
        #TODO: Multiprocess thread2 start here
        if self.DEBUG: print("Completing polygon with %d points." % len(self.polyDrawerBed.points))
        if len(self.polyDrawerBed.points) >= 3: # make sure there are enough points for create an avg line selection
            cv2.fillPoly(self.polyDrawerBed.stencil, np.array([self.polyDrawerBed.points]), (255,255,255)) #fill the stencil with white given the provided shape
            self.polyDrawerBed.createAvgLine(detail=self.detail, area="Bed")
        

        self.polyDrawerSurface.done = True # shape drawing is completed
        self.polyDrawerBed.done = True # shape drawing is completed
        #TODO: Multiprocess threads (1,2) wait until all are done

        self.refresh(self.resultImage) # display the poly-filled region


        end = time.time() # time keeping for optimisation purposes
        if self.DEBUG: print("Average point line computed with (DETAIL=" + str(self.detail) + ") for (" + str(int(end - start)) + ") secs.") # time keeping for optimisation purposes


    @staticmethod
    def undoOnChange(val, targetWindow):
        """
        Undoes a point from the bed or surface when the trackbar value is changed.\n
        This is a very janky way of implementing undo because OpenCV's keyboard interactions are very buggy.
        DO NOT USE WITHOUT A TRACKBAR.
        """
        
        # targetWindow = Window(targetWindow)
        if targetWindow.active == 0: # perform undos for surface drawer if it's active
            if targetWindow.DEBUG: print("Undoing for Surface")
            targetWindow.polyDrawerSurface.points.pop()
        else:
            if targetWindow.DEBUG: print("Undoing for bed")
            targetWindow.polyDrawerBed.points.pop()

        targetWindow.refresh(targetWindow.filterImage(targetWindow.sourceImage))

    
    def viewModeOnChange(self, val):
        """
        Toggles view based on `val` (0: unaltered image, 1: filtered image, 2: edge view)
        DO NOT USE WITHOUT A TRACKBAR.
        """
        self.displayToggle = val
        self.refresh(self.filterImage(self.sourceImage))






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
        # self.avgPointsSurface = 
        # self.avgPointsSurface = 



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

            self.window.drawDone = True
            self.window.drawLines()









    def createAvgLine(self, detail:int, area:str):
        """
        Creates a line by finding the point location within a given image subsection. 
        The spacing between subsections is determined by the `detail` value
        - `detail`: the number of subsections to calculate the average
        - `area`: indicates whether this is a surface or bed in the saved csv's file name

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


        self.window.displayToggle = 2
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
        for n in range(len(averagedPoints)): # take back the average points to the basis of the original sourceImage
            averagedPoints[n] = (averagedPoints[n][0]  + xlist[0][0], averagedPoints[n][1] + ylist[0][1])
        if self.DEBUG: print(averagedPoints)


        self.writeToCSV(averagedPoints,area)



        end = time.time() # time keeping for optimisation purposes
        if self.DEBUG: print("Average point line computed with (DETAIL=" + str(self.window.detail) + ") for (" + str(int(end - start)) + ") secs.") # time keeping for optimisation purposes


        cv2.polylines(self.window.resultImage, np.array([averagedPoints]), False, self.colour, 1) 




    def writeToCSV(self, data, area:str):
        """
        Writes the averaged points to a CSV file.\n
        This method formats the CSV info so the bed data does not overwrite the surface.
        - `data`: the averaged points to be logged
        - `area`: indicates whether this is a surface or bed in the saved csv's file name
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
        with open(imgName + area + ".csv", 'w', encoding="ISO-8859-1", newline='') as file:
            write = csv.writer(file)
            write.writerow(("avg points for: ", imgName, "Crop Values: ", self.window.image.cropVals[0],self.window.image.cropVals[1], "Detail:", self.window.detail)) #header
            write.writerow(['x','y', 'depth']) #header
            write.writerows(export_data) # pixel coord data

            






# ====================================


class App:
    """
    `class App` is the overall manager of all the operations that this application handles.
    """

    def __init__ (self, path: str, batchSize:int):
        self.path = path
        self.batchSize = batchSize
        self.dir_list = os.listdir(path) # Get the list of all files and directories

        # self.dir_list = sorted(self.dir_list, key=lambda x: int(os.path.splitext(x)[0]))


    def process(self, tiff):
        
        # ================================
        # ================================
        # ================================
        # MAIN WINDOW 
        DEBUG = True #global debug switch
        DETAIL = 100 #initial detail value


        imgPath = self.path + "/" + tiff #compose the image path from the folder and the items within

        # base image:=========================
        # image = Image(imgPath, (0,824), DEBUG=DEBUG)
        image = Image(imgPath, (460, 1780), DEBUG=DEBUG)

        # creating windows
        winRef = Window("Reference", drawable=True, detail=DETAIL, image=image, DEBUG=DEBUG)

        # initial displaying images onto windows
        winRef.refresh(winRef.sourceImage)
        # ===================================






        # trackbars:==========================
        # blur: 
        winRef.addTrackbar("Blur", (1, 100), partial(winRef.blurOnChange, image=image.img)) # creates blur trackbar on reference window
        winRef.setTrackbar("Blur", 10) # sets the trackbar's initial value 

        # edge
        winRef.addTrackbar("Threshold", (0,100), partial(winRef.edgeOnChange, image=Image.blur(winRef.blurAmount,winRef.sourceImage)))
        winRef.setTrackbar("Threshold", 25) # sets the trackbar's initial value 

        # detail:
        winRef.addTrackbar("Detail", (0, 1000) , winRef.setDetailOnChange)
        winRef.setTrackbar("Detail", 100) # sets the trackbar's initial value 

        # surface/bed selector:
        winRef.addTrackbar("S/B Select", (0, 1), winRef.surfaceBedSwitch)
        
        # undo trackbar (this is kinda stupid)
        winRef.addTrackbar("Undo", (0,1), partial(Window.undoOnChange, targetWindow=winRef))

        # toggle views
        winRef.addTrackbar("View Mode", (0,2), winRef.viewModeOnChange)

        # ================================
        # BUG: required to make the windows not instantly close
        Window.closeOnESC()
        return winRef.resultImage



    def launch(self, saveDirectory = ""):

        anchorCounter = 0 # counter that points at the starting position of the current batch (i.e.: if batchSize = 3: batch 1 : anchorCounter = 0; batch 2 : anchorCounter = 3) hopefully that makes sense
        print("TARGET: "+str(len(self.dir_list)))
        print(self.dir_list)
        
        count = 0
        while anchorCounter < len(self.dir_list):
            resImages = [] # list containing the resulting line calculation from each images; will be used later for image stitching
            
            for count in range(self.batchSize):
                if anchorCounter+count >= len(self.dir_list):
                    break

                #FIXME: incompelete function
                currImage = self.dir_list[anchorCounter+count]
                resImages.append(self.process(currImage))

                print("Current image: " + str(anchorCounter+count))
            print()
                
            anchorCounter = anchorCounter + self.batchSize

            res = Image.stitch(resImages)
            count = anchorCounter - self.batchSize + 1
            print("saving Image " + str(count))
            cv2.imwrite(saveDirectory + "/" + str(count) + ".png", res)
            
                



# running code
if __name__ == "__main__":

    # DEV/DEBUG SETUP
    # app = App("C:/Users/LENOVO/Desktop/testImages Sequence", 5)
    # app.launch("C:/Users/LENOVO/Desktop/saveHere/")

    # ACTUAL SETUP
    app = App("C:\\Users\\dtarz\\Box\\Summer 2022\\InteractiveSurfaceBedPicker\\Flight141_ZScopes", 5)
    app.launch("C:\\Users\\dtarz\\Box\\Summer 2022\\InteractiveSurfaceBedPicker\\Flight141_ZScopesProcessed")

    cv2.waitKey(0) # required to make the window not instantly close





"""
END GOAL: (program is not here yet)

1:
select folder with the TIFF files (sorta complete)

2:
select the reigon of surface (complete)
select the reigon of bed, right click (complete)

3.
adjust threshold if needed (sorta complete)

4. 
click done
repeat until the while set of TIFF files is done. (complete)

5.
click finished, 
image is saved in the same directory as the code file, with stitched TIFF files (sorta complete)
"""