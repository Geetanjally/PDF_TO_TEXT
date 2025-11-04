import cv2
image = cv2.imread(r"G:\Project\PDF_TO_TEXT\1_pdf_to_image\output_images\TOC\page_1.jpeg",cv2.IMREAD_GRAYSCALE)
edges = cv2.Canny(image,50,150)

cv2.imshow("Original image",image)
cv2.imshow("Edges ",edges)
cv2.waitKey(0)
cv2.destroyAllWindows()