import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

client_twilio = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)


def send_whatsapp(body, to_number=None):
    to_number = to_number or os.getenv("MY_WHATSAPP_NUMBER")

    message = client_twilio.messages.create(
        from_=os.getenv("TWILIO_WHATSAPP_FROM"),
        to=to_number,
        body=body
    )

    return message.sid


if __name__ == "__main__":
    test_message = "בדיקה: הצינור עובד. ההכנסות צמחו ב-18% ביחס לשנה שעברה."

    sid = send_whatsapp(test_message)

    print(f"Message sent. SID: {sid}")