from kavenegar import KavenegarAPI
import random

# ✅ Your Kavenegar API key
API_KEY = "6B78587A63766E58546B554549305A71685276414E5950506D687454776B43624744666C34647A6D3042593D"
SENDER = "2000660110"


def generate_otp():
    return str(random.randint(100000, 999999))


def main():
    phone = input("Enter phone number (e.g. 09123456789): ").strip()
    otp = generate_otp()

    api = KavenegarAPI(API_KEY)

    params = {
        "sender": SENDER,
        "receptor": phone,
        "message": f"کد ورود MYFITA: {otp}",
    }

    response = api.sms_send(params)

    print("✅ OTP sent successfully")
    print("OTP (for dev):", otp)
    print(response)


if __name__ == "__main__":
    main()