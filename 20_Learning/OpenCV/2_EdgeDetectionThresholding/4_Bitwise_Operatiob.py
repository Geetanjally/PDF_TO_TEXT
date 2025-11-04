# Bitwise operations

# 🎯 Use Cases
# Combine two images.
# Cut out a specific region (using mask).
# Replace or hide an area in another image.
# Remove background or add watermark.

# Common OpenCV Bitwise Functions
# Function	Description
# cv2.bitwise_and(img1, img2, mask=None)	Keeps overlapping (common) parts
# cv2.bitwise_or(img1, img2, mask=None)	Combines both images
# cv2.bitwise_xor(img1, img2, mask=None)	Keeps non-overlapping areas
# cv2.bitwise_not(img)	Inverts pixels (black → white, white → black)

'''
- IMG1,IMG2 height width same
- use only black and white for clear mask
'''
import cv2
import numpy as np
img1 = np.zeros((300,300),dtype = "uint8")
img2 = np.zeros((300,300),dtype = "uint8")

cv2.circle(img1,(150,150),100,255,-1)
cv2.rectangle(img2,(100,100),(250,250),255,-1)

#Bitwise Operation
bitwise_and = cv2.bitwise_and(img1, img2, mask=None)	#Keeps overlapping (common) parts
bitwise_or = cv2.bitwise_or(img1, img2, mask=None)	#Combines both images
bitwise_xor = cv2.bitwise_xor(img1, img2, mask=None)	#Keeps non-overlapping areas
bitwise_not = cv2.bitwise_not(img1)	

cv2.imshow("Original image1",img1)
cv2.imshow("Original image2",img2)
cv2.imshow("ADD; ",bitwise_and)
cv2.imshow("OR; ",bitwise_or)
cv2.imshow("XOR; ",bitwise_xor)
cv2.imshow("NOT; ",bitwise_not)
cv2.waitKey(0)
cv2.destroyAllWindows()