import yaml

with open('configs/oto/image.yaml') as f:
    data = yaml.safe_load(f)

print(f"save_copy: {data['image']['save']['save_copy']}")
print(f"save_meta: {data['image']['meta']['save_meta']}")
