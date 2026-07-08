import asyncio
import httpx

async def main():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        # Log in
        login_res = await client.post("/api/auth/login/", json={
            "email": "hospital_test@betterhand.org",
            "password": "password123"
        })
        print(f"Login status: {login_res.status_code}")
        login_data = login_res.json()
        token = login_data.get("access_token") or login_data.get("access")
        print(f"Token: {token[:15]}..." if token else "No token")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get dashboard
        dash_res = await client.get("/api/donation/dashboard/", headers=headers)
        print(f"Dashboard status: {dash_res.status_code}")
        print("Dashboard JSON response:")
        import json
        print(json.dumps(dash_res.json(), indent=2))
        
        # Get requests
        req_res = await client.get("/api/donation/requests/hospital/", headers=headers)
        print(f"\nRequests list status: {req_res.status_code}")
        print("Requests list response:")
        print(json.dumps(req_res.json(), indent=2))

if __name__ == '__main__':
    asyncio.run(main())
