# To check given pdf have text layer or not?
import fitz

#Handwritten Notes have No Text layer
doc = fitz.open(r"G:\Project\PDF_TO_TEXT\0_Input_folder\TOC.pdf")
page = doc[0]
text = page.get_text("text")
print(len(text))

#Digital PDF's have Text Layer
doc = fitz.open(r"G:\Project\PDF_TO_TEXT\0_Input_folder\Synopsis.pdf")
page = doc[0]
text = page.get_text("text")
print(len(text))
