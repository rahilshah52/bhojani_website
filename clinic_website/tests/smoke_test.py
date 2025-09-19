import requests

def check(url):
    try:
        r = requests.get(url, timeout=5)
        return (url, r.status_code)
    except Exception as e:
        return (url, str(e))

if __name__ == '__main__':
    base = 'http://127.0.0.1:5000'
    paths = ['/', '/about', '/services', '/testimonials', '/login']
    for p in paths:
        print(check(base + p))
