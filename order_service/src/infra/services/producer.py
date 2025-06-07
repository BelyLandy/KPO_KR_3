from aiokafka import AIOKafkaProducer

class Producer:
    """
    Kafka-продюсер с поддержкой транзакций и идемпотентности.
    """

    def __init__(
        self,
        bootstrap_servers: str,
        transactional_id: str
    ) -> None:
        """
        :param bootstrap_servers: Адрес(а) Kafka-брокера
        :param transactional_id: Идентификатор для транзакций продьюсера
        """
        self._producer: AIOKafkaProducer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            transactional_id=transactional_id,
            enable_idempotence=True,
        )

    async def start(self) -> None:
        """Запустить подключение продьюсера."""
        await self._producer.start()

    async def stop(self) -> None:
        """Отключить продьюсер."""
        await self._producer.stop()

    async def send(
        self,
        topic: str,
        key: bytes,
        value: bytes
    ) -> None:
        """
        Отправить сообщение в Kafka в рамках транзакции.
        :param topic: Топик для отправки
        :param key: Ключ сообщения (bytes)
        :param value: Полезная нагрузка сообщения (bytes)
        :raises Exception: при ошибке отправки
        """
        # Начало транзакции
        await self._producer.begin_transaction()
        try:
            print(f"Отправка в топик {topic}: ключ={key}, значение={value}")
            # Отправляем и ждём подтверждения
            await self._producer.send_and_wait(topic, key=key, value=value)
            print(f"Сообщение успешно отправлено в {topic}")
            # Фиксируем транзакцию
            await self._producer.commit_transaction()
            print(f"Транзакция для {topic} зафиксирована")
        except Exception as exc:
            # Откатываем транзакцию при ошибке
            await self._producer.abort_transaction()
            print(f"[ERROR] Ошибка при отправке в {topic}: {exc}")
            raise
