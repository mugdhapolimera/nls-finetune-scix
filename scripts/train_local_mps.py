#!/usr/bin/env python3
"""Train NLQT-Qwen3-1.7B on Apple Silicon using MLX.

Uses mlx-lm for native Apple Silicon LoRA fine-tuning with 4-bit quantization.
~3-5x faster than PyTorch MPS. Training takes ~30-60 min on M2 Pro 32GB.

Usage:
    # Full pipeline (build dataset + train + fuse + eval):
    python scripts/train_local_mps.py

    # Skip dataset build (if already built):
    python scripts/train_local_mps.py --skip-dataset-build

    # Custom settings:
    python scripts/train_local_mps.py --epochs 3 --batch-size 4

    # Use query format instead of intent format:
    python scripts/train_local_mps.py --format query

    # Push fused model to HuggingFace:
    python scripts/train_local_mps.py --push-to-hub adsabs/NLQT-Qwen3-1.7B-v2

Requirements:
    pip install mlx-lm
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def build_dataset(repo_root: Path, output_format: str, date: str, seed: int) -> None:
    """Run convert_to_intent_format.py + build_dataset.py."""
    print("\n" + "=" * 60)
    print("BUILDING DATASET")
    print("=" * 60)

    if output_format == "intent":
        intent_input = repo_root / "data/datasets/raw/gold_examples.json"
        intent_output = repo_root / "data/datasets/raw/gold_examples_intent.json"
        print("\nConverting to intent format...")
        subprocess.check_call([
            sys.executable, str(repo_root / "scripts/convert_to_intent_format.py"),
            "--input", str(intent_input),
            "--output", str(intent_output),
        ])
        gold_file = str(intent_output)
    else:
        gold_file = str(repo_root / "data/datasets/raw/gold_examples.json")

    cmd = [
        sys.executable, str(repo_root / "scripts/build_dataset.py"),
        "--gold", gold_file,
        "--output-dir", str(repo_root / "data/datasets/processed"),
        "--format", output_format,
        "--date", date,
        "--seed", str(seed),
    ]
    if output_format == "intent":
        cmd.append("--gold-only")

    subprocess.check_call(cmd)


def prepare_mlx_data(repo_root: Path, mlx_data_dir: Path) -> None:
    """Prepare data directory in mlx-lm expected format.

    mlx-lm expects a directory with train.jsonl and valid.jsonl,
    each line having a 'messages' field with chat format.
    Our build_dataset.py already produces this exact format.
    """
    mlx_data_dir.mkdir(parents=True, exist_ok=True)

    src_train = repo_root / "data/datasets/processed/train.jsonl"
    src_val = repo_root / "data/datasets/processed/val.jsonl"

    dst_train = mlx_data_dir / "train.jsonl"
    dst_valid = mlx_data_dir / "valid.jsonl"

    # Symlink to avoid copying
    for src, dst in [(src_train, dst_train), (src_val, dst_valid)]:
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        dst.symlink_to(src.resolve())

    # Count examples
    train_count = sum(1 for _ in open(src_train))
    val_count = sum(1 for _ in open(src_val))
    print(f"  Train: {train_count} examples")
    print(f"  Val:   {val_count} examples")


def run_eval(adapter_path: Path, model: str, train_file: Path, date: str) -> None:
    """Run quick eval on 10 test queries using mlx-lm generate."""
    from mlx_lm import generate, load

    print("\nLoading model + adapter for eval...")
    mlx_model, tokenizer = load(model, adapter_path=str(adapter_path))

    # Get system prompt from training data
    first_example = json.loads(open(train_file).readline())
    system_prompt = first_example["messages"][0]["content"]

    test_queries = [
        "papers about exoplanets published in 2023",
        "articles by John Smith on machine learning",
        "highly cited papers about dark matter",
        "recent gravitational wave detections in Nature",
        "Hawking radiation papers from the 1970s",
        "first author Tenenbaum on stellar oscillations",
        "papers NOT about cosmology by Perlmutter",
        "JWST observations of early galaxies 2022 to 2024",
        "refereed reviews about fast radio bursts",
        "papers citing the original LIGO detection paper",
    ]

    print(f"System prompt: {system_prompt[:80]}...\n")
    print("-" * 70)

    for query in test_queries:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Query: {query}\nDate: {date}"},
        ]
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
        )
        response = generate(
            mlx_model, tokenizer, prompt=prompt,
            max_tokens=256, verbose=False,
        )
        print(f"Input:  {query}")
        print(f"Output: {response}")
        print("-" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Train NLQT on Apple Silicon using MLX (native, ~3-5x faster than PyTorch MPS)"
    )
    parser.add_argument("--base-model", type=str, default="Qwen/Qwen3-1.7B",
                        help="Base model (HuggingFace repo or local path)")
    parser.add_argument("--output-dir", type=str, default="./output/NLQT-Qwen3-1.7B-v2",
                        help="Output directory for adapters and fused model")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=4,
                        help="Batch size (4 works well on M2 Pro 32GB with 4-bit)")
    parser.add_argument("--grad-accum", type=int, default=4,
                        help="Gradient accumulation steps (effective batch = batch-size * grad-accum)")
    parser.add_argument("--learning-rate", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--max-seq-length", type=int, default=512, help="Max sequence length")
    parser.add_argument("--num-lora-layers", type=int, default=16,
                        help="Number of layers to apply LoRA to (use -1 for all)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--format", type=str, choices=["query", "intent"], default="intent",
                        help="Training format")
    parser.add_argument("--date", type=str, default="2026-03-18",
                        help="Date for training examples")
    parser.add_argument("--skip-dataset-build", action="store_true",
                        help="Skip dataset build step")
    parser.add_argument("--skip-fuse", action="store_true",
                        help="Skip fusing adapter into base model")
    parser.add_argument("--skip-eval", action="store_true",
                        help="Skip evaluation step")
    parser.add_argument("--grad-checkpoint", action="store_true",
                        help="Use gradient checkpointing (saves memory, slightly slower)")
    parser.add_argument("--push-to-hub", type=str, default=None,
                        help="HuggingFace repo ID to upload fused model to")
    parser.add_argument("--mask-prompt", action="store_true", default=True,
                        help="Mask the prompt in loss (only train on assistant output, default: True)")
    args = parser.parse_args()

    # ── Check Apple Silicon ──
    import platform
    if platform.machine() != "arm64" or platform.system() != "Darwin":
        print("ERROR: This script requires Apple Silicon (arm64 macOS).")
        print("For CUDA GPUs, use scripts/train_1.7b_colab.ipynb or scripts/train_standalone.py")
        return 1

    try:
        import mlx
        import mlx_lm
    except ImportError:
        print("ERROR: mlx-lm not installed. Run: pip install mlx-lm")
        return 1

    print(f"Device: Apple {platform.processor()}")
    print(f"mlx-lm: {mlx_lm.__version__}")

    # ── Resolve paths ──
    repo_root = Path(__file__).parent.parent.resolve()
    sys.path.insert(0, str(repo_root / "packages/finetune/src"))
    output_dir = Path(args.output_dir)
    adapter_dir = output_dir / "adapters"
    fused_dir = output_dir / "fused"
    mlx_data_dir = output_dir / "mlx_data"

    print(f"Repo root: {repo_root}")
    print(f"Output: {output_dir}")

    train_file = repo_root / "data/datasets/processed/train.jsonl"
    val_file = repo_root / "data/datasets/processed/val.jsonl"

    # ── Build dataset ──
    if not args.skip_dataset_build:
        build_dataset(repo_root, args.format, args.date, args.seed)
    else:
        if not train_file.exists():
            print(f"ERROR: {train_file} not found. Remove --skip-dataset-build to generate it.")
            return 1
        print("Skipping dataset build (--skip-dataset-build)")

    # ── Prepare MLX data ──
    print("\n" + "=" * 60)
    print("PREPARING DATA")
    print("=" * 60)
    prepare_mlx_data(repo_root, mlx_data_dir)

    # ── Calculate iterations ──
    train_count = sum(1 for _ in open(train_file))
    steps_per_epoch = train_count // (args.batch_size * args.grad_accum)
    total_iters = steps_per_epoch * args.epochs

    print(f"\n  Steps/epoch: {steps_per_epoch}")
    print(f"  Total iterations: {total_iters}")
    print(f"  Effective batch: {args.batch_size} x {args.grad_accum} = {args.batch_size * args.grad_accum}")

    # ── Train with mlx_lm.lora ──
    print("\n" + "=" * 60)
    print(f"TRAINING: {args.base_model}")
    print("=" * 60)

    output_dir.mkdir(parents=True, exist_ok=True)

    lora_cmd = [
        sys.executable, "-m", "mlx_lm.lora",
        "--model", args.base_model,
        "--data", str(mlx_data_dir),
        "--train",
        "--iters", str(total_iters),
        "--batch-size", str(args.batch_size),
        "--grad-accumulation-steps", str(args.grad_accum),
        "--num-layers", str(args.num_lora_layers),
        "--learning-rate", str(args.learning_rate),
        "--max-seq-length", str(args.max_seq_length),
        "--adapter-path", str(adapter_dir),
        "--steps-per-report", "10",
        "--steps-per-eval", str(max(50, steps_per_epoch // 4)),
        "--save-every", str(max(100, steps_per_epoch)),
        "--val-batches", "25",
        "--seed", str(args.seed),
    ]

    if args.mask_prompt:
        lora_cmd.append("--mask-prompt")

    if args.grad_checkpoint:
        lora_cmd.append("--grad-checkpoint")

    print(f"  Model: {args.base_model}")
    print(f"  LoRA layers: {args.num_lora_layers}")
    print(f"  Batch: {args.batch_size} x {args.grad_accum}")
    print(f"  Iterations: {total_iters}")
    print(f"  LR: {args.learning_rate}")
    print(f"  Mask prompt: {args.mask_prompt}")
    print(f"  Estimated time: ~30-60 min on M2 Pro\n")

    start = time.time()
    subprocess.check_call(lora_cmd)
    elapsed = time.time() - start

    print(f"\nTraining complete in {elapsed / 60:.1f} minutes")
    print(f"Adapter saved to {adapter_dir}")

    # ── Eval with adapter ──
    if not args.skip_eval:
        print("\n" + "=" * 60)
        print("QUICK EVAL: 10 TEST QUERIES")
        print("=" * 60)
        run_eval(adapter_dir, args.base_model, train_file, args.date)

    # ── Fuse adapter into base model ──
    if not args.skip_fuse:
        print("\n" + "=" * 60)
        print("FUSING ADAPTER INTO BASE MODEL")
        print("=" * 60)

        fuse_cmd = [
            sys.executable, "-m", "mlx_lm.fuse",
            "--model", args.base_model,
            "--adapter-path", str(adapter_dir),
            "--save-path", str(fused_dir),
            "--dequantize",  # dequantize back to fp16 for deployment
        ]

        subprocess.check_call(fuse_cmd)
        print(f"Fused model saved to {fused_dir}")

        # ── Push to HuggingFace ──
        if args.push_to_hub:
            print(f"\nUploading to HuggingFace: {args.push_to_hub}...")
            fuse_upload_cmd = [
                sys.executable, "-m", "mlx_lm.fuse",
                "--model", args.base_model,
                "--adapter-path", str(adapter_dir),
                "--save-path", str(fused_dir),
                "--dequantize",
                "--upload-repo", args.push_to_hub,
            ]
            subprocess.check_call(fuse_upload_cmd)
            print(f"Uploaded to: https://huggingface.co/{args.push_to_hub}")
    else:
        print("Skipping fuse (--skip-fuse)")

    # ── Done ──
    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)
    print(f"\n  Adapter: {adapter_dir}")
    if not args.skip_fuse:
        print(f"  Fused model: {fused_dir}")
        print(f"\n  To upload to HuggingFace:")
        print(f"    huggingface-cli upload adsabs/NLQT-Qwen3-1.7B-v2 {fused_dir} .")
    print(f"\n  To test locally with mlx-lm:")
    print(f"    python -m mlx_lm.generate --model {fused_dir} --prompt 'Query: papers on dark matter'")
    print(f"\n  To test with the project server:")
    print(f"    cd docker && LLM_TIMEOUT=10 docker compose up")

    return 0


if __name__ == "__main__":
    exit(main())
