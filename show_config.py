import json
import sys
import urllib.request

for model in ("fishaudio/fish-speech-1.5", "fishaudio/openaudio-s1-mini"):
    url = (
        f"https://modelscope.cn/api/v1/models/{model}/repo"
        f"?Revision=master&FilePath=config.json"
    )
    print(f"===== {model}")
    try:
        with urllib.request.urlopen(url) as response:
            data = json.load(response)
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2500])
    except Exception as exc:  # noqa: BLE001
        print("failed:", exc)
