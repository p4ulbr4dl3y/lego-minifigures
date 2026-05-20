import os
import numpy as np
from PIL import Image, ImageOps
import mlx.core as mx
from mlx_vlm.utils import load_model, get_model_path
from mlx_vlm.models.sam3.generate import Sam3Predictor
from mlx_vlm.models.sam3.processing_sam3 import Sam3Processor

class Sam3Inference:
    def __init__(self, model_id="mlx-community/sam3-4bit", threshold=0.5):
        print(f"Загрузка модели SAM3: {model_id}...")
        model_path = get_model_path(model_id)
        sam_model = load_model(model_path)
        sam_processor = Sam3Processor.from_pretrained(str(model_path))
        self.predictor = Sam3Predictor(sam_model, sam_processor, score_threshold=threshold)
        self.prompt = "lego minifigure"

    def predict(self, image_path):
        # Применение exif_transpose для корректной обработки повернутых фотографий
        image_pil = Image.open(image_path).convert("RGB")
        image_pil = ImageOps.exif_transpose(image_pil)
        W, H = image_pil.size
        
        result = self.predictor.predict(image_pil, text_prompt=self.prompt)
        
        objects = []
        for i in range(len(result.scores)):
            mask = result.masks[i]
            score = float(result.scores[i])
            
            # Приведение маски к размеру изображения
            mh, mw = mask.shape
            if (mw, mh) != (W, H):
                mask_pil = Image.fromarray(mask.astype(np.uint8) * 255).resize((W, H), resample=Image.NEAREST)
                mask_full = np.array(mask_pil) > 0
            else:
                mask_full = mask > 0
            
            # Вычисление bbox по маске для более точного кропа
            ys, xs = np.where(mask_full)
            if len(ys) == 0:
                continue
            x1_c, y1_c = int(xs.min()), int(ys.min())
            x2_c, y2_c = int(xs.max()) + 1, int(ys.max()) + 1

            crop_pil = image_pil.crop((x1_c, y1_c, x2_c, y2_c))
            crop_np = np.array(crop_pil)
            
            # Обрезка маски по bbox
            obj_mask = mask_full[y1_c:y2_c, x1_c:x2_c]
            
            bg = np.ones_like(crop_np) * 255
            white_bg_crop_np = np.where(obj_mask[..., None], crop_np, bg)
            white_bg_crop_pil = Image.fromarray(white_bg_crop_np)

            objects.append({
                "box": [x1_c, y1_c, x2_c, y2_c],
                "score": score,
                "crop": crop_pil,
                "white_bg_crop": white_bg_crop_pil,
                "normalized_box": [
                    (x1_c + x2_c) / (2 * W),  # центр x
                    (y1_c + y2_c) / (2 * H),  # центр y
                    (x2_c - x1_c) / W,        # ширина
                    (y2_c - y1_c) / H          # высота
                ]
            })
            
        return objects, W, H
