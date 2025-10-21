"""Simple Modal GPU test script that can be run from the command line"""
import modal

# Create a Modal app
app = modal.App("simple-gpu-test")

# Define the Modal image with GPU dependencies
gpu_image = modal.Image.debian_slim().pip_install(
    "torch>=2.0.0",
    "numpy"
)

# Define the GPU function
@app.function(
    gpu="T4",  # T4 is a good starter GPU, you can use "A10G", "A100", etc.
    image=gpu_image
)
def run_gpu_test():
    """Simple GPU test that prints GPU info and exits"""
    import torch  # type: ignore - installed in Modal container

    print("=" * 50)
    print("GPU Test Starting...")
    print("=" * 50)

    # Check if CUDA is available
    if torch.cuda.is_available():
        print(f"✓ CUDA is available!")
        print(f"✓ GPU Device: {torch.cuda.get_device_name(0)}")
        print(f"✓ Number of GPUs: {torch.cuda.device_count()}")
        print(f"✓ CUDA Version: {torch.version.cuda}")

        # Create a simple tensor on GPU
        x = torch.rand(1000, 1000).cuda()
        y = torch.rand(1000, 1000).cuda()
        z = x @ y  # Matrix multiplication on GPU

        print(f"✓ Successfully performed matrix multiplication on GPU")
        print(f"✓ Result shape: {z.shape}")
    else:
        print("✗ CUDA is not available")

    print("=" * 50)
    print("GPU Test Complete!")
    print("=" * 50)

    return "GPU test completed successfully!"


# Local entrypoint - this runs when you execute the script
@app.local_entrypoint()
def main():
    """Main entry point for command line execution"""
    print("Starting Modal GPU test...")
    result = run_gpu_test.remote()
    print(f"\nFinal result: {result}")
