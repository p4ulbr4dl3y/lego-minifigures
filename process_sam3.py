import os
import cv2
import numpy as np
from PIL import Image, ImageDraw
import mlx.core as mx
from mlx_vlm.utils import load_model, get_model_path
from mlx_vlm.models.sam3.generate import Sam3Predictor
from mlx_vlm.models.sam3.processing_sam3 import Sam3Processor

# --- CONFIGURATION ---
SAM3_MODEL_ID = "mlx-community/sam3-4bit"
PROMPT = "lego minifigure"
DETECTION_THRESHOLD = 0.5
OUTPUT_DIR = "sam3_results"

def process_image(image_path, predictor, output_dir):
    print(f"Processing {image_path}...")
    image_pil = Image.open(image_path).convert("RGB")
    W, H = image_pil.size
    
    result = predictor.predict(image_pil, text_prompt=PROMPT)
    num_objects = len(result.scores)
    print(f"  Found {num_objects} objects.")

    if num_objects == 0:
        return

    # Colors for visualization
    colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255), 
        (255, 255, 0), (255, 0, 255), (0, 255, 255)
    ]
    
    # 1. Create main image with overlays
    overlay_np = np.array(image_pil)
    crops = []
    
    for i in range(num_objects):
        box, mask = result.boxes[i], result.masks[i]
        x1, y1, x2, y2 = map(int, box)
        color = colors[i % len(colors)]
        
        # Mask processing
        mask_resized = np.array(Image.fromarray(mask.astype(np.float32)).resize((W, H), resample=Image.NEAREST)) > 0
        overlay_np[mask_resized] = (overlay_np[mask_resized] * 0.7 + np.array(color) * 0.3).astype(np.uint8)
        
        # Prepare crop for sidebar
        # Extract object with white background
        x1, y1, x2, y2 = max(0, x1), max(0, y1), min(W, x2), min(H, y2)
        obj_crop_pil = image_pil.crop((x1, y1, x2, y2))
        obj_crop_np = np.array(obj_crop_pil)
        
        # Get the corresponding part of the mask
        obj_mask = mask_resized[y1:y2, x1:x2]
        
        # Ensure mask and crop have the same shape for broadcasting
        # In case of off-by-one errors from cropping
        mh, mw = obj_mask.shape
        ch, cw, _ = obj_crop_np.shape
        final_h, final_w = min(mh, ch), min(mw, cw)
        
        obj_mask = obj_mask[:final_h, :final_w]
        obj_crop_np = obj_crop_np[:final_h, :final_w]
        bg = np.ones_like(obj_crop_np) * 255
        
        # Apply mask to keep only the object
        final_crop_np = np.where(obj_mask[..., None], obj_crop_np, bg)
        crops.append(Image.fromarray(final_crop_np))

    main_image_with_masks = Image.fromarray(overlay_np)
    draw = ImageDraw.Draw(main_image_with_masks)
    for i in range(num_objects):
        box = result.boxes[i]
        x1, y1, x2, y2 = map(int, box)
        color = colors[i % len(colors)]
        draw.rectangle([x1, y1, x2, y2], outline=color, width=2)

    # 2. Build adaptive grid
    CROP_SIZE = 200
    GAP = 10
    
    # Calculate how many rows/cols we can fit
    # We want Height_grid <= H
    # rows * (CROP_SIZE + GAP) <= H => rows = H // (CROP_SIZE + GAP)
    max_rows = max(1, H // (CROP_SIZE + GAP))
    cols = int(np.ceil(num_objects / max_rows))
    
    grid_w = cols * (CROP_SIZE + GAP) + GAP
    grid_h = H # Match image height
    
    canvas_w = W + grid_w
    canvas_h = H
    
    canvas = Image.new("RGB", (canvas_w, canvas_h), (240, 240, 240))
    canvas.paste(main_image_with_masks, (0, 0))
    
    for i, crop in enumerate(crops):
        col = i // max_rows
        row = i % max_rows
        
        # Resize crop to fit CROP_SIZE
        crop.thumbnail((CROP_SIZE, CROP_SIZE))
        
        # Center in its cell
        x_off = W + GAP + col * (CROP_SIZE + GAP) + (CROP_SIZE - crop.width) // 2
        y_off = GAP + row * (CROP_SIZE + GAP) + (CROP_SIZE - crop.height) // 2
        
        canvas.paste(crop, (x_off, y_off))

    base_name = os.path.basename(image_path)
    output_path = os.path.join(output_dir, f"grid_{base_name}")
    canvas.save(output_path)
    print(f"  Saved grid result to {output_path}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("Loading SAM3 model...")
    model_path = get_model_path(SAM3_MODEL_ID)
    sam_model = load_model(model_path)
    sam_processor = Sam3Processor.from_pretrained(str(model_path))
    predictor = Sam3Predictor(sam_model, sam_processor, score_threshold=DETECTION_THRESHOLD)

    image_extensions = (".jpg", ".jpeg", ".png", ".webp")
    images = [f for f in os.listdir(".") if f.lower().endswith(image_extensions)]
    
    for img_name in images:
        process_image(img_name, predictor, OUTPUT_DIR)
    
    print("Processing complete.")

if __name__ == "__main__":
    main()
