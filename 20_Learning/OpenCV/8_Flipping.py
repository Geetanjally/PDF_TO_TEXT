#Flipping
#flipped = cv2.flip(image,flipcode)
    # flipcode: 0 (flip vertically: Top to Bottom)
               #1(flip Horizontally: left to right)
               # -1(flip both vertically and Horizontally)

import cv2
image = cv2.imread(r"G:\Project\PDF_TO_TEXT\1_pdf_to_image\output_images\Data Mining\page_1.jpeg")

if image is None:
    print("Image Not found")
else:
    flipped_horizontal = cv2.flip(image,1)
    flipped_vertical = cv2.flip(image,0)
    flipped_both = cv2.flip(image,-1)

    cv2.imshow("original:", image)
    cv2.imshow("Flipped Horizontal: ", flipped_horizontal)
    cv2.imshow("Flipped Vertical: ", flipped_vertical)
    cv2.imshow("Flipped Both: ", flipped_both)

    cv2.waitKey(0)
    cv2.destroyAllWindows