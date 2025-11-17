import os

def combine_texts_in_folder(base_folder):
    """
    Combine all .txt files from each subfolder into one combined file per folder.
    """
    for root, dirs, files in os.walk(base_folder):

        # ✅ Ignore already combined files here
        txt_files = [
            f for f in files 
            if f.endswith('.txt') and "_combined" not in f
        ]

        # Skip root folder (only merge subfolders)
        if not txt_files or root == base_folder:
            continue

        folder_name = os.path.basename(root)
        combined_path = os.path.join(root, f"{folder_name}_combined.txt")

        with open(combined_path, "w", encoding="utf-8") as outfile:
            for txt_file in sorted(txt_files):
                txt_path = os.path.join(root, txt_file)

                outfile.write(f"\n\n---- {txt_file} ----\n\n")
                
                with open(txt_path, "r", encoding="utf-8") as infile:
                    outfile.write(infile.read())

                # ✅ Add separator line after each file (optional)
                outfile.write("\n" + "="*50 + "\n")

        print(f"✅ Combined {len(txt_files)} files into: {combined_path}")

    print("\n🎯 All folders combined successfully!")
