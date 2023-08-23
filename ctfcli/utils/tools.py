import string


def strings(filename, min_length=4):
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

            if len(result) >= min_length:
                yield result

            result = ""

        if len(result) >= min_length:  # catch result at EOF
            yield result
