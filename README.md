# Fine-Tuning SegFormer-B2 for Semantic Segmentation

This project fine-tunes the SegFormer-B2 model using Hugging Face's `transformers` and `datasets` libraries for semantic segmentation tasks. The code handles preprocessing, dataset loading (in COCO format), custom metrics computation (IoU), and training using the `Trainer` API.

## Features

- Uses `SegformerForSemanticSegmentation` from Hugging Face
- Custom dataset preprocessing and label mapping
- Training with evaluation and metric logging
- Configurable hyperparameters

## Requirements

- Python 3.8+
- `transformers`
- `datasets`
- `evaluate`
- `torch`
- `PIL`

## Usage

1. Place your dataset in COCO format.
2. Update label mappings and paths in the script.
3. Run the training script:
   ```bash
   python finetuninng_segformer_b2.py
