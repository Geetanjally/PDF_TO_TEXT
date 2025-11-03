import cv2
image = cv2.imread(r"G:\Project\PDF_TO_TEXT\1_pdf_to_image\output_images\TOC\page_1.jpeg")
blurred = cv2.GaussianBlur(image, (7,7),0)
cv2.imshow("Original image",image)
cv2.imshow("blurred image",blurred)
cv2.waitKey(0)
cv2.destroyAllWindows()