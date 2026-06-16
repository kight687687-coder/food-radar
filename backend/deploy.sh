#!/bin/bash
set -e

# ===== 配置 =====
REMOTE="ubuntu@154.8.193.154"
REMOTE_DIR="/home/ubuntu/food-radar/backend"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "===== Food Radar 后端部署脚本 ====="
echo "目标服务器: $REMOTE:$REMOTE_DIR"
echo ""

# ── 1. tar 管道传输代码 ──
echo "[1/5] 传输代码到服务器..."
ssh -i ~/.ssh/id_rsa "$REMOTE" "rm -rf $REMOTE_DIR && mkdir -p $REMOTE_DIR"
tar -cf - --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' --exclude='data/models' -C "$LOCAL_DIR" . \
  | ssh -i ~/.ssh/id_rsa "$REMOTE" "tar -xf - -C $REMOTE_DIR"

# ── 2. 同步 .env（服务器必须有 .env 才能运行） ──
echo "[2/5] 同步环境配置..."
scp -i ~/.ssh/id_rsa "$LOCAL_DIR/.env" "$REMOTE:$REMOTE_DIR/.env"

# ── 3. 远程安装依赖 ──
echo "[3/5] 安装 Python 依赖..."
ssh -i ~/.ssh/id_rsa "$REMOTE" "cd $REMOTE_DIR && pip3 install -r requirements.txt"

# ── 4. 安装 systemd 服务 ──
echo "[4/5] 配置 systemd 服务..."
ssh -i ~/.ssh/id_rsa "$REMOTE" "sudo mkdir -p /var/log/food-radar && sudo chown ubuntu:ubuntu /var/log/food-radar"
ssh -i ~/.ssh/id_rsa "$REMOTE" "sudo cp $REMOTE_DIR/food-radar.service /etc/systemd/system/"
ssh -i ~/.ssh/id_rsa "$REMOTE" "sudo systemctl daemon-reload"
ssh -i ~/.ssh/id_rsa "$REMOTE" "sudo systemctl enable food-radar"
ssh -i ~/.ssh/id_rsa "$REMOTE" "sudo systemctl restart food-radar"

# ── 5. 检查状态 ──
echo "[5/5] 检查服务状态..."
sleep 2
ssh -i ~/.ssh/id_rsa "$REMOTE" "sudo systemctl status food-radar --no-pager"

echo ""
echo "===== 部署完成 ====="
echo "API地址: http://$REMOTE:5000"
echo "测试: curl http://$REMOTE:5000/health"
