from config.configvalidator import ConfigValidator
from client.client import Client
from utils.logger import logger
from modules.monitor import listen_to_swaps
import asyncio
import json
import sys


async def main():
    try:
        logger.info("🚀 Запуск скрипта мониторинга Uniswap V3...\n")
        # Загрузка параметров
        logger.info("⚙️ Загрузка и валидация параметров...\n")
        validator = ConfigValidator("config/settings.json")
        settings = await validator.validate_config()

        try:
            with open("constants/networks_data.json", "r", encoding="utf-8") as file:
                networks_data = json.load(file)
        except FileNotFoundError:
            logger.error("❌ Файл networks_data.json не найден!")
            return
        except json.JSONDecodeError:
            logger.error("❌ Ошибка формата JSON в файле networks_data.json!")
            return

        if settings["network"] not in networks_data:
            logger.error(f"❌ Сеть {settings['network']} не найдена в networks_data.json!")
            return

        network = networks_data[settings["network"]]

        # Проверка RPC URL
        if not network["rpc_url"] or not network["rpc_url"].startswith("ws"):
            logger.error("❌ RPC URL не указан или не является WebSocket (должен начинаться с ws:// или wss://)!")
            logger.info("⚠️ Для работы мониторинга нужно указать WebSocket URL в файле constants/networks_data.json")
            return

        # Инициализация клиента
        logger.info("⚙️ Инициализация Web3 клиента...\n")
        client = Client(
            proxy=settings["proxy"],
            rpc_url=network["rpc_url"],
            chain_id=network["chain_id"],
            token1=network[settings["token1"]],
            token2=network[settings["token2"]],
            explorer_url=network["explorer_url"]
        )

        # Запуск мониторинга
        logger.info("🔍 Запускаем мониторинг пула Uniswap V3...\n")
        logger.info(f"📊 Мониторинг пары {settings['token1']}/{settings['token2']} в сети {settings['network']}\n")
        
        await listen_to_swaps(client)
        logger.info("⚙️ Завершение работы...\n")
    except KeyboardInterrupt:
        logger.info("🛑 Остановка по Ctrl+C")
    except Exception as e:
        logger.error(f"❌ Произошла ошибка в основном пути: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
