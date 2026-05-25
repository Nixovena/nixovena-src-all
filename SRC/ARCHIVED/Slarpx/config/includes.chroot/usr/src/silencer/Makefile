# SILENCER - Kernel Info Leak Prevention Engine
# Build with security hardening flags

CC = gcc
CFLAGS = -O2 -Wall -Wextra -Werror=format-security -Werror=implicit-function-declaration \
         -D_FORTIFY_SOURCE=2 -fstack-protector-strong -fPIE
LDFLAGS = -Wl,-z,relro -Wl,-z,now -Wl,-z,noexecstack -pie

TARGET = silencer
SRC = silencer.c
INSTALL_DIR = /usr/bin

.PHONY: all clean install

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $<

install: $(TARGET)
	install -m 755 $(TARGET) $(INSTALL_DIR)/$(TARGET)

clean:
	rm -f $(TARGET)
