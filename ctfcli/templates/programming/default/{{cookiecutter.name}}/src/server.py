#!/usr/bin/env python
import random

from six.moves import input


def server():
    print("Hello World")
    secret = random.randint(1, 100)
    while True:
        guess = input("What's the random number?")
        if int(guess) == secret:
            print("You got it!")
            exit()
        else:
            print("No.")


if __name__ == "__main__":
    server()
