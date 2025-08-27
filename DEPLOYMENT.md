# 🚀 Deployment Guide for Aria AI Concierge

This guide covers various deployment options from simple cloud platforms to enterprise Kubernetes.

## 🎯 Quick Deploy Options

### 1. Railway (Fastest - 2 minutes)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up

# Set environment variables in Railway dashboard
railway variables set OPENAI_API_KEY=your_key_here
```
**Cost:** $5/month starter plan  
**URL:** Automatic HTTPS domain provided

### 2. Render (Free tier available)
```bash
# Connect your GitHub repo to Render
# Use deploy/render.yaml configuration
# Add environment variables in Render dashboard
```
**Cost:** Free tier available, $7/month for paid  
**Features:** Auto-deploy from GitHub, managed databases

### 3. Google Cloud Run (Serverless)
```bash
# Build and deploy
gcloud run deploy aria-concierge \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

# Set environment variables
gcloud run services update aria-concierge \
  --set-env-vars OPENAI_API_KEY=your_key_here
```
**Cost:** Pay per request, very cost-effective  
**Features:** Auto-scaling, serverless

## 🐳 Docker Deployment

### Local Docker
```bash
# Build and run
docker build -t aria-concierge .
docker run -p 8000:8000 --env-file .env aria-concierge
```

### Docker Compose (Recommended for development)
```bash
# Run with SQLite
docker-compose up

# Run with PostgreSQL
docker-compose --profile with-db up

# Run with full stack (PostgreSQL + Redis)
docker-compose --profile with-db --profile with-cache up
```

### Docker Hub Deployment
```bash
# Build and push to Docker Hub
docker build -t yourusername/aria-concierge .
docker push yourusername/aria-concierge

# Deploy anywhere
docker run -p 8000:8000 yourusername/aria-concierge
```

## ☁️ Cloud Platform Specific

### AWS ECS/Fargate
```bash
# Create ECR repository
aws ecr create-repository --repository-name aria-concierge

# Build and push
docker build -t aria-concierge .
docker tag aria-concierge:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/aria-concierge:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/aria-concierge:latest

# Create ECS service (use AWS Console or Terraform)
```

### Azure Container Instances
```bash
# Create resource group
az group create --name aria-rg --location eastus

# Deploy container
az container create \
  --resource-group aria-rg \
  --name aria-concierge \
  --image yourusername/aria-concierge \
  --ports 8000 \
  --environment-variables OPENAI_API_KEY=your_key
```

### DigitalOcean App Platform
1. Connect your GitHub repository
2. Use `deploy/render.yaml` as configuration reference
3. Set environment variables in DO dashboard
4. Deploy automatically

## 🎛️ Kubernetes Deployment

### Local Kubernetes (minikube/kind)
```bash
# Apply deployment
kubectl apply -f deploy/k8s-deployment.yaml

# Create secrets
kubectl create secret generic aria-secrets \
  --from-literal=openai-api-key=your_key_here \
  --from-literal=database-url=your_db_url

# Port forward for testing
kubectl port-forward service/aria-concierge-service 8000:80
```

### Production Kubernetes
```bash
# Build and push image
docker build -t your-registry/aria-concierge:v1.0.0 .
docker push your-registry/aria-concierge:v1.0.0

# Update deployment image
kubectl set image deployment/aria-concierge aria-concierge=your-registry/aria-concierge:v1.0.0

# Scale deployment
kubectl scale deployment aria-concierge --replicas=5
```

## 🔧 Environment Configuration

### Required Environment Variables
```bash
# LLM API (choose one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Database (optional, defaults to SQLite)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Server configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
SECRET_KEY=your-secret-key
```

### Optional External APIs
```bash
# Enhanced functionality
GOOGLE_MAPS_API_KEY=your_google_key
YELP_API_KEY=your_yelp_key
AMADEUS_API_KEY=your_amadeus_key
AMADEUS_API_SECRET=your_amadeus_secret

# Email integration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

## 📊 Monitoring & Logging

### Health Checks
All deployments include health check endpoint:
```
GET /api/health
```

### Logging
Configure structured logging for production:
```python
# Add to your deployment
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Metrics (Optional)
Add Prometheus metrics:
```bash
pip install prometheus-client
# Implement metrics in your deployment
```

## 🔒 Security Considerations

### Production Checklist
- [ ] Set `DEBUG=false`
- [ ] Use strong `SECRET_KEY`
- [ ] Enable HTTPS/TLS
- [ ] Set up rate limiting
- [ ] Configure CORS properly
- [ ] Use environment variables for secrets
- [ ] Regular security updates
- [ ] Database connection encryption
- [ ] API key rotation policy

### Rate Limiting
```python
# Add to FastAPI app
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/chat")
@limiter.limit("10/minute")
async def chat(request: Request, message: ChatMessage):
    # ... existing code
```

## 💰 Cost Estimates

### Monthly Costs (USD)

| Platform | Free Tier | Paid Plan | Enterprise |
|----------|-----------|-----------|------------|
| Railway | - | $5+ | $20+ |
| Render | ✅ 750hrs | $7+ | $25+ |
| Google Cloud Run | ✅ 2M requests | $10+ | $50+ |
| Heroku | - | $7+ | $25+ |
| DigitalOcean | - | $12+ | $40+ |
| AWS ECS | - | $15+ | $100+ |

*Plus LLM API costs (OpenAI: ~$0.002/1K tokens)*

## 🚀 Recommended Deployment Path

1. **Development**: Local Docker Compose
2. **MVP/Testing**: Railway or Render (free tier)
3. **Production**: Google Cloud Run or DigitalOcean
4. **Enterprise**: Kubernetes on AWS/GCP/Azure

## 🆘 Troubleshooting

### Common Issues

**Port binding errors:**
```bash
# Check if port is in use
lsof -i :8000
# Use different port
PORT=8080 python run_server.py
```

**Memory issues:**
```bash
# Increase Docker memory limits
docker run -m 1g aria-concierge
```

**Database connection:**
```bash
# Check DATABASE_URL format
# SQLite: sqlite:///./data/aria.db
# PostgreSQL: postgresql://user:pass@host:5432/db
```

**API key issues:**
```bash
# Verify environment variables
echo $OPENAI_API_KEY
# Check .env file is loaded
```

## 📞 Support

For deployment issues:
1. Check the health endpoint: `/api/health`
2. Review application logs
3. Verify environment variables
4. Test with mock mode first (no API keys)
5. Open GitHub issue with deployment details

---

**Happy Deploying! 🚀**