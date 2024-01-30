import hashlib


def hash_file(fp, algo="sha1"):
    fp.seek(0)
    if algo == "sha1":
        h = hashlib.sha1()  # nosec
        # https://stackoverflow.com/a/64730457
        while chunk := fp.read(1024):
            h.update(chunk)
        fp.seek(0)
        return h.hexdigest()
    else:
        raise NotImplementedError
