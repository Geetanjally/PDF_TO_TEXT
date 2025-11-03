# Sharpening: Sharpening is the process of enhancing edges and fine details in an image.
# It increases contrast at the edges so that text or object boundaries look clearer and more defined.

# in handwritten or scanned notes:
# Blurring and noise make edges faint.
# Sharpening boosts those faded strokes — so characters become clearer for OCR.

# syntax
# cv2.filter2D(src,ddepth,kernel)

import cv2
import numpy as np
image = cv2.imread(r"G:\Project\PDF_TO_TEXT\1_pdf_to_image\output_images\TOC\page_1.jpeg")

sharpen_kernel = np.array([
    [0,-1,0],
    [-1,5,-1],
    [0,-1,0]
])
sharpened = cv2.filter2D(image,-1,sharpen_kernel)
cv2.imshow("Original image",image)
cv2.imshow("Sharpened image",sharpened)
cv2.waitKey(0)
cv2.destroyAllWindows()