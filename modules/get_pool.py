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

    # Убедись, что токены отсортированы (token0 < token1 по адресу)
    token1, token2 = sorted([client.token1, client.token2], key=lambda x: x.lower())

    factory = await client.get_contract(contract_address=UNISWAP_V3_FACTORY, abi=UNISWAP_V3_FACTORY_ABI)
    for fee in range(100, 501, 100):
        pool_address = await factory.functions.getPool(token1, token2, fee).call()
        if pool_address != "0x0000000000000000000000000000000000000000":
            return pool_address


