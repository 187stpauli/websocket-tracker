import aiohttp
from eth_abi import decode_abi
from modules.get_pool import get_uniswap_v3_pool
import json
from eth_utils import to_checksum_address, decode_hex

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


async def listen_to_swaps(client):
    swap_topic = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
    pool = await get_uniswap_v3_pool(client)

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(client.rpc_url) as ws:
            # Отправка подписки
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_subscribe",
                "params": [
                    "logs",
                    {
                        "address": pool,
                        "topics": [[swap_topic]]
                    }
                ]
            }
            await ws.send_str(json.dumps(payload))
            print("🔌 Подписка на Swap отправлена...\n")

            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if "params" in data:
                        try:
                            log = data["params"]["result"]
                            decoded = decode_swap_event(log, swap_topic)
                            print("✅ Swap Event:")
                            for k, v in decoded.items():
                                print(f"  {k}: {v}")
                            print()
                        except Exception as e:
                            print(f"⚠️ Ошибка декодирования: {e}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f"❌ WebSocket ошибка: {msg.data}")
                    break
