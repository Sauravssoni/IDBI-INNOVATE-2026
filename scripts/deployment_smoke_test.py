import urllib.request
import urllib.error
import json
import sys
import os

def check_backend(url):
    try:
        req = urllib.request.Request(f"{url}/health")
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print(f"❌ Backend health returned {response.status}")
                return False
            data = json.loads(response.read().decode())
            if data.get("status") != "ok":
                print(f"❌ Backend not healthy: {data}")
                return False
            print("✅ Backend health check passed.")
            return True
    except Exception as e:
        print(f"❌ Backend health check failed: {e}")
        return False

def check_frontend(url):
    import time
    for i in range(10):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    print(f"❌ Frontend returned {response.status}")
                    return False
                print("✅ Frontend health check passed.")
                return True
        except Exception as e:
            print(f"Frontend health check failed (attempt {i+1}/10): {e}")
            time.sleep(5)
    print("❌ Frontend health check ultimately failed.")
    return False

def run():
    target_api = os.environ.get("TARGET_API", "http://localhost:8000")
    target_frontend = os.environ.get("TARGET_FRONTEND", "http://localhost:3005")
    print(f"Running Deployment Smoke Test against {target_api} and {target_frontend}...")
    backend_ok = check_backend(target_api)
    frontend_ok = check_frontend(target_frontend)
    
    if backend_ok and frontend_ok:
        print("✅ Smoke test PASSED")
        sys.exit(0)
    else:
        print("❌ Smoke test FAILED")
        sys.exit(1)

if __name__ == "__main__":
    run()
