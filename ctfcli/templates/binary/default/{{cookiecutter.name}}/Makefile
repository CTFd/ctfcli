.DEFAULT_GOAL := 64

32:
	gcc -g -Wall -m32 -o dist/{{cookiecutter.name}} src/{{cookiecutter.name}}.c

64:
	gcc -g -Wall -m64 -o dist/{{cookiecutter.name}} src/{{cookiecutter.name}}.c

clean:
	$(RM) dist/*
