# Как загрузить Rhythm First в `vvgstt/RhythmFirst`

## 1. Создать репозиторий на GitHub

1. Откройте `https://github.com/new`.
2. В поле **Owner** выберите `vvgstt`.
3. Введите название **RhythmFirst**.
4. Выберите Public или Private.
5. Не добавляйте README, `.gitignore` и лицензию: они уже лежат в проекте.
6. Нажмите **Create repository**.

Итоговый адрес: `https://github.com/vvgstt/RhythmFirst`.

## 2. Распаковать проект

Распакуйте архив Rhythm First. Внутри должны быть `README.md`, папки `app`, `public`, `scripts`, `tests` и файл `Rhythm First.command`.

## 3. Опубликовать через Terminal

Откройте Terminal, напишите `cd ` с пробелом, перетащите в окно Terminal распакованную папку проекта и нажмите Enter. Затем выполните команды по очереди:

```bash
git init
git branch -M main
git add .
git commit -m "Initial Rhythm First MVP"
git remote add origin https://github.com/vvgstt/RhythmFirst.git
git push -u origin main
```

Если Git сообщает `remote origin already exists`, вместо повторного `git remote add` выполните:

```bash
git remote set-url origin https://github.com/vvgstt/RhythmFirst.git
git push -u origin main
```

GitHub может открыть авторизацию в браузере. Обычный пароль аккаунта для `git push` не используется.

## 4. Проверить публикацию

Откройте `https://github.com/vvgstt/RhythmFirst` и проверьте:

- виден README с описанием проекта;
- присутствует `Rhythm First.command`;
- присутствуют папки `app`, `public`, `scripts`, `tests`, `docs`;
- во вкладке **Actions** запустилась проверка **Tests**.

В репозиторий не должны попадать `.venv`, `__pycache__`, записи пользователя и сгенерированные музыкальные файлы — они исключены через `.gitignore`.

## Последующие обновления

После изменений:

```bash
git add .
git commit -m "Describe the update"
git push
```

Для версии 0.2.1 можно создать тег:

```bash
git tag v0.2.1
git push origin v0.2.1
```
