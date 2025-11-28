from nlp.prepare import prepare_text

sample = """
Digital Transformation  
- is a process of adopt-
ing digital technologies
to improve business per-
formance!!

Email: contact@test.com
"""

result = prepare_text(sample)

print("\nCLEAN TEXT:\n", result["clean_text"])
print("\nSENTENCES:\n", result["sentences"])
