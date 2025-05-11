import aiohttp
from eth_abi import decode_abi
from modules.get_pool import get_uniswap_v3_pool
import json
from eth_utils import to_checksum_address, decode_hex
import asyncio
from utils.data_saver import DataSaver

with open("abi/pool_abi.json", "r", encoding="utf-8") as f:
    POOL_ABI = json.load(f)


def decode_swap_event(log: dict, swap_topic) -> dict:
    if log["topics"][0].lower() != swap_topic:
        raise ValueError("❌ Это не Swap событие")

    sender = to_checksum_address("0x" + log["topics"][1][-40:])
    recipient = to_checksum_address("0x" + log["topics"][2][-40:])
    data = decode_hex(log["data"])

    amount0, amount1, sqrtPriceX96, liquidity, tick_bytes = decode_abi(
        ["int256", "int256", "uint160", "uint128", "bytes32"], data
    )

    # int24 занимает последние 3 байта
    tick = int.from_bytes(tick_bytes[-3:], byteorder="big", signed=True)

    return {
        "event": "Swap",
        "sender": sender,
        "recipient": recipient,
        "amount0": amount0,
        "amount1": amount1,
        "sqrtPriceX96": sqrtPriceX96,
        "liquidity": liquidity,
        "tick": tick
    }


def decode_mint_event(log: dict, mint_topic) -> dict:
    if log["topics"][0].lower() != mint_topic:
        raise ValueError("❌ Это не Mint событие")

    sender = to_checksum_address("0x" + log["topics"][1][-40:])
    owner = to_checksum_address("0x" + log["topics"][2][-40:])
    data = decode_hex(log["data"])

    tickLower, tickUpper, amount, amount0, amount1 = decode_abi(
        ["int24", "int24", "uint128", "uint256", "uint256"], data
    )

    return {
        "event": "Mint",
        "sender": sender,
        "owner": owner,
        "tickLower": tickLower,
        "tickUpper": tickUpper,
        "amount": amount,
        "amount0": amount0,
        "amount1": amount1
    }


def decode_burn_event(log: dict, burn_topic) -> dict:
    if log["topics"][0].lower() != burn_topic:
        raise ValueError("❌ Это не Burn событие")

    owner = to_checksum_address("0x" + log["topics"][1][-40:])
    data = decode_hex(log["data"])

    tickLower, tickUpper, amount, amount0, amount1 = decode_abi(
        ["int24", "int24", "uint128", "uint256", "uint256"], data
    )

    return {
        "event": "Burn",
        "owner": owner,
        "tickLower": tickLower,
        "tickUpper": tickUpper,
        "amount": amount,
        "amount0": amount0,
        "amount1": amount1
    }


async def get_token_info(client, token_address):
    contract = await client.get_contract(token_address, client.w3.eth.contract_factory.contractFactories["ERC20"].abi)
    symbol = await contract.functions.symbol().call()
    decimals = await contract.functions.decimals().call()
    return {
        "address": token_address,
        "symbol": symbol,
        "decimals": decimals
    }


async def listen_to_swaps(client):
    # События для мониторинга
    swap_topic = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
    mint_topic = "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde"
    burn_topic = "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c"
    
    pool = await get_uniswap_v3_pool(client)
    
    # Инициализируем сохранение данных
    data_saver = DataSaver()
    
    # Получаем информацию о токенах для форматирования
    try:
        token0_info = await get_token_info(client, client.token1)
        token1_info = await get_token_info(client, client.token2)
        print(f"🔍 Токены пула: {token0_info['symbol']} / {token1_info['symbol']}")
    except Exception as e:
        print(f"⚠️ Не удалось получить информацию о токенах: {e}")
        token0_info = {"symbol": "Token0", "decimals": 18}
        token1_info = {"symbol": "Token1", "decimals": 18}
    
    # Добавить обработку переподключения
    reconnect_attempts = 0
    max_reconnect_attempts = 5
    
    while reconnect_attempts < max_reconnect_attempts:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(client.rpc_url) as ws:
                    # Отправка подписки на несколько событий
                    payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_subscribe",
                        "params": [
                            "logs",
                            {
                                "address": pool,
                                "topics": [[swap_topic, mint_topic, burn_topic]]
                            }
                        ]
                    }
                    await ws.send_str(json.dumps(payload))
                    print("🔌 Подписка на события пула отправлена...\n")
                    
                    # Сбрасываем счетчик переподключений при успешной подписке
                    reconnect_attempts = 0

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if "params" in data:
                                try:
                                    log = data["params"]["result"]
                                    event_topic = log["topics"][0].lower()
                                    
                                    if event_topic == swap_topic:
                                        decoded = decode_swap_event(log, swap_topic)
                                        
                                        # Конвертируем в понятный формат
                                        amount0_formatted = decoded['amount0'] / (10 ** token0_info['decimals'])
                                        amount1_formatted = decoded['amount1'] / (10 ** token1_info['decimals'])
                                        
                                        print("✅ Swap Event:")
                                        print(f"  Sender: {decoded['sender']}")
                                        print(f"  Recipient: {decoded['recipient']}")
                                        print(f"  {token0_info['symbol']}: {amount0_formatted:.6f}")
                                        print(f"  {token1_info['symbol']}: {amount1_formatted:.6f}")
                                        
                                        # Вычисление цены
                                        if decoded['amount0'] != 0 and decoded['amount1'] != 0:
                                            price = abs(amount1_formatted / amount0_formatted)
                                            print(f"  Price: 1 {token0_info['symbol']} = {price:.6f} {token1_info['symbol']}")
                                        
                                        # Сохраняем данные
                                        data_saver.save_swap_data(decoded)
                                        
                                    elif event_topic == mint_topic:
                                        decoded = decode_mint_event(log, mint_topic)
                                        
                                        # Конвертируем в понятный формат
                                        amount0_formatted = decoded['amount0'] / (10 ** token0_info['decimals'])
                                        amount1_formatted = decoded['amount1'] / (10 ** token1_info['decimals'])
                                        
                                        print("🟢 Mint Event:")
                                        print(f"  Sender: {decoded['sender']}")
                                        print(f"  Owner: {decoded['owner']}")
                                        print(f"  {token0_info['symbol']}: {amount0_formatted:.6f}")
                                        print(f"  {token1_info['symbol']}: {amount1_formatted:.6f}")
                                        print(f"  Tick Range: {decoded['tickLower']} to {decoded['tickUpper']}")
                                        
                                    elif event_topic == burn_topic:
                                        decoded = decode_burn_event(log, burn_topic)
                                        
                                        # Конвертируем в понятный формат
                                        amount0_formatted = decoded['amount0'] / (10 ** token0_info['decimals'])
                                        amount1_formatted = decoded['amount1'] / (10 ** token1_info['decimals'])
                                        
                                        print("🔴 Burn Event:")
                                        print(f"  Owner: {decoded['owner']}")
                                        print(f"  {token0_info['symbol']}: {amount0_formatted:.6f}")
                                        print(f"  {token1_info['symbol']}: {amount1_formatted:.6f}")
                                        print(f"  Tick Range: {decoded['tickLower']} to {decoded['tickUpper']}")
                                    
                                    print()
                                except Exception as e:
                                    print(f"⚠️ Ошибка декодирования: {e}")
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print(f"❌ WebSocket ошибка: {msg.data}")
                            break
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            print("❌ WebSocket соединение закрыто")
                            break
                            
        except aiohttp.ClientConnectionError as e:
            reconnect_attempts += 1
            wait_time = 2 ** reconnect_attempts  # Экспоненциальная задержка
            print(f"⚠️ Ошибка соединения: {e}. Попытка переподключения {reconnect_attempts}/{max_reconnect_attempts} через {wait_time} сек")
            await asyncio.sleep(wait_time)
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            break
    
    if reconnect_attempts >= max_reconnect_attempts:
        print("❌ Превышено максимальное количество попыток переподключения")
