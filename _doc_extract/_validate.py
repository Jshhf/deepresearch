import yaml, sys, io, os, py_compile

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "deep_research"))
files = ["docker-compose.yml", "docker-compose.infrastructure.yml"]
ok = True
for f in files:
    with io.open(root + "\\" + f, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    services = data.get("services", {})
    print(f, "-> services:", sorted(services.keys()))
    for name, svc in services.items():
        img = svc.get("image")
        build = svc.get("build")
        if build:
            print("   ", name, "build:", build.get("context"), "/", build.get("dockerfile"))
        if img:
            print("   ", name, "image:", img)

print("--- py_compile ingest.py ---")
py_compile.compile(root + r"\app\mult_agents\rag\ingest.py", doraise=True)
print("ingest.py compile OK")
