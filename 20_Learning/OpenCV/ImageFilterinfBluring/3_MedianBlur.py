# Median Blur: Median blur replaces each pixel’s value with the median
# value of the neighboring pixels in a defined kernel window (like 3×3, 5×5, etc.).

# It’s mainly used to remove “salt and pepper” noise — those random 
# white and black dots you often see in scanned or handwritten images.

# The median value is less affected by extreme outliers (like 255) 
# than the average. Here we find the middle value of sorted pixels

# That’s why median blur preserves edges better and removes 
# “pepper-like” noise effectively.

# Syntax
# blurred = cv2.medianBlur(image,kernel_size)

import cv2
image = cv2.imread(r"G:\Project\PDF_TO_TEXT\1_pdf_to_image\output_images\TOC\page_1.jpeg")

blurred = cv2.medianBlur(image,3)
cv2.imshow("Original image",image)
cv2.imshow("blurred image",blurred)
cv2.waitKey(0)
cv2.destroyAllWindows()

