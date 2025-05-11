from eth_utils import keccak


async def print_all_event_topic0(abi: list):
    print("🧾 Список событий и их topic0:\n")
    for entry in abi:
        if entry.get("type") == "event":
            name = entry["name"]
            types = [inp["type"] for inp in entry["inputs"]]
            signature = f"{name}({','.join(types)})"
            topic0 = "0x" + keccak(text=signature).hex()
            print(f"📌 {name.ljust(20)} → {signature}")
            print(f"   topic0: {topic0}\n")