import httpx

STATUS_COLORS = {"up": 0x2ECC71, "down": 0xE74C3C}


async def send(config: dict, *, title: str, description: str, status: str) -> None:
    webhook_url: str = config["webhook_url"]
    payload = {
        "embeds": [
            {
                "title": title,
                "description": description,
                "color": STATUS_COLORS.get(status, 0x95A5A6),
            }
        ]
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(webhook_url, json=payload)
        response.raise_for_status()
