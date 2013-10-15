default: sqlite3xcu.so

%.so: %.c
	gcc -g -O -fPIC -shared -o $@ $^ -lmagic


clean:
	rm -f *~ *.so
