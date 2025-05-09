# -*- coding: utf-8 -*-
"""Finetuninng Segformer-b2

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1WWPfIj-6abNRxOYvDTw8fuB7iWixFfLG
"""

pip install jsonlines

pip install requests pandas

import jsonlines

# Path to your NDJSON file
file_path = "/content/Export v2 project - Transparent bees - 10_23_2024.ndjson"

# Read NDJSON file
with jsonlines.open(file_path) as reader:
    data = [obj for obj in reader]  # Each line is stored as a dictionary

# Print the total number of images
print(f"Total number of images: {len(data)}")


import jsonlines

# Path to your NDJSON file
file_path = "/content/Export v2 project - Transparent bees - 10_23_2024.ndjson"

# Read NDJSON file
with jsonlines.open(file_path) as reader:
    data = [obj for obj in reader]  # Load all images

# Set to store unique label names
unique_labels = set()

# Loop through all images
for item in data:
    try:
        annotations = item['projects']['cm1j1ueis06co07xnaxj3cgsb']['labels'][0]['annotations']['objects']

        # Extract and add label names to the set
        for annotation in annotations:
            unique_labels.add(annotation['name'])  # Add label name (e.g., "wood", "bee")

    except KeyError:
        # Skip images without annotations
        continue

# Print all unique label names
print(f"Total unique labels: {len(unique_labels)}")
print("Label names:", unique_labels)




import requests
from PIL import Image
from io import BytesIO
import matplotlib.pyplot as plt

# Replace with your actual Labelbox API key
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJja3Bldjc4Z3IyMGhlMHlhYjh4eThiYXE4Iiwib3JnYW5pemF0aW9uSWQiOiJja3Bldjc4Z2cyMGhkMHlhYjZjcXFjZHU0IiwiYXBpS2V5SWQiOiJjbTVzN3NnZ2cwNHZzMDc1YTloMGZmcDg4Iiwic2VjcmV0IjoiNGQ5NWYwZWY3OGFhYjgyNTUzM2ExYjM0OWUxMGVlN2EiLCJpYXQiOjE3MzY2MDE2NTksImV4cCI6MjM2Nzc1MzY1OX0.u_nFDZEixOPuWlisWI2fc4uF_VT6Yb0r-wzYLVVYHVA"

# Set up headers for API-authenticated endpoints (for masks)
auth_headers = {
    "Authorization": f"Bearer {API_KEY}"
}

# Preassign fixed colors for the three labels:
# Wood   -> Red, Other -> Green, Comb  -> Blue.
preassigned_colors = {
    "Wood": (255, 0, 0),
    "Other": (0, 255, 0),
    "Comb": (0, 0, 255)
}

# Define the number of images to display (change this value to display first n images)
num_images = 1  # Change this value as desired

# Ensure num_images doesn't exceed available data length
num_images = min(num_images, len(data))

# Determine the grid size dynamically based on num_images
rows = (num_images + 4) // 5  # 5 images per row maximum
cols = min(num_images, 5)     # at most 5 columns

# Prepare the matplotlib figure with a dynamic grid
fig, axes = plt.subplots(nrows=rows, ncols=cols, figsize=(cols * 4, rows * 4))
axes = axes.flatten() if num_images > 1 else [axes]

# Loop over the first num_images
for idx, item in enumerate(data[:num_images]):
    image_index = idx + 1  # Adjust numbering to start at 1

    # --- Download the base image (no API key for pre-signed URLs) ---
    image_url = item['data_row']['row_data']
    response = requests.get(image_url)  # Pre-signed URL does not need extra headers
    if response.status_code != 200:
        print(f"Failed to download image {image_index}. Status code: {response.status_code}")
        continue
    base_img = Image.open(BytesIO(response.content)).convert("RGBA")

    # Create a transparent overlay for masks
    overlay = Image.new("RGBA", base_img.size, (255, 255, 255, 0))

    # --- Process annotations for this image ---
    annotations = item['projects']['cm1j1ueis06co07xnaxj3cgsb']['labels'][0]['annotations']['objects']
    for annotation in annotations:
        label_name = annotation['name']
        # Look up the fixed color for this label; if not found, fallback to white.
        color_rgb = preassigned_colors.get(label_name, (255, 255, 255))

        # Get the composite mask URL for this annotation
        composite_mask_url = annotation['mask']['url']

        # Download the composite mask image with the API key in the headers
        mask_response = requests.get(composite_mask_url, headers=auth_headers)
        if mask_response.status_code != 200:
            print(f"Failed to download mask for image {image_index} from {composite_mask_url}. Status code: {mask_response.status_code}")
            continue

        # Open the mask image and convert it to grayscale ("L")
        mask_img = Image.open(BytesIO(mask_response.content)).convert("L")

        # Resize mask if needed so that it matches the base image dimensions
        if mask_img.size != base_img.size:
            mask_img = mask_img.resize(base_img.size)

        # Create a colored version of the mask with a semi-transparent alpha (e.g., 100)
        colored_mask = Image.new("RGBA", base_img.size, color_rgb + (80,))

        # Overlay the colored mask on the transparent overlay using the grayscale mask as an alpha channel
        overlay.paste(colored_mask, (0, 0), mask=mask_img)

    # --- Combine the base image and the overlay ---
    combined = Image.alpha_composite(base_img, overlay)

    # --- Display the image in the corresponding subplot ---
    axes[idx].imshow(combined)
    axes[idx].axis("off")
    axes[idx].set_title(f"Image {image_index}")

# Adjust layout and display all images
plt.tight_layout()
plt.show()

pip install transformers datasets jsonlines torch torchvision



"""### original size"""

import jsonlines
import requests
from PIL import Image
from io import BytesIO
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from transformers import (
    SegformerImageProcessor,  # Using the new processor instead of the deprecated feature extractor
    SegformerForSemanticSegmentation,
    TrainingArguments,
    Trainer,
    default_data_collator,
)
import os
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
from transformers import TrainerCallback

# ------------------------- Step 1: Load NDJSON ----------------------------
def read_ndjson(file_path):
    with jsonlines.open(file_path) as reader:
        return [obj for obj in reader]

# ------------------------- Step 2: Convert to Semantic Map ----------------------------
def convert_to_semantic_mask(masks, labels, height, width):
    semantic_mask = torch.zeros((height, width), dtype=torch.int64)
    for mask, label in zip(masks, labels):
        semantic_mask[mask.bool()] = label
    return semantic_mask

# ------------------------- Step 3: Dataset Class ----------------------------
class SegFormerBeeDataset(Dataset):
    def __init__(self, data, api_key, image_processor, label_map, size=512):
        self.data = data
        self.api_key = api_key
        self.image_processor = image_processor
        self.label_map = label_map
        self.size = size

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        try:
            info = self.data[idx]
            image_url = info['data_row']['row_data']
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content)).convert('RGB')
            # Save original image size for upsampling predictions later
            original_width, original_height = image.size

            annotations = info['projects']['cm1j1ueis06co07xnaxj3cgsb']['labels'][0]['annotations']['objects']
            masks = []
            labels = []
            for annotation in annotations:
                mask_url = annotation['mask']['url']
                mask_resp = requests.get(mask_url, headers={"Authorization": f"Bearer {self.api_key}"})
                mask = Image.open(BytesIO(mask_resp.content)).convert('L')
                mask_arr = np.array(mask) == 255
                masks.append(torch.tensor(mask_arr, dtype=torch.uint8))
                labels.append(self.label_map[annotation['name']])

            # Skip sample if no masks are available
            if not masks:
                return None

            height, width = masks[0].shape
            masks = torch.stack(masks)
            semantic_mask = convert_to_semantic_mask(masks, labels, height, width)

            # Resize semantic mask to the desired size (for training)
            semantic_mask = Image.fromarray(semantic_mask.numpy().astype(np.uint8)).resize(
                (self.size, self.size), resample=Image.NEAREST
            )

            pixel_values = self.image_processor(images=image, return_tensors="pt").pixel_values.squeeze()
            labels_tensor = torch.from_numpy(np.array(semantic_mask)).long()

            return {
                "pixel_values": pixel_values,
                "labels": labels_tensor,
                "original_size": (original_width, original_height),  # For inference use only
                "original_image": image,  # For visualization during inference
            }
        except Exception as e:
            print(f"Skipping image at index {idx} due to error: {e}")
            return None

class PrintTrainingLossCallback(TrainerCallback):
    def on_log(self, args, state, control, logs=None, **kwargs):
        # This callback prints the training loss if available at the end of an epoch.
        if logs and "loss" in logs:
            print(f"Epoch {state.epoch}: Training Loss = {logs['loss']}")

# ------------------------- Custom Data Collator ----------------------------
def custom_data_collator(features):
    # Remove extra keys that are not expected by the model.
    filtered_features = []
    for feature in features:
        if feature is not None:
            # Only keep keys that are tensors for training.
            filtered_feature = {k: v for k, v in feature.items() if k in ["pixel_values", "labels"]}
            filtered_features.append(filtered_feature)
    return default_data_collator(filtered_features)

# ------------------------- Step 4: Training + Inference ----------------------------
def train_segformer_model(ndjson_path, api_key, data_fraction=1):
    """
    data_fraction: fraction of total data to use (e.g., 0.1 means 10% of the dataset)
    """
    label_map = {"Wood": 1, "Other": 2, "Comb": 3}  # 0 is reserved for background
    num_labels = len(label_map) + 1

    # Load and subset the dataset
    data = read_ndjson(ndjson_path)
    keep_count = max(1, int(len(data) * data_fraction))
    data = data[:keep_count]

    # Split the data into training and testing sets
    train_data, test_data = train_test_split(data, test_size=0.2, random_state=42)

    # Use the new image processor
    image_processor = SegformerImageProcessor(size=512, reduce_labels=False, do_resize=True, do_normalize=True)

    # Create dataset objects
    train_dataset = SegFormerBeeDataset(train_data, api_key, image_processor, label_map)
    test_dataset = SegFormerBeeDataset(test_data, api_key, image_processor, label_map)

    # Load model (note: the segmentation head is reinitialized to match our number of labels)
    model = SegformerForSemanticSegmentation.from_pretrained(
        "nvidia/segformer-b2-finetuned-ade-512-512",
        num_labels=num_labels,
        ignore_mismatched_sizes=True,
    )

    args = TrainingArguments(
        output_dir="./segformer_bee_output",
        per_device_train_batch_size=2,
        per_device_eval_batch_size=2,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        num_train_epochs=15,
        logging_dir="./logs",
        logging_strategy="epoch",  # Ensure logging happens per epoch
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        processing_class=image_processor,
        data_collator=custom_data_collator,
        callbacks=[PrintTrainingLossCallback()],
    )

    trainer.train()
    return model, test_dataset, image_processor

def show_predictions(model, dataset, image_processor, device='cpu', num_samples=3):
    model.eval()
    model.to(device)

    for i in range(num_samples):
        sample = dataset[i]
        if sample is None:
            continue

        input_tensor = sample["pixel_values"].unsqueeze(0).to(device)

        with torch.no_grad():
            outputs = model(input_tensor)
        preds = outputs.logits.argmax(dim=1).squeeze().cpu().numpy()

        # Upsample predictions to original image dimensions
        orig_w, orig_h = sample["original_size"]
        preds_upsampled = Image.fromarray(preds.astype(np.uint8)).resize(
            (orig_w, orig_h), resample=Image.NEAREST
        )
        mask_upsampled = Image.fromarray(sample["labels"].numpy().astype(np.uint8)).resize(
            (orig_w, orig_h), resample=Image.NEAREST
        )

        preds_upsampled = np.array(preds_upsampled)
        mask_upsampled = np.array(mask_upsampled)
        original_image = sample["original_image"]

        plt.figure(figsize=(15, 4))
        plt.subplot(1, 3, 1)
        plt.imshow(original_image)
        plt.title("Original Image")

        plt.subplot(1, 3, 2)
        plt.imshow(mask_upsampled)
        plt.title("Ground Truth (Original Size)")

        plt.subplot(1, 3, 3)
        plt.imshow(preds_upsampled)
        plt.title("Predicted (Original Size)")
        plt.show()

# ------------------------- Main ---------------------------------------

os.environ["WANDB_DISABLED"] = "true"

ndjson_path = "/content/Export v2 project - Transparent bees - 10_23_2024.ndjson"
api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJja3Bldjc4Z3IyMGhlMHlhYjh4eThiYXE4Iiwib3JnYW5pemF0aW9uSWQiOiJja3Bldjc4Z2cyMGhkMHlhYjZjcXFjZHU0IiwiYXBpS2V5SWQiOiJjbTVzN3NnZ2cwNHZzMDc1YTloMGZmcDg4Iiwic2VjcmV0IjoiNGQ5NWYwZWY3OGFhYjgyNTUzM2ExYjM0OWUxMGVlN2EiLCJpYXQiOjE3MzY2MDE2NTksImV4cCI6MjM2Nzc1MzY1OX0.u_nFDZEixOPuWlisWI2fc4uF_VT6Yb0r-wzYLVVYHVA"


# Load only 10% of the dataset by setting data_fraction=0.1
model, test_dataset, image_processor = train_segformer_model(
    ndjson_path, api_key, data_fraction=1
)

device = 'cuda' if torch.cuda.is_available() else 'cpu'
show_predictions(model, test_dataset, image_processor, device=device, num_samples=3)

model.save_pretrained("./segformer-custom-b2")
image_processor.save_pretrained("./segformer-custom-b2")

!zip -r segformer-custom-b2.zip ./segformer-custom-b2

!pip install git+https://github.com/lucasb-eyer/pydensecrf.git

import pydensecrf.densecrf as dcrf
from pydensecrf.utils import unary_from_softmax, create_pairwise_bilateral, create_pairwise_gaussian

def apply_crf(image, output_logits):
    h, w = image.shape[:2]
    n_classes = output_logits.shape[0]

    d = dcrf.DenseCRF2D(w, h, n_classes)

    # Convert softmax to unary potentials (log-probabilities)
    unary = unary_from_softmax(output_logits)  # shape: [n_classes, H*W]
    d.setUnaryEnergy(unary)

    # Pairwise terms (smoothness and appearance consistency)
    feats_gaussian = create_pairwise_gaussian(sdims=(3, 3), shape=(h, w))
    d.addPairwiseEnergy(feats_gaussian, compat=3)

    feats_bilateral = create_pairwise_bilateral(
        sdims=(50, 50), schan=(13, 13, 13),
        img=image, chdim=2
    )
    d.addPairwiseEnergy(feats_bilateral, compat=10)

    Q = d.inference(5)  # Run inference for 5 iterations
    return np.argmax(Q, axis=0).reshape((h, w))  # Final segmentation mask

def show_predictions_with_crf(model, dataset, image_processor, device='cpu', num_samples=3):
    model.eval()
    model.to(device)

    for i in range(num_samples):
        sample = dataset[i]
        if sample is None:
            continue

        input_tensor = sample["pixel_values"].unsqueeze(0).to(device)

        with torch.no_grad():
            outputs = model(input_tensor)

        logits = outputs.logits.squeeze().cpu().numpy()  # shape: [num_classes, H, W]
        softmax_output = torch.nn.functional.softmax(torch.tensor(logits), dim=0).numpy()

        raw_preds = softmax_output.argmax(axis=0)

        # Upsample to original size
        orig_w, orig_h = sample["original_size"]
        original_image = np.array(sample["original_image"])

        # Resize logits to original size for CRF
        upsampled_softmax = np.zeros((softmax_output.shape[0], orig_h, orig_w))
        for c in range(softmax_output.shape[0]):
            upsampled_softmax[c] = np.array(Image.fromarray(softmax_output[c]).resize((orig_w, orig_h), resample=Image.BILINEAR))

        crf_preds = apply_crf(original_image, upsampled_softmax)

        # Resize ground truth mask to original
        gt_mask = sample["labels"].numpy().astype(np.uint8)
        gt_mask_resized = np.array(Image.fromarray(gt_mask).resize((orig_w, orig_h), resample=Image.NEAREST))

        # Resize raw prediction for visualization
        raw_pred_resized = np.array(Image.fromarray(raw_preds.astype(np.uint8)).resize((orig_w, orig_h), resample=Image.NEAREST))

        # Plot all
        plt.figure(figsize=(20, 4))
        plt.subplot(1, 4, 1)
        plt.imshow(original_image)
        plt.title("Original Image")

        plt.subplot(1, 4, 2)
        plt.imshow(gt_mask_resized)
        plt.title("Ground Truth")

        plt.subplot(1, 4, 3)
        plt.imshow(raw_pred_resized)
        plt.title("Raw Prediction")

        plt.subplot(1, 4, 4)
        plt.imshow(crf_preds)
        plt.title("CRF Prediction")
        plt.show()

show_predictions_with_crf(model, test_dataset, image_processor, device=device, num_samples=3)

def show_predictions_with_tta(model, dataset, image_processor, device='cpu', num_samples=3):
    model.eval()
    model.to(device)

    def horizontal_flip(img_tensor):
        return torch.flip(img_tensor, dims=[-1])

    def reverse_horizontal_flip(mask_np):
        return np.fliplr(mask_np)

    for i in range(num_samples):
        sample = dataset[i]
        if sample is None:
            continue

        pixel_values = sample["pixel_values"].unsqueeze(0).to(device)

        # TTA: Original and flipped versions
        pixel_values_flipped = horizontal_flip(pixel_values)

        with torch.no_grad():
            output_orig = model(pixel_values)
            output_flip = model(pixel_values_flipped)

        # Reverse the flip for the flipped output
        logits_orig = output_orig.logits.squeeze().cpu().numpy()  # [C, H, W]
        logits_flip = output_flip.logits.squeeze().cpu().numpy()
        logits_flip = np.flip(logits_flip, axis=2)  # Flip back horizontally

        # Average logits and get prediction
        avg_logits = (logits_orig + logits_flip) / 2.0
        tta_preds = np.argmax(avg_logits, axis=0)

        # Raw prediction (no TTA)
        raw_preds = np.argmax(logits_orig, axis=0)

        # Resize everything to original image size
        orig_w, orig_h = sample["original_size"]
        original_image = np.array(sample["original_image"])

        raw_pred_resized = np.array(Image.fromarray(raw_preds.astype(np.uint8)).resize((orig_w, orig_h), resample=Image.NEAREST))
        tta_pred_resized = np.array(Image.fromarray(tta_preds.astype(np.uint8)).resize((orig_w, orig_h), resample=Image.NEAREST))
        gt_mask = np.array(Image.fromarray(sample["labels"].numpy().astype(np.uint8)).resize((orig_w, orig_h), resample=Image.NEAREST))

        # Plot results
        plt.figure(figsize=(20, 4))
        plt.subplot(1, 4, 1)
        plt.imshow(original_image)
        plt.title("Original Image")

        plt.subplot(1, 4, 2)
        plt.imshow(gt_mask)
        plt.title("Ground Truth")

        plt.subplot(1, 4, 3)
        plt.imshow(raw_pred_resized)
        plt.title("Raw Prediction")

        plt.subplot(1, 4, 4)
        plt.imshow(tta_pred_resized)
        plt.title("TTA Prediction (avg)")
        plt.show()



show_predictions_with_tta(model, test_dataset, image_processor, device=device, num_samples=3)

import pydensecrf.densecrf as dcrf
from pydensecrf.utils import unary_from_softmax, create_pairwise_bilateral, create_pairwise_gaussian

def apply_crf(image, softmax_output):
    h, w = image.shape[:2]
    n_classes = softmax_output.shape[0]

    d = dcrf.DenseCRF2D(w, h, n_classes)

    unary = unary_from_softmax(softmax_output)  # [C, H*W]
    d.setUnaryEnergy(unary)

    feats_gaussian = create_pairwise_gaussian(sdims=(3, 3), shape=(h, w))
    d.addPairwiseEnergy(feats_gaussian, compat=3)

    feats_bilateral = create_pairwise_bilateral(
        sdims=(50, 50), schan=(13, 13, 13),
        img=image, chdim=2
    )
    d.addPairwiseEnergy(feats_bilateral, compat=10)

    Q = d.inference(5)
    return np.argmax(Q, axis=0).reshape((h, w))

def show_predictions_with_tta_and_crf(model, dataset, image_processor, device='cpu', num_samples=3):
    model.eval()
    model.to(device)

    def horizontal_flip(img_tensor):
        return torch.flip(img_tensor, dims=[-1])

    for i in range(num_samples):
        sample = dataset[i]
        if sample is None:
            continue

        pixel_values = sample["pixel_values"].unsqueeze(0).to(device)
        pixel_values_flipped = horizontal_flip(pixel_values)

        with torch.no_grad():
            output_orig = model(pixel_values)
            output_flip = model(pixel_values_flipped)

        logits_orig = output_orig.logits.squeeze().cpu().numpy()  # [C, H, W]
        logits_flip = output_flip.logits.squeeze().cpu().numpy()
        logits_flip = np.flip(logits_flip, axis=2)  # Reverse horizontal flip

        avg_logits = (logits_orig + logits_flip) / 2.0
        softmax_output = torch.nn.functional.softmax(torch.tensor(avg_logits), dim=0).numpy()

        raw_preds = np.argmax(logits_orig, axis=0)
        tta_preds = np.argmax(avg_logits, axis=0)

        # Resize everything to original size
        orig_w, orig_h = sample["original_size"]
        original_image = np.array(sample["original_image"])

        # Resize logits for CRF (to original image size)
        upsampled_softmax = np.zeros((softmax_output.shape[0], orig_h, orig_w))
        for c in range(softmax_output.shape[0]):
            upsampled_softmax[c] = np.array(
                Image.fromarray(softmax_output[c]).resize((orig_w, orig_h), resample=Image.BILINEAR)
            )

        crf_pred = apply_crf(original_image, upsampled_softmax)

        raw_pred_resized = np.array(Image.fromarray(raw_preds.astype(np.uint8)).resize((orig_w, orig_h), resample=Image.NEAREST))
        tta_pred_resized = np.array(Image.fromarray(tta_preds.astype(np.uint8)).resize((orig_w, orig_h), resample=Image.NEAREST))
        gt_mask = np.array(Image.fromarray(sample["labels"].numpy().astype(np.uint8)).resize((orig_w, orig_h), resample=Image.NEAREST))

        # Plot
        plt.figure(figsize=(24, 4))
        plt.subplot(1, 5, 1)
        plt.imshow(original_image)
        plt.title("Original Image")

        plt.subplot(1, 5, 2)
        plt.imshow(gt_mask)
        plt.title("Ground Truth")

        plt.subplot(1, 5, 3)
        plt.imshow(raw_pred_resized)
        plt.title("Raw Prediction")

        plt.subplot(1, 5, 4)
        plt.imshow(tta_pred_resized)
        plt.title("TTA Prediction")

        plt.subplot(1, 5, 5)
        plt.imshow(crf_pred)
        plt.title("TTA + CRF Prediction")
        plt.show()

show_predictions_with_tta_and_crf(model, test_dataset, image_processor, device=device, num_samples=3)