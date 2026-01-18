import os

def main():
    docs_root = os.environ.get("DOCS_ROOT", "")
    if docs_root:
        print(docs_root)
    else:
        print("")

if __name__ == "__main__":
    main()

