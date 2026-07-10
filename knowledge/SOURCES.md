# Knowledge sources & refresh notes (not loaded as rules).
# Last online refresh: 2026-07-10

pricing_and_availability:
  - name: cloud-gpus.com Price Analytics
    url: https://cloud-gpus.com/price-analytics/
    used_for: Median on-demand/spot rates (H100, H200, B200, MI300X, RTX 5090, L40S, …)
  - name: AIMultiple GPU Index
    url: https://aimultiple.com/gpu-index
    used_for: Cross-provider medians and ranges (B200/B300/MI300X/5090)
  - name: GetDeploying GPU catalog
    url: https://getdeploying.com/gpus
    used_for: Provider coverage and price bands
  - name: GPU Tracker
    url: https://gputracker.dev/gpu/rtx5090
    used_for: RTX 5090 marketplace floor/ceiling

hardware_specs:
  - name: AMD Instinct MI350 Series
    url: https://www.amd.com/en/products/accelerators/instinct/mi350.html
    used_for: MI350X/MI355X 288GB HBM3E, CDNA4
  - name: MI350X vs B200 analyses (2026)
    url: https://siliconanalysts.com/analysis/amd-vs-nvidia-ai-gpu-market-share-2026
    used_for: Spec table BF16/FP8, HBM, interconnect caveats

amd_cloud_ops:
  - name: Azure ND MI300X driver / ROCm image
    url: https://learn.microsoft.com/en-us/azure/virtual-machines/linux/azure-nd-mi300-series-amd-gpu-driver-linux-installation-guide
    used_for: Ubuntu 22.04 + ROCm 6.2.2 marketplace guidance
  - name: AMD Instinct on Azure
    url: https://instinct.docs.amd.com/projects/instinct-azure/latest/mi300x.html
    used_for: ND96isr_MI300X_v5 topology
  - name: ROCm system validation / RCCL
    url: https://rocm.docs.amd.com/en/latest/how-to/rocm-for-ai/system-setup/prerequisite-system-validation.html
    used_for: RCCL bandwidth pretest, clock determinism
  - name: TensorWave MI300X
    url: https://tensorwave.com/products/accelerators/amd-mi300x
    used_for: AMD-focused cloud node notes

fine_tuning_practice:
  - name: PEFT LoRA conceptual guide
    url: https://huggingface.co/docs/peft/conceptual_guides/lora
    used_for: Rank/alpha defaults
  - name: QLoRA / Unsloth 2026 practitioner guides
    url: https://huggingface.co/docs/peft
    used_for: r=16, alpha=2r, LR 2e-4, 1–3 epochs, all-linear targets
