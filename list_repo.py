import json
import sys
import urllib.request

model = sys.argv[1]
url = f"https://modelscope.cn/api/v1/models/{model}/repo/files?Revision=master"
with urllib.request.urlopen(url) as response:
    payload = json.load(response)

files = payload.get("Data", {}).get("Files", [])
print(f"===== {model} ({len(files)} files)")
for item in files:
    size = item.get("Size", 0) or 0
    print(f"{item.get('Path')}  {size / 1048576:.1f} MB")
