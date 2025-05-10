from eth_abi import decode_abi
from web3 import Web3
import logging

logger = logging.getLogger(__name__)

SWAP_TOPIC = "0x783cca1c0412dd0d695e784568d7c5edf5b509b5c8c6c33c1c3fef6aef7e623c"
MINT_TOPIC = "0x9f679b1155ef32ca4e7724a797156521ced63d40c5d9fdcf7c6c2e6dc3e3a002"
BURN_TOPIC = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"


def decode_int24(value) -> int:
    if isinstance(value, str) and value.startswith("0x"):
        raw = bytes.fromhex(value[2:])
    elif isinstance(value, bytes):
        raw = value
    else:
        raise ValueError("Unsupported type for int24 decoding")

    if len(raw) >= 3:
        raw = raw[-3:]
    else:
        raise ValueError("Недостаточно байт для int24")

    return int.from_bytes(raw, byteorder='big', signed=True)


def decode_int24_from_abi_slot(slot: bytes) -> int:
    if len(slot) != 32:
        raise ValueError("ABI slot должен быть 32 байта")
    return int.from_bytes(slot[29:], byteorder='big', signed=True)


def decode_uniswap_v3_event(raw_log: dict):
    topic0 = raw_log['topics'][0].lower()
    data = raw_log['data']
    address = Web3.to_checksum_address(raw_log['address'])

    if topic0 == BURN_TOPIC:
        logger.info("🔥 Обрабатывается событие BURN")

        try:
            topics = raw_log['topics']
            if len(topics) < 3:
                logger.warning("⚠️ Слишком мало topics (%d) — пропуск", len(topics))
                return None

            owner = Web3.to_checksum_address("0x" + topics[1][-40:])
            tick_lower = decode_int24(topics[2])

            if len(topics) >= 4:
                tick_upper = decode_int24(topics[3])
                event_type = "полный"
            else:
                tick_upper = None
                event_type = "усечённый"

            raw_data = bytes.fromhex(data[2:])
            if len(raw_data) != 96:
                logger.warning("⚠️ Неправильная длина raw_data (%d байт) для BURN", len(raw_data))
                return None

            amount, amount0, amount1 = decode_abi(
                ['uint128', 'uint256', 'uint256'],
                raw_data
            )

            logger.info("🧯 [СЖИГАНИЕ] Пул: %s", address)
            logger.info("👤 Владелец: %s", owner)
            logger.info("🧭 Диапазон тиков: %s → %s", tick_lower,
                        tick_upper if tick_upper is not None else "(неизвестен)")
            logger.info("💧 Кол-во: %s", amount)
            logger.info("💰 Токен0: %s | Токен1: %s", amount0, amount1)

            return {
                "событие": "Сжигание",
                "тип_события": event_type,
                "владелец": owner,
                "тик_нижний": tick_lower,
                "тик_верхний": tick_upper,
                "количество": amount,
                "токен0": amount0,
                "токен1": amount1
            }

        except Exception as e:
            logger.error("❌ Ошибка при обработке BURN: %s", e)
            return None

    elif topic0 == MINT_TOPIC:
        logger.info("🪙 Обрабатывается событие MINT")
        try:
            topics = raw_log['topics']
            if len(topics) < 4:
                logger.warning("⚠️ Недостаточно topics (%d) для события MINT", len(topics))
                return None

            sender = Web3.to_checksum_address("0x" + topics[1][-40:])
            owner = Web3.to_checksum_address("0x" + topics[2][-40:])
            tick_lower = decode_int24(topics[3])
            raw_data = bytes.fromhex(data[2:])

            if len(raw_data) != 128:
                logger.warning("⚠️ Неправильная длина raw_data (%d байт) для MINT", len(raw_data))
                return None

            tick_upper = decode_int24_from_abi_slot(raw_data[0:32])
            rest_data = raw_data[32:]
            amount, amount0, amount1 = decode_abi(
                ['uint128', 'uint256', 'uint256'],
                rest_data
            )

            logger.info("🪙 [МИНТ] Пул: %s", address)
            logger.info("👤 Отправитель: %s → Владелец: %s", sender, owner)
            logger.info("🧭 Диапазон тиков: %s → %s", tick_lower, tick_upper)
            logger.info("💧 Кол-во: %s", amount)
            logger.info("💰 Токен0: %s | Токен1: %s", amount0, amount1)

            return {
                "событие": "Минт",
                "тип_события": "полный",
                "отправитель": sender,
                "владелец": owner,
                "тик_нижний": tick_lower,
                "тик_верхний": tick_upper,
                "количество": amount,
                "токен0": amount0,
                "токен1": amount1
            }

        except Exception as e:
            logger.error("❌ Ошибка при обработке MINT: %s", e)
            return None

    elif topic0 == SWAP_TOPIC:
        logger.info("🔄 Обрабатывается событие SWAP")

        try:
            topics = raw_log['topics']
            if len(topics) < 3:
                logger.warning("⚠️ Недостаточно topics (%d) для события SWAP", len(topics))
                return None

            sender = Web3.to_checksum_address("0x" + topics[1][-40:])
            recipient = Web3.to_checksum_address("0x" + topics[2][-40:])
            raw_data = bytes.fromhex(data[2:])

            if len(raw_data) != 160:
                logger.warning("⚠️ Неправильная длина raw_data (%d байт) для SWAP", len(raw_data))
                return None

            tick_raw = raw_data[-32:]
            tick = decode_int24_from_abi_slot(tick_raw)
            rest_data = raw_data[:-32]
            amount0, amount1, sqrtPriceX96, liquidity = decode_abi(
                ['int256', 'int256', 'uint160', 'uint128'],
                rest_data
            )

            logger.info("🔄 [ОБМЕН] Пул: %s", address)
            logger.info("👤 Отправитель: %s → Получатель: %s", sender, recipient)
            logger.info("💱 Сумма: amount0 = %s, amount1 = %s", amount0, amount1)
            logger.info("📊 sqrtPriceX96: %s | ликвидность: %s | тик: %s", sqrtPriceX96, liquidity, tick)

            return {
                "событие": "Обмен",
                "тип_события": "полный",
                "отправитель": sender,
                "получатель": recipient,
                "amount0": amount0,
                "amount1": amount1,
                "sqrtPriceX96": sqrtPriceX96,
                "ликвидность": liquidity,
                "тик": tick
            }

        except Exception as e:
            logger.error("❌ Ошибка при обработке SWAP: %s", e)
            return None


    else:
        logger.warning("❓ Неизвестное событие с topic0: %s", topic0)

    return None
