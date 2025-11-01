#Load Image
import cv2
image = cv2.imread(r"G:\Project\PDF_TO_TEXT\2_OpenCV\processed_images\gray_page_1.jpeg")

if image is None:
    print("Error: Image not found")
else:
    print("Image loaded Successfully") 

#Display Image
cv2.imshow("Notes",image)
cv2.waitKey(0)
# 0 Means pause the window till any key got pressed in keyboard
cv2.destroyAllWindows()


if image is not None:
    cv2.imshow("Notes",image) #open the window
    cv2.waitKey(0) #wait for a key
    cv2.destroyAllWindows() #close the window
else:
    print("Could Not Load the image")