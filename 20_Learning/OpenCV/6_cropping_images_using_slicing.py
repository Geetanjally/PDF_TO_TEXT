# Cropping Images using Slicing in OpenCV

# syntax
# cropped_img = image[startY:EndY, StartX:EndY]

import cv2
image = cv2.imread(r"G:\Project\PDF_TO_TEXT\1_pdf_to_image\output_images\Data Mining\page_1.jpeg")

if image is not None:
    cropped = image[100:500,50:1000]

    cv2.imshow("Original Image: ", image)
    cv2.imshow("Cropped: ",cropped)
    cv2.waitKey(0)
    cv2.destroyAllWindow()