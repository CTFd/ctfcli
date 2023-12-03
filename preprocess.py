import os


def replace_symlinks():
    os.system("""find . -type l -exec sh -c 'target=$(readlink -f "$0"); rm "$0" && cp "$target" "$0"' {} \;""")


if __name__ == "__main__":
    replace_symlinks()
