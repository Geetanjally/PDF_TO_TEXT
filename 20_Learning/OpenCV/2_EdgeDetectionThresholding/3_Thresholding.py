# Thresholding is a technique to convert a grayscale image into a 
# binary (black & white) image based on a threshold value.

# 👉 It’s like saying:
#     “If pixel brightness is above a certain level, make it white 
#     — otherwise make it black.”

# 🧠 Why It’s Important (for your project)

# - For OCR or handwritten text extraction, background variations 
# (shadows, paper texture, etc.) make text hard to detect.

# - Thresholding removes that background — leaving only clear black text 
# on white background 🧾

# syntax
# thresholded_image = cv2.threshold(image,thresh_value,max_value,method)

import cv2
image = cv2.imread(r"G:\Project\PDF_TO_TEXT\1_pdf_to_image\output_images\TOC\page_1.jpeg",cv2.IMREAD_GRAYSCALE)
ret , thresh_image = cv2.threshold(image,120,255,cv2.THRESH_BINARY)

cv2.imshow("Original image",image)
cv2.imshow("Threshold Image ",thresh_image)
cv2.waitKey(0)
cv2.destroyAllWindows()