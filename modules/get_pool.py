from client.client import Client

UNISWAP_V3_FACTORY = "0x1F98431c8aD98523631AE4a59f267346ea31F984"

UNISWAP_V3_FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"}
        ],
        "name": "getPool",
        "outputs": [{"internalType": "address", "name": "pool", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]


async def get_uniswap_v3_pool(client: Client):
    """
    Получает адрес пула Uniswap V3 для указанной пары токенов.
    Проверяет все доступные fee tiers: 0.01%, 0.05%, 0.3%, 1%
    """
    # Убедись, что токены отсортированы (token0 < token1 по адресу)
    token1, token2 = sorted([client.token1, client.token2], key=lambda x: x.lower())

    factory = await client.get_contract(contract_address=UNISWAP_V3_FACTORY, abi=UNISWAP_V3_FACTORY_ABI)
    
    # Стандартные fee tiers в Uniswap V3
    fee_tiers = [100, 500, 3000, 10000]  # 0.01%, 0.05%, 0.3%, 1%
    
    found_pools = []
    
    # Проверяем все fee tiers
    for fee in fee_tiers:
        try:
            pool_address = await factory.functions.getPool(token1, token2, fee).call()
            if pool_address != "0x0000000000000000000000000000000000000000":
                fee_percent = fee / 10000
                print(f"🔍 Найден пул с комиссией {fee_percent}%: {pool_address}")
                found_pools.append((pool_address, fee))
        except Exception as e:
            print(f"⚠️ Ошибка при проверке пула с fee={fee}: {e}")
    
    if not found_pools:
        raise ValueError(f"❌ Пул для пары {token1}/{token2} не найден ни с одним значением комиссии")
    
    # Возвращаем адрес пула с самой высокой ликвидностью (обычно это пул с fee=3000)
    # Если есть пул с fee=3000, возвращаем его
    for pool_address, fee in found_pools:
        if fee == 3000:
            return pool_address
    
    # Иначе возвращаем первый найденный пул
    return found_pools[0][0]


