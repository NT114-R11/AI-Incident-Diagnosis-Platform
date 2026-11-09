from pydantic import BaseModel, ConfigDict


class WebhookBase(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)