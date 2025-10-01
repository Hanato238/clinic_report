import configparser
import socket

ini_path = r'C:\Users\admin\AppData\Roaming\Canfield\Sculptor.ini'

# デコード/エンコード
def decode_backslash_utf16be(s: str) -> str:
    return bytes.fromhex(s.replace("\\x", "")).decode("utf-16-be")

def encode_backslash_utf16be(s: str) -> str:
    return "".join(f"\\x{b1:02x}{b2:02x}" for b1, b2 in zip(*[iter(s.encode("utf-16-be"))]*2))

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

def main():
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(ini_path, encoding="utf-8")  # ASCII なので utf-8 で十分

    ip = get_local_ip()
    print(f"自IP: {ip}")
    config.setdefault("capture", {})["DS3Url"] = f"http://{ip}:2779/VEOSIntegration/"
    print("DS3Urlを更新しました")

    config.setdefault("global", {})["institutionName"] = encode_backslash_utf16be("髪のなやみのクリニック")
    config.setdefault("global", {})["institutionAddress"] = encode_backslash_utf16be("愛知県名古屋市田江通")
    print("クリニック情報を更新しました")

    with open(ini_path, "w", encoding="utf-8") as f:
        config.write(f)

if __name__ == "__main__":
    main()
