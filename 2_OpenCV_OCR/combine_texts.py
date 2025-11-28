import os

def combine_texts_in_folder(base_folder):
    """
    Combine ALL .txt files (even if they are in the base folder)
    into one combined file.
    """
    txt_files = [
        f for f in os.listdir(base_folder)
        if f.endswith(".txt") and "_combined" not in f
    ]

    if not txt_files:
        print("⚠️ No text files found to combine in:", base_folder)
        return None

    combined_path = os.path.join(base_folder, "combined_output.txt")

    with open(combined_path, "w", encoding="utf-8") as outfile:
        for txt_file in sorted(txt_files):
            txt_path = os.path.join(base_folder, txt_file)

            outfile.write(f"\n\n---- {txt_file} ----\n\n")

            with open(txt_path, "r", encoding="utf-8") as infile:
                outfile.write(infile.read())

            outfile.write("\n" + "=" * 50 + "\n")

    print(f"✅ Combined {len(txt_files)} files into: {combined_path}")
    return combined_path
