import sys
from Quanti.uploader import upload_all_files
from utils import *
from ssh_manager import *


def main():
    print("🚀 Quanti Benchmark Runner")

    print("🛠️ [0/4] Parsing input arguments...")
    args = parse_args(sys.argv[1:])
    print(f"✅ Input parsed: LLM={args.llm}, Workload={args.workload}")

    try:
        print("📡 [1/4] Setting up server...")
        upload_all_files()
        print("✅ Server setup complete.")

        print("⚡ [2/4] Executing benchmark on server...")
        workload_basename = os.path.basename(args.workload)
        cmd = f"""ssh glg1 'cd ~/Quanti && source ~/vllm-env/bin/activate && python3 benchmark.py {args.llm} data/input/{workload_basename}'"""

        print(f"📝 Executing: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Benchmark completed successfully")
            print("📤 Server output:")
            print(result.stdout)

            print("📥 [3/4] Downloading results...")
            os.makedirs("./results", exist_ok=True)

            print("  📥 Downloading query results...")
            subprocess.run("scp -O 'glg1:~/Quanti/results/*' ./results/", shell=True)

            print("  📥 Downloading energy traces...")
            subprocess.run("scp -O 'glg1:~/Quanti/energy_traces/*' ./results/", shell=True)

            print("  📥 Downloading benchmark reports...")
            subprocess.run("scp -O 'glg1:~/Quanti/benchmark_report_*.json' ./results/", shell=True)

            print("  📋 Downloaded files:")
            subprocess.run("ls -la ./results/", shell=True)

            print("✅ Results downloaded to ./results/")
        else:
            print("❌ Benchmark failed")
            print("stdout:", result.stdout)
            print("stderr:", result.stderr)
            sys.exit(1)

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
