# Deployment Guide — Crypto News Pipeline

This guide covers provisioning a new Linux VPS from scratch through to a running pipeline instance using Docker and GitHub Actions CI/CD.

## Prerequisites

- Linux VPS (Ubuntu 22.04+ or Debian 12+ recommended)
- Root or sudo access
- Git installed on the VPS (for initial clone)
- Docker Hub account (free tier)
- GitHub repository with push access

## VPS Initial Setup

Update apt and install Docker Engine:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

Add your deploy user to the docker group (log out and back in after):

```bash
sudo usermod -aG docker $USER
```

Verify installation:

```bash
docker --version
docker compose version
```

Clone the repository:

```bash
sudo git clone https://github.com/<YOUR_ORG>/crypto-news-pipeline.git /opt/crypto-news-pipeline
sudo chown -R $USER:$USER /opt/crypto-news-pipeline
```

## Directory Structure

```
/opt/crypto-news-pipeline/
├── docker-compose.yml
├── Dockerfile
├── entrypoint.sh
├── src/
├── data/
│   ├── .env            (create manually — chmod 600)
│   ├── sources.json    (create manually)
│   ├── logs/           (auto-created by entrypoint)
│   └── session/        (auto-created by entrypoint)
└── ...
```

## Files You Need to Create

### `.env`

Copy the template from `.env.example` to `/opt/crypto-news-pipeline/data/.env` and fill in all 8 required values:

```bash
cp /opt/crypto-news-pipeline/.env.example /opt/crypto-news-pipeline/data/.env
nano /opt/crypto-news-pipeline/data/.env
chmod 600 /opt/crypto-news-pipeline/data/.env
```

Required environment variables:

| Variable | Description |
|----------|-------------|
| `TELEGRAM_API_ID` | Numeric API ID from my.telegram.org |
| `TELEGRAM_API_HASH` | 32-character API hash from my.telegram.org |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather (format: `123456:ABCdef...`) |
| `ADMIN_CHAT_ID` | Your personal Telegram chat ID for approvals |
| `OPENROUTER_API_KEY` | API key from OpenRouter for AI processing |
| `BINANCE_SQUARE_API_KEY` | API key from Binance Square for publishing |
| `TELEGRAM_CHANNEL_ID` | Target public channel for approved posts |
| `SYSTEM_MODE` | `AUTO` or `MANUAL` startup mode |

### `sources.json`

Create `/opt/crypto-news-pipeline/data/sources.json` with your Telegram source channel configuration. Use `sources.default.json` in the repo as a template.

```bash
cp /opt/crypto-news-pipeline/sources.default.json /opt/crypto-news-pipeline/data/sources.json
nano /opt/crypto-news-pipeline/data/sources.json
```

## GitHub Secrets Configuration

Configure these 6 secrets in your GitHub repository: Settings → Secrets and variables → Actions.

| Secret | What It Is | How to Obtain |
|--------|------------|---------------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username | Sign up at hub.docker.com |
| `DOCKERHUB_TOKEN` | Docker Hub Personal Access Token | Docker Hub → Account Settings → Personal Access Tokens → New Token (scopes: Read, Write, Delete) |
| `SSH_HOST` | VPS IP address or hostname | Your VPS provider dashboard |
| `SSH_USER` | SSH username on the VPS | Typically `ubuntu`, `admin`, or `deploy` |
| `SSH_PRIVATE_KEY` | SSH private key for VPS access | Generate: `ssh-keygen -t ed25519 -f ~/.ssh/deploy_key` then `ssh-copy-id -i ~/.ssh/deploy_key.pub <SSH_USER>@<SSH_HOST>` |
| `SSH_KNOWN_HOSTS` | VPS host public key (optional, recommended) | Run: `ssh-keyscan <SSH_HOST>` and paste the output |

## First Deploy

1. Complete the VPS initial setup (Docker + repo clone).
2. Create `.env` and `sources.json` in the `data/` directory on the VPS.
3. Configure all 6 GitHub Secrets in the repository.
4. Push a version tag to trigger the CD pipeline:

```bash
git tag v1.0.0
git push origin v1.0.0
```

5. Monitor the pipeline: GitHub → Actions → CI/CD Pipeline workflow run.
6. The CD job will: build the Docker image, push to Docker Hub, SSH into the VPS, pull the image, and restart the container.

## Verification

SSH into the VPS and run:

```bash
docker ps
```

Expected output: container `crypto-news-pipeline` with status `Up` or `Healthy`.

Check startup logs:

```bash
docker compose logs --tail 50
```

Verify the entrypoint ran successfully:

```bash
docker compose logs | grep "Entrypoint validation passed"
```

## Troubleshooting

### Container Exits Immediately (Exit Code 1)

**Cause:** Missing `.env` keys or placeholder values (`your_*`). `src/config.py` raises `ConfigError`.

**Fix:** Check logs with `docker compose logs`. Ensure all 8 env vars in `data/.env` are filled with real values and `chmod 600` is set.

### Telegram Session Lost (Re-auth on Every Deploy)

**Cause:** `telegram.session` not persisted across container restarts.

**Fix:** Ensure `data/session/` directory exists on the host. The volume mount `./data/session:/app/session` in `docker-compose.yml` must resolve to an existing directory.

### SSH Host Key Verification Failed

**Cause:** Ephemeral GitHub Actions runner has no `known_hosts` entry.

**Fix:** Add the `SSH_KNOWN_HOSTS` secret, or configure `StrictHostKeyChecking=no` in the `appleboy/ssh-action` config.

### Health Check Shows Unhealthy

**Cause:** `pgrep` health check may fail if the process name doesn't match exactly.

**Fix:** Verify the container is running with `docker ps`. The health check is informational — `restart: unless-stopped` handles crashes automatically.

## Recovering Telegram Session

If the session file is lost or corrupt, you need to re-authenticate interactively:

```bash
cd /opt/crypto-news-pipeline
docker compose down
rm -f data/session/telegram.session
docker compose run --rm pipeline
```

The pipeline will prompt for your phone number and the OTP code sent via Telegram. After auth succeeds:

```bash
ls -la data/session/
docker compose up -d
```

## Updating

To deploy a new version:

```bash
git tag v1.1.0
git push origin v1.1.0
```

The CI/CD pipeline automatically builds, pushes, and deploys the new image to the VPS.

## Rolling Back

To roll back to a previous version:

1. SSH into the VPS
2. Stop the container: `docker compose down`
3. Edit `docker-compose.yml` to pin the previous image tag
4. Start the container: `docker compose up -d`
