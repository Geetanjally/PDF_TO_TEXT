# .shape for finding image height,weigth and color channels
# output: (height,weight,color channels)

import cv2
image = cv2.imread(r"G:\Project\PDF_TO_TEXT\2_OpenCV\processed_images\gray_page_1.jpeg")

if image is not None:
    h,w,c = image.shape
    print(f"Heigth : {h}\nWeigth : {w}\n Channels : {c}")
else:
    print("Image not Found")
