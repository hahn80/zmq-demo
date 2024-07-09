# Compiler
JAVAC = javac
JAVA = java

# Classpath for the dependencies
CP = libs/jeromq-0.6.0.jar:libs/gson-2.11.0.jar

# Source and output files
SRC = ZmqClient.java
CLASS = ZmqClient

# Target to compile the Java source file
all: compile run

# Compile the Java source file
compile:
	$(JAVAC) -cp $(CP) -Xlint:deprecation -Xlint:unchecked $(SRC)

# Run the compiled Java class
run:
	$(JAVA) -cp .:$(CP) $(CLASS)

# Clean the compiled class file
clean:
	rm -f *.class

.PHONY: all compile run clean

