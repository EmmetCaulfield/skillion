# Convenience Makefile to clean out editor backup files, compiled
# python, etc.

default:
	@echo 'This makefile only has a "clean" target'

clean:
	find ./ -name '*.pyc' -exec rm {} \;
	find ./ -name '*~'    -exec rm {} \;
	find ./ -name '*.so'  -exec rm {} \;
