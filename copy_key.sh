#!/bin/bash

# Скрипт для копирования SSH ключа на удаленный сервер
# Использование: ./copy_key.sh <ip_address>

# Проверка наличия аргумента
if [ $# -ne 1 ]; then
    echo "Использование: $0 <ip_address>"
    echo "Пример: $0 192.168.82.167"
    echo "Пример: $0 10.0.0.5"
    exit 1
fi

IP_ADDRESS="$1"
USERNAME="semaphore"
PUBLIC_KEY="/var/ddx/semaphore_id.pub"

# Проверка существования публичного ключа
if [ ! -f "$PUBLIC_KEY" ]; then
    echo "Ошибка: Публичный ключ не найден: $PUBLIC_KEY"
    exit 1
fi

# Проверка формата IP-адреса (базовая проверка)
if ! [[ "$IP_ADDRESS" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    echo "Ошибка: Некорректный формат IP-адреса: $IP_ADDRESS"
    exit 1
fi

# Настройки SSH
SSH_OPTS="-o StrictHostKeyChecking=no \
          -o UserKnownHostsFile=/dev/null \
          -o ConnectTimeout=10 \
          -o BatchMode=yes \
          -o PasswordAuthentication=no"

echo "Копируем SSH ключ на сервер $IP_ADDRESS..."

# Копируем ключ
cat "$PUBLIC_KEY" | \
    ssh $SSH_OPTS "${USERNAME}@${IP_ADDRESS}" \
    'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'

# Проверяем результат
if [ $? -eq 0 ]; then
    echo "✅ Ключ успешно скопирован на $IP_ADDRESS"
    
    # Дополнительная проверка подключения
    echo "Проверяем подключение..."
    ssh $SSH_OPTS "${USERNAME}@${IP_ADDRESS}" "echo 'SSH подключение успешно настроено!'" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ Подключение работает корректно"
    else
        echo "⚠️  Ключ скопирован, но возникли проблемы с проверкой подключения"
    fi
else
    echo "❌ Ошибка при копировании ключа на $IP_ADDRESS"
    echo "Возможные причины:"
    echo "  - Сервер недоступен"
    echo "  - Пользователь $USERNAME не существует на сервере"
    echo "  - Проблемы с сетевым подключением"
    exit 1
fi
