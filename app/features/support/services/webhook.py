from datetime import datetime, timezone

import httpx


async def send_contact_webhook(
    name: str,
    email: str,
    message: str,
    user_id: str | None = None,
    submitted_at: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    page: str | None = None,
):
    """Send contact form data to Make.com webhook"""
    webhook_url = "https://hook.us2.make.com/3i3zegehnmdiivhtnoi4r7sxma22y44z"

    payload = {
        "name": name,
        "email": email,
        "message": message,
        "userId": user_id or "",
        "submittedAt": submitted_at or datetime.now(timezone.utc).isoformat(),
    }

    # Add optional fields if available
    if category:
        payload["category"] = category
    if priority:
        payload["priority"] = priority
    if page:
        payload["page"] = page

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook_url, json=payload, headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            if response.status_code != 200:
                print(f"Make.com webhook returned {response.status_code}: {response.text}")

            response.raise_for_status()
            print(f"Successfully sent to Make.com webhook: {payload}")

    except Exception as e:
        # Log error but don't fail the request
        print(f"Failed to send webhook to Make.com: {e}")
