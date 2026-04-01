import json

from channels.generic.websocket import AsyncWebsocketConsumer

class CompanyLiveTrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.company_id = self.scope["url_route"]["kwargs"]["company_id"]
        company_id_str = str(self.company_id)
        user = self.scope.get("user")
        payload = self.scope.get("token_payload", {}) or {}
        token_company_id = str(payload.get("company_id") or "")

        if not user or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return

        user_company_id = str(getattr(user, "company_id", "") or "")
        if token_company_id and token_company_id != company_id_str:
            await self.close(code=4403)
            return
        if user_company_id and user_company_id != company_id_str:
            await self.close(code=4403)
            return

        self.group_name = f"live_tracking_company_{self.company_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def live_location_update(self, event):
        await self.send(text_data=json.dumps(event.get("payload", {})))
