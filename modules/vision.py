from PIL import Image

def describe_frames(images, blip_processor, blip_model, device):
    """BLIP 画面描述"""
    captions = []
    for img_path in images:
        image = Image.open(img_path).convert("RGB")
        inputs = blip_processor(image, return_tensors="pt").to(device)
        out_ids = blip_model.generate(**inputs)
        caption = blip_processor.decode(out_ids[0], skip_special_tokens=True)
        captions.append(caption)
    return captions