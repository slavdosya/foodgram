# Продуктовый помощник Foodgram

## Описание проекта Foodgram

«Продуктовый помощник»: приложение, на котором пользователи публикуют рецепты, подписываться на публикации других авторов и добавлять рецепты в избранное. Сервис «Список покупок» позволит пользователю создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

## Запуск проекта
1. Клонирование репозитория
   ```
   git clone git@github.com:slavdosya/foodgram.git
   ```
3. Создание виртуального окружения и его запуска
   ```
   python3 -m venv venv
   ```
   ```
   source /venv/bin/activate
   ```
5. Установка зависимостей
   ```
   pip install -r requirements.txt
   ```
7. Создать .env файл в корне проекта по примеру:
   ```
   DB_ENGINE=django.db.backends.postgresql # указываем, что работаем с postgresql
   DB_NAME=postgres # имя базы данных
   POSTGRES_USER=postgres # логин для подключения к базе данных
   POSTGRES_PASSWORD=postgres # пароль для подключения к БД (установите свой)
   DB_HOST=db # название сервиса (контейнера)
   DB_PORT=5432 # порт для подключения к БД
   DEBUG=0
   ```
8. Выполните миграции
   ```
   python manage.py migrate
   ```
9. Загрузите ингредиенты
    ```
    python manage.py import_csv ingredients.csv
    ```
10. Запустите сервер
    ```
    python manage.py runserver
    ```
   
