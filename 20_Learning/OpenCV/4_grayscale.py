import cv2
image = cv2.imread(r"G:\Project\PDF_TO_TEXT\2_OpenCV\processed_images\gray_page_1.jpeg")

if image is not None:
    gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    cv2.imshow("GrayScaleImage",gray)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
else:
    print("Image not found")