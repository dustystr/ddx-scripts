#!/bin/bash

# Скрипт для выполнения Python скрипта с каждой строкой файла (кроме первой) в качестве аргумента
# Использование: ./script.sh <input_file> [python_script]

# Проверка наличия аргументов
if [ $# -lt 1 ]; then
    echo "Использование: $0 <input_file> [python_script]"
    echo "Пример 1: $0 ip_addresses.txt"
    echo "Пример 2: $0 servers.txt process.py"
    exit 1
fi

INPUT_FILE="$1"
PYTHON_SCRIPT="${2:-extract_ips.py}"  # По умолчанию используем extract_ips.py

# Проверка существования файла
if [ ! -f "$INPUT_FILE" ]; then
    echo "Ошибка: Файл '$INPUT_FILE' не найден"
    exit 1
fi

# Проверка существования Python скрипта
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Ошибка: Python скрипт '$PYTHON_SCRIPT' не найден"
    exit 1
fi

echo "Обработка файла: $INPUT_FILE"
echo "Используем скрипт: $PYTHON_SCRIPT"
echo "--------------------------------"

# Читаем файл, пропуская первую строку
line_number=0
while IFS= read -r line || [[ -n "$line" ]]; do
    ((line_number++))
    
    # Пропускаем первую строку
    if [ $line_number -eq 1 ]; then
        continue
    fi
    
    # Пропускаем пустые строки
    if [ -z "$line" ] || [ "$line" = "" ]; then
        continue
    fi
    
    # Убираем пробелы в начале и конце
    line_cleaned=$(echo "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    
    echo "Обработка строки $line_number: '$line_cleaned'"
    
    # Выполняем Python скрипт с аргументом
    python3 "$PYTHON_SCRIPT" "$line_cleaned" --ssh-user administrator --ssh-password inbody --semaphore-password "sBrEVAPHV2Ukgy2L"
    . /home/anko/repo/ddx-scripts/copy_key.sh $line_cleaned sBrEVAPHV2Ukgy2L
    
    echo "--------------------------------"
done < "$INPUT_FILE"

echo "Обработка завершена. Обработано $((line_number-1)) строк."
