# Конструирование программного обеспечения. Контрольная работа №3

## Работу выполнил **Девятов Денис Сергеевич, группа БПИ-238**

## Документация к разработанным микросервисам.

---

## Инструкция запуска.

В корне проекта, выполните в терминале:

```
# Сборка и запуск стека.
docker compose up --build

# Остановка и удаление томов.
docker compose down -v
```

![image](https://github.com/user-attachments/assets/5bef5e2b-7efe-4508-bd54-a679467e7214)

После запуска контейнеров можно открыть Swagger на 8001 и проверить работу решения.

| URL                                                      | Сервис                        |
| -------------------------------------------------------- | ----------------------------- |
| [http://localhost:8000/docs](http://localhost:8001/docs) | Orders Service                |
| [http://localhost:8002/docs](http://localhost:8002/docs) | Payment Service               |

![image](https://github.com/user-attachments/assets/d6c7a75e-34c4-4974-9427-3ec949155c32)
![image](https://github.com/user-attachments/assets/d8f66d66-3592-4036-ad01-34ad3d5f8a2b)

---

## Запуск автоматических тестов

```bash
pytest --cov=src --cov-report=term-missing
```

Покрытие по `coverage.py` ≥ **65 %**.

![image](https://github.com/user-attachments/assets/3cc1dba1-b003-440b-98f2-9ef3b94df7f7)
![image](https://github.com/user-attachments/assets/386e34cf-9824-4d21-87a5-f3aaeccb2cdc)

---
