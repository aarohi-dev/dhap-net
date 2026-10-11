from huggingface_hub import HfFileSystem
fs = HfFileSystem()
files = fs.ls('datasets/Taqui/lanl-cyber-datasets/lanl-2015', detail=True)
for f in files:
    size = f.get('size', 0) or 0
    name = f['name'].split('/')[-1]
    gb = size/1e9
    print(f"{name:30s}  {gb:.3f} GB  ({size} bytes)")
