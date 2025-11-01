import cv2
image = cv2.imread(r"G:\Project\PDF_TO_TEXT\1_pdf_to_image\output_images\Data Mining\page_1.jpeg")

if image is None:
    print("Image Not found")
else:
    print("Image Loaded")

    resized = cv2.resize(image,(400,400))
    
    cv2.imshow("Original Image", image)
    cv2.imshow("Resized Image", resized)

    cv2.imwrite("resized_image.jpeg", resized)

    cv2.waitKey(0)
    cv2.destroyAllWindow()