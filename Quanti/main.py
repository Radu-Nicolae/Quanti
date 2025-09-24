import sys
from Quanti.uploader import upload_all_files
from utils import *
from ssh_manager import *


def main():
    print("🚀 Quanti Benchmark Runner")

    print("🛠️ [0/4] Parsing input arguments...")
    args = parse_args(sys.argv[1:])
    os.makedirs(args.output_dir, exist_ok=True)
    print(f"✅ Input parsed: LLM={args.llm}, Workload={args.workload}")

    try:
        print("📡 [1/4] Setting up server...")
        upload_all_files()
        print("✅ Server setup complete.")

        print("⚡ [2/4] Executing benchmark on server...")
        workload_basename = os.path.basename(args.workload)
        cmd = f"""ssh glg1 'cd ~/Quanti && source ~/vllm-env/bin/activate && python3 benchmark.py {args.llm} data/input/{workload_basename} {args.output_dir}'"""

        print(f"📝 Executing: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Benchmark completed successfully")
            print("📤 Server output:")
            print(result.stdout)
            print("📥 [3/4] Downloading results...")
            print(f"  📥 Downloading structured results to {args.output_dir}...")

            os.makedirs(args.output_dir, exist_ok=True)

            download_cmd = f"scp -O -r 'glg1:~/Quanti/{args.output_dir}/*' {args.output_dir}/"
            result = subprocess.run(download_cmd, shell=True, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✅ Results downloaded to {args.output_dir}/")
                print("  📋 Downloaded files:")
                subprocess.run(f"find {args.output_dir} -name '*.json' -o -name '*.csv' | head -10", shell=True)
            else:
                print(f"⚠️ Structured download failed: {result.stderr}")
                print("Check server output above for details")

    except KeyboardInterrupt:
        print("\n⚠️ Benchmark interrupted by user")
        cleanup_server()
        sys.exit(130)

    except Exception as e:
        print(f"\n❌ Benchmark failed with error: {e}")
        cleanup_server()
        sys.exit(1)

    finally:
        cleanup_server()


if __name__ == "__main__":
    main()
