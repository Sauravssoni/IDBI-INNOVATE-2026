import httpx

c = httpx.Client()
c.cookies.set("vyapar_session", "test")
print(c.cookies)
