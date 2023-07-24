"""
BUGS:
- Trackbar/slider does not appear on windows
- Blur (and edge) views don't work

TODO:
- poly draw 
    - ctrl+z
"""

import cv2
import numpy as np



class Image:
    """
    Contains an image helpful methods for alternative displays of the image.
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



    def blur(image, strength):
        """
        Creates a blurred version of the given image using the given blur strength value.
        - image: the image to be blurred (read-in cv2 image, not path)
        - strength: value of the intensity of the blur (number)
        """

        print("Calculating blur")

        return cv2.GaussianBlur(image, (strength,strength), 0) #blur recalculation
    
    def edgeC(image, threshold):
        """
        Creates an edges version of the given image using the given blur strength value.
        - image: the image to be edge-detected (read-in cv2 image, not path)
        - threshold: value of the intensity of the edge-detection (number)
        """

        print("Calculating edges")

        return cv2.Canny(image=image, threshold1=threshold, threshold2=threshold) # CannyEdge calculation
         



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
        cv2.namedWindow(windowName, cv2.WINDOW_NORMAL) # Create window


   
    def refresh(self, image):
        """
        Shows the image on the window.
        - image: image to show on the window (read-in cv2 image, not path)
        """
        if self.DEBUG: print("Re-displaying image onto window " + self.windowName)

        cv2.imshow(self.windowName, image) # (re)Display the image
        
        k = cv2.waitKey(0) & 0xFF 
        if k == 27: # close all windows when ESC is pressed
            cv2.destroyWindow(self.windowName)


    def addTrackbar(self, label, range, callback):
        """
        Creates a trackbar onto the window.
        - label: Label of the trackbar.
        - range: start and end values of the trackbar.
        - callback: the function to be called everytime the trackbar is changed.
        """
        if self.DEBUG: print("Creating trackbar " + label +" with range " + range + " on window " + self.windowName)

        cv2.createTrackbar(label, self.windowName, range[0], range[1], callback) # Creates trackbar



    def __str__(self):
        """
        String representation of the window.
        Makes the code look a bit cleaner, think idk.
        """
        return self.windowName




# running code
if __name__ == "__main__":
    imgPath = "C:/Users/LENOVO/Desktop/uni/summer 2022/EAS Research/code/BedPickerTest/flight_141_30_0006351_0006375-reel_begin_end_TIFF.tiff"

    image = Image(imgPath, (460, 1780), True)

    winRef = Window("Reference", True)
    winRef.addTrackbar("epic", (10,50), winRef.refresh(image.img))
    dpge = Window("bing", True)

    winRef.refresh(image.img)
    dpge.refresh(image.img)


    # winBlur = Window("Blur", True)
    # winEdge = Window("Edge", True)

    # winBlur.refresh(image.blur(image.img, 10))
    # winEdge.refresh(image.edgeC(image.blur(image.img,10), 10))