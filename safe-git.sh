#!/bin/bash

# 1. Проверка статуса
git status

# 2. Сохраняем изменения, если есть что stash'ить
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Сохраняем изменения в stash..."
    git stash push -m "backup before pull"
else
    echo "Локальных изменений нет."
fi

# 3. Подтягиваем последние изменения с GitHub
echo "Подтягиваем изменения с origin/main..."
git fetch origin
git pull --rebase origin main

# 4. Восстанавливаем свои изменения
if git stash list | grep -q "backup before pull"; then
    echo "Восстанавливаем свои изменения..."
    git stash pop
fi

# 5. Проверяем статус
git status

# 6. Добавляем все изменения для коммита
# Безопасно игнорируем приватные файлы, например config.py, если они указаны в .gitignore
echo "Добавляем изменения в индекс..."
git add --all :/

# 7. Проверяем, есть ли изменения для коммита
if git diff --cached --quiet; then
    echo "Нет изменений для коммита. Коммит не создан."
else
    # 8. Создаём коммит
    echo "Введите сообщение коммита:"
    read commit_msg
    git commit -m "$commit_msg"

    # 9. Отправляем на GitHub
    git push origin main

    echo "Готово! Все изменения синхронизированы с origin/main."
fi
