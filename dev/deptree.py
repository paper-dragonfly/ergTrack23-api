import json

with open("deptree.json", "r") as f:
    file = json.load(f)

top_packs = []
for d in file:
    top_packs.append((f'{d["package_name"]}=={d["required_version"]}'))
for p in top_packs:
    print(p)

print(len(top_packs))
