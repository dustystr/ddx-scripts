#!/bin/bash

# Отключаем все проверки хоста
SSH_OPTS="-o StrictHostKeyChecking=no \
          -o UserKnownHostsFile=/dev/null \
          -o ConnectTimeout=10 \
          -o BatchMode=yes \
          -o PasswordAuthentication=no"

# Копируем ключ
cat /home/anko/id_ed25519.pub | \
    ssh $SSH_OPTS semaphore@192.168.82.167 \
    'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'

# Проверяем результат
if [ $? -eq 0 ]; then
    echo "Ключ успешно скопирован на 192.168.82.167"
else
    echo "Ошибка при копировании ключа"
    exit 1
fi
