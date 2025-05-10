from dotenv import load_dotenv
import requests
import logging
import json
import os
import re

logger = logging.getLogger(__name__)
load_dotenv(dotenv_path=".env")


class ConfigValidator:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config_data = self.load_config()

    def load_config(self) -> dict:
        """Загружает конфигурационный файл"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            logging.error(f"❗️ Файл конфигурации {self.config_path} не найден.")
            exit(1)
        except json.JSONDecodeError:
            logging.error(f"❗️ Ошибка разбора JSON в файле конфигурации {self.config_path}.")
            exit(1)

    @staticmethod
    async def resolve_proxy(proxy: str) -> str:

        if proxy.startswith("ENV:"):
            proxy_name = proxy[4:]
            raw = os.getenv("PROXIES")
            if not raw:
                logging.error("❗️ Ошибка: переменная окружения 'PROXIES' не найдена.")
                exit(1)
            try:
                proxy_map = json.loads(raw)
            except json.JSONDecodeError:
                logging.error("❗️ Ошибка: 'PROXIES' в .env имеет некорректный JSON формат.")
                exit(1)

            if proxy_name not in proxy_map:
                logging.error(f"❗️ Ошибка: ключ '{proxy_name}' не найден в PROXIES.")
                exit(1)

            return proxy_map[proxy_name]

        return proxy

    async def validate_config(self) -> dict:
        """Валидация всех полей конфигурации"""

        await self.validate_required_keys()

        if "network" not in self.config_data:
            logging.error("❗️ Ошибка: Отсутствует 'network' в конфигурации.")
            exit(1)

        if "proxy" not in self.config_data:
            logging.error("❗️ Ошибка: Отсутствует 'proxy' в конфигурации.")
            exit(1)

        if "token1" not in self.config_data:
            logging.error("❗️ Ошибка: Отсутствует 'token1' в конфигурации.")
            exit(1)

        if "token2" not in self.config_data:
            logging.error("❗️ Ошибка: Отсутствует 'token2' в конфигурации.")
            exit(1)

        if self.config_data["token1"] == self.config_data["token2"]:
            logging.error(
                "❗️ Ошибка: Поля 'token1' и 'token2' имеют одинаковое значение, введите разные токены.")
            exit(1)

        load_dotenv(dotenv_path="../.env")

        resolved_proxy = await self.resolve_proxy(self.config_data["proxy"])
        self.config_data["proxy"] = resolved_proxy

        await self.validate_network(self.config_data["network"])
        await self.validate_proxy(self.config_data["proxy"])
        await self.validate_token1(self.config_data["token1"])
        await self.validate_token2(self.config_data["token2"])

        return self.config_data

    async def validate_required_keys(self):
        required_keys = [
            "network",
            "private_key",
            "proxy",
            "token1",
            "token2"
        ]

        for key in required_keys:
            if key not in self.config_data:
                logging.error(f"❗️ Ошибка: отсутствует обязательный ключ '{key}' в settings.json")
                exit(1)

    @staticmethod
    async def validate_token1(token: str) -> None:
        """Валидация названия токена"""
        tokens = [
            "USDC",
            "ETH"
        ]
        if token not in tokens:
            logging.error("❗️ Ошибка: Неподдерживаемый токен! Введите один из поддерживаемых токенов.")
            exit(1)

    @staticmethod
    async def validate_token2(token: str) -> None:
        """Валидация названия токена"""
        tokens = [
            "USDC",
            "ETH"
        ]
        if token not in tokens:
            logging.error("❗️ Ошибка: Неподдерживаемый токен! Введите один из поддерживаемых токенов.")
            exit(1)

    @staticmethod
    async def validate_network(network: str) -> None:
        """Валидация названия сети"""
        networks = [
            "Ethereum"
        ]
        if network not in networks:
            logging.error("❗️ Ошибка: Неподдерживаемая сеть отправления! Введите одну из поддерживаемых сетей.")
            exit(1)

    @staticmethod
    async def validate_proxy(proxy: str) -> None:
        """Валидация прокси-адреса"""
        if not proxy:
            logging.info("⚠️ Прокси не указан — пропуск валидации.\n")
            return

        pattern = r"^(?P<login>[^:@]+):(?P<password>[^:@]+)@(?P<host>[\w.-]+):(?P<port>\d+)$"
        match = re.match(pattern, proxy)
        if not match:
            logging.error("❗️ Ошибка: Неверный формат прокси! Должен быть 'login:pass@host:port'.")
            exit(1)

        proxy_url = {
            "http": f"http://{proxy}"
        }
        response = requests.get("https://httpbin.org/ip", proxies=proxy_url, timeout=5)
        if response.status_code != 200:
            logging.error("❗️ Ошибка: 'proxy' нерабочий или вернул неверный статус-код!")
            exit(1)
