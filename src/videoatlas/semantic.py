"""Offline CLIP scene embeddings. Models must already exist on disk."""
import json
from pathlib import Path


def load_model(directory):
    from transformers import CLIPModel, CLIPProcessor
    import torch
    directory = str(Path(directory).resolve())
    if not Path(directory, 'config.json').is_file():
        raise FileNotFoundError('Select a complete local CLIP model folder (config.json missing)')
    model = CLIPModel.from_pretrained(directory, local_files_only=True).eval()
    processor = CLIPProcessor.from_pretrained(directory, local_files_only=True)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    return model.to(device), processor, device


def encode_images(model, processor, device, paths):
    import torch
    from PIL import Image
    with torch.inference_mode():
        with_images = []
        for path in paths:
            with Image.open(path) as im:
                with_images.append(im.convert('RGB').copy())
        inputs = processor(images=with_images, return_tensors='pt', padding=True)
        features = model.get_image_features(**{k: v.to(device) for k,v in inputs.items()})
        if not isinstance(features, torch.Tensor):
            features = features.pooler_output
        features = torch.nn.functional.normalize(features, dim=-1)
        return features.cpu().tolist()


def encode_text(model, processor, device, query):
    import torch
    with torch.inference_mode():
        inputs = processor(text=[query], return_tensors='pt', padding=True, truncation=True)
        features = model.get_text_features(**{k:v.to(device) for k,v in inputs.items()})
        if not isinstance(features, torch.Tensor):
            features = features.pooler_output
        return torch.nn.functional.normalize(features, dim=-1)[0].cpu().tolist()


def index_video(db, video_id, video_path, cache, model_directory):
    from .analysis import frame
    model, processor, device = load_model(model_directory)
    scenes = db.get_scenes(video_id)
    times = [float(s['seconds']) for s in scenes] if scenes else []
    if not times:
        video = db.conn.execute('SELECT duration FROM videos WHERE id=?', (video_id,)).fetchone()
        duration = float(video['duration'] or 0)
        times = [max(0, duration*f) for f in (.1,.3,.5,.7,.9)] if duration else [0]
    # Bound each video to a reasonable sample count. Further scenes can be processed in a later pass.
    if len(times)>200:
        stride = max(1, len(times)//200)
        times=times[::stride][:200]
    folder = Path(cache)/'semantic'/str(video_id)
    folder.mkdir(parents=True,exist_ok=True)
    results=[]
    for index,second in enumerate(times):
        image_path=folder/f'{index:05d}.jpg'
        try:
            frame(video_path,second,image_path,384)
            results.append((second,str(image_path)))
        except Exception:
            continue
    if not results:
        raise RuntimeError('No frames extracted for semantic indexing')
    model_id=str(Path(model_directory).resolve())
    # Batch frames to avoid allocating the entire collection in GPU memory.
    with db.conn:
        db.conn.execute('DELETE FROM semantic_frames WHERE video_id=? AND model_id=?',(video_id,model_id))
        for start in range(0,len(results),8):
            batch=results[start:start+8]
            vectors=encode_images(model,processor,device,[p for _,p in batch])
            db.conn.executemany('''INSERT INTO semantic_frames(video_id,seconds,thumbnail,model_id,vector)
               VALUES(?,?,?,?,?)''',[(video_id,t,p,model_id,json.dumps(v)) for (t,p),v in zip(batch,vectors)])
    return len(results)


def search(db, query, model_directory, limit=30):
    import heapq
    model, processor, device=load_model(model_directory)
    target=encode_text(model,processor,device,query)
    model_id=str(Path(model_directory).resolve())
    from .vector_index import search_hnsw
    approximate = search_hnsw(db, model_id, target, limit)
    if approximate is not None:
        return approximate
    best=[]
    rows=db.conn.execute('''SELECT f.video_id,f.seconds,f.thumbnail,f.vector,v.name,v.path
       FROM semantic_frames f JOIN videos v ON v.id=f.video_id WHERE f.model_id=?''',(model_id,))
    for row in rows:
        vector=json.loads(row['vector'])
        score=sum(a*b for a,b in zip(target,vector))
        item=(score,int(row['video_id']),float(row['seconds']),row['name'],row['path'],row['thumbnail'])
        if len(best)<limit: heapq.heappush(best,item)
        elif score>best[0][0]:heapq.heapreplace(best,item)
    return sorted(best,reverse=True)
