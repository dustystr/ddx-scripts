#!/bin/bash

# Скрипт для автоматического копирования SSH ключа с использованием ssh-copy-id
# Использование: ./ssh_copy_auto.sh <ip_address> <password>

# Проверка наличия аргументов
if [ $# -ne 2 ]; then
    echo "Использование: $0 <ip_address> <password>"
    echo "Пример: $0 192.168.82.167 mypassword123"
    echo ""
    echo "Безопасная альтернатива (чтение пароля из файла):"
    echo "  $0 192.168.82.167 \"\$(cat password.txt)\""
    echo "  $0 192.168.82.167 \"\$SSH_PASSWORD\""
    exit 1
fi

IP_ADDRESS="$1"
PASSWORD="$2"
USERNAME="semaphore"
PUBLIC_KEY="/var/ddx/semaphore_id.pub"

# Проверка существования публичного ключа
if [ ! -f "$PUBLIC_KEY" ]; then
    echo "❌ Ошибка: Публичный ключ не найден: $PUBLIC_KEY"
    exit 1
fi

# Базовая проверка IP адреса
if ! [[ "$IP_ADDRESS" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    echo "❌ Ошибка: Неверный формат IP адреса: $IP_ADDRESS"
    exit 1
fi

echo "🔧 Начинаю настройку SSH ключа для ${USERNAME}@${IP_ADDRESS}"
echo ""

# Вариант 1: Использование sshpass (рекомендуемый способ)
if command -v sshpass > /dev/null 2>&1; then
    echo "📦 Использую sshpass для автоматизации..."
    
    # Пробуем выполнить ssh-copy-id с sshpass
    if sshpass -p "$PASSWORD" ssh-copy-id -f -i "$PUBLIC_KEY" -o StrictHostKeyChecking=no ${USERNAME}@${IP_ADDRESS} 2>/dev/null; then
        echo "✅ SSH ключ успешно скопирован!"
    else
        echo "❌ Ошибка при копировании ключа через sshpass"
        echo "Пробую альтернативный метод..."
    fi
else
    echo "⚠️  sshpass не установлен, пробую альтернативные методы..."
fi

# Вариант 2: Использование expect (более надежный)
echo ""
echo "🔄 Пробую метод с expect..."

# Создаем временный скрипт expect
TEMP_EXPECT=$(mktemp)
cat > "$TEMP_EXPECT" << 'EOF'
#!/usr/bin/expect -f

set ip [lindex $argv 0]
set password [lindex $argv 1]
set username [lindex $argv 2]
set pubkey [lindex $argv 3]

set timeout 20

# Отключаем стандартный вывод для чистоты
log_user 0

spawn ssh-copy-id -f -i $pubkey -o StrictHostKeyChecking=no ${username}@${ip}

expect {
    timeout {
        send_user "Ошибка: Таймаут подключения\n"
        exit 1
    }
    
    "Connection refused" {
        send_user "Ошибка: Подключение отклонено\n"
        exit 1
    }
    
    "No route to host" {
        send_user "Ошибка: Нет маршрута до хоста\n"
        exit 1
    }
    
    "password:" {
        send -- "$password\r"
        exp_continue
    }
    
    "Permission denied" {
        send_user "Ошибка: Неверный пароль\n"
        exit 1
    }
    
    "(yes/no)" {
        send "yes\r"
        exp_continue
    }
    
    "Number of key(s) added:" {
        send_user "Ключ успешно добавлен\n"
        set success 1
    }
    
    "already installed" {
        send_user "Ключ уже установлен\n"
        set success 1
    }
}

expect {
    eof {
        if {[info exists success]} {
            exit 0
        } else {
            exit 0  # ssh-copy-id может завершиться без сообщения об успехе
        }
    }
    
    timeout {
        send_user "Ошибка: Таймаут операции\n"
        exit 1
    }
}
EOF

# Делаем скрипт исполняемым и запускаем
chmod +x "$TEMP_EXPECT"
"$TEMP_EXPECT" "$IP_ADDRESS" "$PASSWORD" "$USERNAME" "$PUBLIC_KEY"

# Сохраняем результат
EXPECT_RESULT=$?

# Удаляем временный файл
rm -f "$TEMP_EXPECT"

# Проверяем результат
if [ $EXPECT_RESULT -eq 0 ]; then
    echo "✅ Ключ успешно скопирован или уже был установлен"
else
    echo "❌ Ошибка при копировании ключа"
    echo "Пробую прямой метод..."
fi

# Вариант 3: Прямой метод с созданием authorized_keys вручную
echo ""
echo "🛠️  Пробую прямой метод..."

# Используем expect для прямого копирования ключа
/usr/bin/expect << EOF 2>/dev/null
set timeout 15
spawn ssh -o StrictHostKeyChecking=no ${USERNAME}@${IP_ADDRESS} "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo 'SSH_KEY_COPIED'"
expect {
    "password:" { send "$PASSWORD\r" }
    "(yes/no)" { send "yes\r"; exp_continue }
    timeout { exit 1 }
}
expect {
    "SSH_KEY_COPIED" { exit 0 }
    eof { exit 0 }
    timeout { exit 1 }
}
EOF

if [ $? -eq 0 ]; then
    echo "✅ Ключ успешно установлен через прямой метод"
else
    echo "❌ Все методы не удались"
    echo ""
    echo "Возможные причины:"
    echo "  1. Неверный пароль для пользователя '$USERNAME'"
    echo "  2. Сервер $IP_ADDRESS недоступен"
    echo "  3. SSH сервер не запущен на порту 22"
    echo "  4. Пользователь '$USERNAME' не существует на сервере"
    exit 1
fi

# Финальная проверка
echo ""
echo "🔍 Проверяю подключение без пароля..."
if ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no ${USERNAME}@${IP_ADDRESS} "echo '✅ Подключение успешно!'" 2>/dev/null; then
    echo "✅ SSH подключение настроено корректно!"
    echo ""
    echo "Теперь вы можете подключаться без пароля:"
    echo "  ssh ${USERNAME}@${IP_ADDRESS}"
else
    echo "⚠️  Предупреждение: Ключ скопирован, но автоматическая проверка не удалась"
    echo "   Попробуйте подключиться вручную:"
    echo "   ssh ${USERNAME}@${IP_ADDRESS}"
fi
