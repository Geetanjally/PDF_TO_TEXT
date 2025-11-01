# Image Rotation and Flipping

# M= cv2.getRotationMatrix2D(center, angle, scale)
# rotated_image = cv2.warpAffine(image,M,(weight,height))

# - Center is(Width//2, Height//2)
# Angle: of Rotation
# Scale:ZoomIn ,ZoomOut 
    # 1:same size
    # 0.5: half size
    # 2: Double Size

# Original Image
# M: Formula

import cv2
image = cv2.imread(r"G:\Project\PDF_TO_TEXT\1_pdf_to_image\output_images\Data Mining\page_1.jpeg")

if image is None:
    print("Image Not found")
else:
    h,w = image.shape[:2]
    M = cv2.getRotationMatrix2D((w//2,h//2), 90,1.0)
    rotated_image = cv2.warpAffine(image,M,(w,h))

    cv2.imshow("Rotated Image:",rotated_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows
             