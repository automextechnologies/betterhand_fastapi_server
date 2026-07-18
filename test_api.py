import urllib.request
import json

def test_api():
    try:
        url = "http://localhost:8000/admin/debug/ward-search?state=Kerala&district=Malappuram&local_body_name=valanchery&ward_number=6"
        print("Fetching:", url)
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            print(json.dumps(data, indent=2))
    except Exception as e:
        print("Error fetching debug url:", e)

if __name__ == '__main__':
    test_api()
