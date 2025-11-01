import cv2
image = cv2.imread(r"G:\Project\PDF_TO_TEXT\2_OpenCV\processed_images\gray_page_1.jpeg")

if image is not None:
    success = cv2.imwrite("output_python.jpg",image)
    if success:
        print("Image saved succesfully as 'output_python.jpg'")
    else:
        print("Failed to save an image")
else:
    print("Could Not load the image")