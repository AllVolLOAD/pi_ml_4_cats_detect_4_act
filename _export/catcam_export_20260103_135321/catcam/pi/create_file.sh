#!/bin/bash
# Скрипт для создания файла
# Использование: ./create_file.sh <путь_к_файлу> [содержимое]

FILE_PATH="$1"
CONTENT="$2"

if [ -z "$FILE_PATH" ]; then
    echo "Использование: $0 <путь_к_файлу> [содержимое]"
    echo "Примеры:"
    echo "  $0 /tmp/test.txt"
    echo "  $0 /tmp/test.txt 'Hello World'"
    exit 1
fi

# Создаем директорию если её нет
DIR=$(dirname "$FILE_PATH")
if [ ! -d "$DIR" ]; then
    mkdir -p "$DIR"
    echo "Создана директория: $DIR"
fi

# Создаем файл
if [ -z "$CONTENT" ]; then
    # Создаем пустой файл
    touch "$FILE_PATH"
    echo "Создан пустой файл: $FILE_PATH"
else
    # Создаем файл с содержимым
    echo "$CONTENT" > "$FILE_PATH"
    echo "Создан файл с содержимым: $FILE_PATH"
fi

# Устанавливаем права
chmod 644 "$FILE_PATH"
echo "Файл создан: $FILE_PATH"

