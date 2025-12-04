from app import main

for r in main.app.router.routes:
    path = getattr(r, 'path', None)
    methods = getattr(r, 'methods', None)
    name = getattr(r, 'name', None)
    print(f"{path} {methods} -> {name}")
