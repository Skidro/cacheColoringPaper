CC=gcc
CXX=g++
PGMS=bandwidth

CFLAGS=-O2 -Wall -g -static
CXXFLAGS=$(CFLAGS)
LDFLAGS=-Wl,--no-as-needed -lrt -static

all: $(PGMS)

bandwidth: bandwidth.o pagetype.o

clean:
	rm -f *.o *~ $(PGMS)
