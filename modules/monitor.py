import aiohttp
from aiohttp import WSMessage
from web3 import AsyncWeb3, WebsocketProviderV2
from web3.datastructures import AttributeDict
from modules.decoder import decode_uniswap_v3_event
from modules.get_pool import get_uniswap_v3_pool
from client.client import Client
from utils.logger import logger
import json

with open("abi/pool_abi.json", "r", encoding="utf-8") as f:
    POOL_ABI = json.load(f)


async def decode_tx_data(client, tx_data, pool):
    contract = await client.get_contract(pool, POOL_ABI)
    try:
        function_abi = contract.decode_function_input(tx_data)
        logger.info(f"Успешно декодировал данные. Функция {function_abi[0]}, аргументы {function_abi[1]}\n")
    except Exception as e:
        logger.error(f'Ошибка декодирования {e}\n')


async def enable_monitoring(client: Client):
    swap_topic = "0x783cca1c0412dd0d695e784568d7c5edf5b509b5c8c6c33c1c3fef6aef7e623c"
    mint_topic = "0x9f679b1155ef32ca4e7724a797156521ced63d40c5d9fdcf7c6c2e6dc3e3a002"
    burn_topic = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
    topics = [[swap_topic, mint_topic, burn_topic]]
    pool = await get_uniswap_v3_pool(client)

    async with AsyncWeb3.persistent_websocket(WebsocketProviderV2(client.rpc_url)) as w3:

        subscription_id = await w3.eth.subscribe("logs", {"address": pool})

        logger.info("🔌 Подписка отправлена\n")

        try:
            while True:
                msg = await w3.provider._ws_recv()
                data = msg
                params = data.get("params")
                if params:
                    result = params.get("result")
                    if result["address"] == pool.lower():
                        logger.info(f"Найдена транзакция от адреса {pool}")
                        tx_data = result["data"]
                        if tx_data:
                            await decode_tx_data(client, tx_data, pool)
                            logger.info(f"Пытаюсь декодировать транзакцию {tx_data}")
                logger.info(f"📩 Новое сообщение: {data}")

        except Exception as e:
            logger.error(f"Ошибка при прослушивании сокета: {e}")
