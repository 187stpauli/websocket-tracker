from config.configvalidator import ConfigValidator
from client.client import Client
from utils.logger import logger
from modules.monitor import listen_to_swaps
import asyncio
import json


async def main():
    try:
        logger.info("🚀 Запуск скрипта...\n")
        # Загрузка параметров
        logger.info("⚙️ Загрузка и валидация параметров...\n")
        validator = ConfigValidator("config/settings.json")
        settings = await validator.validate_config()

        with open("constants/networks_data.json", "r", encoding="utf-8") as file:
            networks_data = json.load(file)

        network = networks_data[settings["network"]]

        # Инициализация клиента
        client = Client(
            proxy=settings["proxy"],
            rpc_url=network["rpc_url"],
            chain_id=network["chain_id"],
            token1=network[settings["token1"]],
            token2=network[settings["token2"]],
            explorer_url=network["explorer_url"]
        )

        # Запуск мониторинга
        logger.info("⚙️ Запускаем мониторинг...\n")
        await listen_to_swaps(client)
        logger.info("⚙️ Завершение работы...\n")
    except Exception as e:
        logger.error(f"Произошла ошибка в основном пути: {e}")
    except KeyboardInterrupt:
        print("🛑 Остановка по Ctrl+C")


if __name__ == "__main__":
    asyncio.run(main())
