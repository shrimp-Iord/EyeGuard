"""One-time export of CLIP's image + text encoders to ONNX.

Run with the dev venv (which still has torch/transformers). Produces
models/clip_vision.onnx and models/clip_text.onnx so the runtime can score with
onnxruntime only — no PyTorch. Preprocessing/tokenization still use the SAME
transformers CLIPImageProcessor/CLIPTokenizer at runtime, so the embeddings
match the torch version and all tuned thresholds stay valid.
"""

import os
import torch
from pathlib import Path
from transformers import CLIPModel

MODEL_ID = "openai/clip-vit-base-patch32"
OUT = Path(__file__).resolve().parent.parent / "models"
OUT.mkdir(exist_ok=True)

m = CLIPModel.from_pretrained(MODEL_ID).eval()


class Vision(torch.nn.Module):
    def forward(self, pixel_values):
        return m.get_image_features(pixel_values=pixel_values)


class Text(torch.nn.Module):
    def forward(self, input_ids, attention_mask):
        return m.get_text_features(input_ids=input_ids,
                                   attention_mask=attention_mask)


print("exporting vision encoder…")
torch.onnx.export(
    Vision(), (torch.randn(2, 3, 224, 224),),
    str(OUT / "clip_vision.onnx"),
    input_names=["pixel_values"], output_names=["image_embeds"],
    dynamic_axes={"pixel_values": {0: "b"}, "image_embeds": {0: "b"}},
    opset_version=14, do_constant_folding=True)

print("exporting text encoder…")
torch.onnx.export(
    Text(), (torch.ones(2, 77, dtype=torch.long),
             torch.ones(2, 77, dtype=torch.long)),
    str(OUT / "clip_text.onnx"),
    input_names=["input_ids", "attention_mask"], output_names=["text_embeds"],
    dynamic_axes={"input_ids": {0: "b"}, "attention_mask": {0: "b"},
                  "text_embeds": {0: "b"}},
    opset_version=14, do_constant_folding=True)

# Save the learned logit_scale (a constant) so the runtime doesn't need the model.
import json
(OUT / "clip_meta.json").write_text(json.dumps(
    {"logit_scale": float(m.logit_scale.exp().item())}))

for f in ["clip_vision.onnx", "clip_text.onnx", "clip_meta.json"]:
    print(f"  {f}: {(OUT / f).stat().st_size/1e6:.1f} MB")
print("done")
