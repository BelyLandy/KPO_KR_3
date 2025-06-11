from aiokafka import AIOKafkaProducer


class Producer:
    """ Kafka-продюсер с поддержкой транзакций и идемпотентности. """

    def __init__(
        self,
        bootstrap_servers: str,
        transactional_id: str
    ) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            transactional_id=transactional_id,
            enable_idempotence=True,
        )

    async def start(self) -> None:
        """ Запускает продюсер. """
        await self._producer.start()

    async def stop(self) -> None:
        """ Останавливает продюсер. """
        await self._producer.stop()

    async def send(
        self,
        topic: str,
        key: bytes,
        value: bytes
    ) -> None:
        """ Отправляет сообщение в Kafka в рамках транзакции. """
        await self._producer.begin_transaction()
        try:
            print(f"Отправка в {topic}: key={key}, value={value}")
            await self._producer.send_and_wait(topic, key=key, value=value)
            print(f"Сообщение успешно отправлено в {topic}")
            await self._producer.commit_transaction()
            print(f"Транзакция для {topic} зафиксирована")
        except Exception as err:
            print(f"Ошибка при отправке в {topic}: {err}")
            await self._producer.abort_transaction()
            raise
