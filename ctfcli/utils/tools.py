import string


def strings(filename, min=4):
    """
    Python implementation of strings
    https://stackoverflow.com/a/17197027
    """
    with open(filename, errors="ignore") as f:
        result = ""
        for c in f.read():
            if c in string.printable:
                result += c
                continue
            if len(result) >= min:
                yield result
            result = ""
        if len(result) >= min:  # catch result at EOF
            yield result
