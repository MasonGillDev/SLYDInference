apt update
apt install -y build-essential gcc g++
apt install -y python3-dev
curl https://bootstrap.pypa.io/get-pip.py | python3
apt install python3.12-venv
python3 -m venv /opt/vllm-env
source /opt/vllm-env/bin/activate
pip install torch vllm

python -m vllm.entrypoints.openai.api_server \
    --model HuggingFaceTB/SmolLM3-3B \
    --port 5002 \
    --max-num-seqs 32 \
    --gpu-memory-utilization 0.7