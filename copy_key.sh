#!/bin/bash

# Скрипт для копирования SSH ключа с использованием expect и пароля как аргумента
# Использование: ./copy_key_with_password.sh <ip_address> <password> [username]

# Проверка наличия аргументов
if [ $# -lt 2 ]; then
    echo "Использование: $0 <ip_address> <password> [username]"
    echo "Пример: $0 192.168.82.167 mypassword123"
    echo "Пример: $0 192.168.82.167 mypassword123 semaphore"
    echo ""
    echo "Безопасная альтернатива (передача через переменную):"
    echo "  PASSWORD='mypass' $0 192.168.82.167 \"\$PASSWORD\""
    exit 1
fi

IP_ADDRESS="$1"
PASSWORD="$2"
USERNAME="${3:-semaphore}"  # По умолчанию используем semaphore
PUBLIC_KEY="/home/anko/id_ed25519.pub"

# Проверка существования публичного ключа
if [ ! -f "$PUBLIC_KEY" ]; then
    echo "Ошибка: Публичный ключ не найден: $PUBLIC_KEY"
    exit 1
fi

# Читаем публичный ключ
PUB_KEY_CONTENT=$(cat "$PUBLIC_KEY")

# Используем expect для автоматического ввода пароля
expect << EOF
set timeout 15
set send_slow {1 .01}

# Отключаем вывод в stdout для безопасности
log_user 0

spawn ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${USERNAME}@${IP_ADDRESS} "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

expect {
    timeout {
        puts "Ошибка: Таймаут подключения"
        exit 1
    }
    
    "Connection refused" {
        puts "Ошибка: Подключение отклонено"
        exit 1
    }
    
    "No route to host" {
        puts "Ошибка: Нет маршрута до хоста"
        exit 1
    }
    
    "password:" {
        send -- "$PASSWORD\r"
        exp_continue
    }
    
    "Permission denied" {
        puts "Ошибка: Неверный пароль или доступ запрещен"
        exit 1
    }
    
    "Are you sure you want to continue connecting" {
        send "yes\r"
        exp_continue
    }
}

expect {
    eof {
        puts "Успех: Ключ скопирован"
        exit 0
    }
    
    timeout {
        puts "Ошибка: Таймаут после отправки пароля"
        exit 1
    }
}
EOF

# Проверяем результат выполнения expect
EXPECT_RESULT=$?

if [ $EXPECT_RESULT -eq 0 ]; then
    echo "✅ SSH ключ успешно скопирован на ${USERNAME}@${IP_ADDRESS}"
    
    # Дополнительная проверка (без пароля, если ключ работает)
    echo "Проверяем подключение без пароля..."
    ssh -o BatchMode=yes -o ConnectTimeout=5 ${USERNAME}@${IP_ADDRESS} "echo 'Подключение успешно!'" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "✅ Подключение по SSH ключу работает корректно"
    else
        echo "⚠️  Ключ скопирован, но автоматическое подключение не работает"
    fi
else
    echo "❌ Ошибка при копировании ключа"
    exit 1
fi
