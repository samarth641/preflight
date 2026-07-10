"""Fine-tune Gemma as Preflight's AI Explanation Engine (Core Objective #10).

AMD / ROCm MI300X variant of finetune_gemma_explainer.py. Upload THIS file to
notebooks.amd.com along with explanation_train.jsonl (put the jsonl next to it).

Differences from the original (all because bitsandbytes 4-bit is unreliable on ROCm,
and the AMD notebook's egress is allowlisted through hf-mirror.com):
    1. HF_ENDPOINT is pointed at hf-mirror.com (huggingface.co is blocked on the box).
    2. MODEL_NAME uses the plain (non -bnb-4bit) repo so it loads in bf16.
    3. load_in_4bit=False  — you have ~51GB VRAM, no need for 4-bit; avoids the ROCm bnb bug.
    4. optim="adamw_torch" — the 8-bit optimizer needs bitsandbytes.
Everything else (dataset, prompt template, LoRA config, 3 epochs, gguf export, smoke
test) is unchanged from the team's original script.

Input:  explanation_train.jsonl (uploaded next to this file)
Output: ./gemma-explainer-adapter/        (LoRA adapter — small, portable)
        ./gemma-explainer-merged/         (merged 16-bit model, optional)
        ./gemma-explainer.gguf            (quantized, for llama.cpp serving — the wired artifact)

Steps on the AMD notebook:
    1. %pip install unsloth unsloth_zoo --no-deps
       %pip install trl==1.8.0 peft accelerate datasets --no-deps
    2. Upload explanation_train.jsonl next to this script
    3. Run this script top to bottom (or %run finetune_gemma_explainer_amd.py)
    4. Download gemma-explainer.gguf back to this repo at
       backend/app/core/explainers/artifacts/gemma-explainer.gguf
"""
from __future__ import annotations

import os

# --- AMD edit 1: egress on the box is allowlisted; huggingface.co is blocked, the mirror is not.
#     MUST be set before any huggingface_hub / unsloth import triggers a download.
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import json
from pathlib import Path

# --- AMD edit 2: plain repo (not -bnb-4bit) so it loads in bf16 without bitsandbytes.
MODEL_NAME = "unsloth/gemma-2-2b-it"
MAX_SEQ_LENGTH = 1024  # our examples are short; keep this small for speed
DATASET_PATH = Path("explanation_train.jsonl")  # uploaded alongside this script
ADAPTER_OUT = Path("gemma-explainer-adapter")
MERGED_OUT = Path("gemma-explainer-merged")
GGUF_OUT = "gemma-explainer.gguf"

# ---------------------------------------------------------------------------
# 1. Load model + tokenizer (bf16, LoRA-ready) via Unsloth
# ---------------------------------------------------------------------------
from unsloth import FastLanguageModel  # noqa: E402

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=None,  # auto-detect (bf16 on MI300X)
    # --- AMD edit 3: no 4-bit. ~51GB VRAM is plenty for a 2B model in bf16 + LoRA,
    #     and it avoids the ROCm bitsandbytes 4-bit NaN/decode bug.
    load_in_4bit=False,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0.0,  # 0 is optimized in Unsloth
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# ---------------------------------------------------------------------------
# 2. Load + format the dataset as a single prompt string per example
# ---------------------------------------------------------------------------
from datasets import Dataset  # noqa: E402

PROMPT_TEMPLATE = """<start_of_turn>user
{instruction}

{input}<end_of_turn>
<start_of_turn>model
{output}<end_of_turn>"""


def load_examples(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            ex = json.loads(line)
            rows.append({"text": PROMPT_TEMPLATE.format(**ex)})
    return rows


rows = load_examples(DATASET_PATH)
print(f"loaded {len(rows)} training examples")
dataset = Dataset.from_list(rows)

# ---------------------------------------------------------------------------
# 3. Train (SFT via trl) — scoped for "a few hundred examples, finish today"
# ---------------------------------------------------------------------------
from trl import SFTTrainer, SFTConfig  # noqa: E402

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LENGTH,
    args=SFTConfig(
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        warmup_steps=10,
        num_train_epochs=3,
        learning_rate=2e-4,
        bf16=True,
        logging_steps=10,
        # --- AMD edit 4: adamw_8bit needs bitsandbytes; use the standard torch optimizer.
        optim="adamw_torch",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=42,
        output_dir="outputs",
        report_to="none",
    ),
)

trainer_stats = trainer.train()
print(trainer_stats)

# ---------------------------------------------------------------------------
# 4. Save — adapter (small, always) + merged/GGUF (optional, for easy serving)
# ---------------------------------------------------------------------------
model.save_pretrained(str(ADAPTER_OUT))
tokenizer.save_pretrained(str(ADAPTER_OUT))
print(f"saved LoRA adapter: {ADAPTER_OUT.resolve()}")

try:
    model.save_pretrained_merged(str(MERGED_OUT), tokenizer, save_method="merged_16bit")
    print(f"saved merged model: {MERGED_OUT.resolve()}")
except Exception as exc:  # noqa: BLE001
    print(f"merged save skipped ({exc}) — adapter alone is enough to serve")

try:
    model.save_pretrained_gguf(GGUF_OUT, tokenizer, quantization_method="q4_k_m")
    print(f"saved GGUF for llama.cpp: {GGUF_OUT}")
except Exception as exc:  # noqa: BLE001
    print(f"GGUF export skipped ({exc}) — not required, adapter/merged model still work")

# ---------------------------------------------------------------------------
# 5. Quick smoke test — same shape as backend/app/core/explainers will send
# ---------------------------------------------------------------------------
FastLanguageModel.for_inference(model)
sample_input = {
    "context": {"hardware": {"vram_usage_percent": 94}},
    "matched": [{
        "rule_id": "cuda-memory-fragmentation", "title": "Insufficient VRAM for Model Size",
        "category": "hardware", "confidence": 0.9, "priority": 8, "source": "NVIDIA CUDA Documentation",
    }],
}
test_prompt = PROMPT_TEMPLATE.format(
    instruction="You are Preflight's AI Explanation Engine. Given the matched training-analysis "
                "signals below, write a short, plain-language explanation of what's happening, "
                "why, and what to do about it. Follow this exact structure: an opening sentence, "
                "a 'because:' bullet list of reasons, a 'Recommended actions:' checklist, and an "
                "'Estimated impact:' line.",
    input=json.dumps(sample_input, indent=2),
    output="",
).rsplit("<end_of_turn>", 1)[0]  # strip trailing empty output turn for generation

inputs = tokenizer(test_prompt, return_tensors="pt").to(model.device)
out = model.generate(**inputs, max_new_tokens=200, temperature=0.3)
print("\n--- SMOKE TEST OUTPUT ---")
print(tokenizer.decode(out[0], skip_special_tokens=True))
