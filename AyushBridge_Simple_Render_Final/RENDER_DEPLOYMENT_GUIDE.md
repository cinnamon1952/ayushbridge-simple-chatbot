# AyushBridge Simple Chatbot - Render Deployment Guide

Deploy your lightweight AyushBridge AI chatbot on Render.com with **zero vector database dependencies**!

## 🚀 **Features of Simple Version**

- ✅ **No Vector Database**: Uses direct README.md content for context
- ✅ **DeepSeek R1 Model**: Free and powerful AI model via OpenRouter
- ✅ **Cloud Ready**: Optimized for Render.com deployment
- ✅ **Lightweight**: Only ~19KB deployment package
- ✅ **Fast Setup**: Deploy in under 5 minutes

## 📦 **What's Included**

| File | Description |
|------|-------------|
| `simple_app.py` | Flask web application (7KB) |
| `simple_chatbot.py` | Core chatbot logic without vector DB (9KB) |
| `requirements_simple.txt` | Minimal dependencies |
| `render.yaml` | Render deployment configuration |
| `runtime.txt` | Python version specification |
| `templates/simple_index.html` | Beautiful web interface (18KB) |
| `README.md` | Source content for chatbot knowledge (29KB) |

## 🔧 **Step-by-Step Deployment**

### **Step 1: Prepare Your Files**
1. Extract `AyushBridge_Simple_Render.zip`
2. You'll have all the files needed for deployment

### **Step 2: Get OpenRouter API Key**
1. Visit [OpenRouter.ai](https://openrouter.ai)
2. Sign up for a free account
3. Go to "Keys" section
4. Create a new API key (starts with `sk-or-v1-...`)

### **Step 3: Deploy on Render**

#### Option A: Deploy from GitHub (Recommended)
1. **Upload to GitHub**:
   ```bash
   # Create new repository on GitHub
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/ayushbridge-chatbot.git
   git push -u origin main
   ```

2. **Connect to Render**:
   - Go to [Render.com](https://render.com)
   - Sign up/Login
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect the `render.yaml` configuration

3. **Set Environment Variable**:
   - In Render dashboard, go to your service
   - Go to "Environment" tab
   - Add: `OPENROUTER_API_KEY` = `your_api_key_here`
   - Save and deploy

#### Option B: Deploy from ZIP
1. **Upload Files**:
   - Go to [Render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Choose "Deploy from Git" or "Upload"
   - Upload your files

2. **Configure Manually**:
   - **Build Command**: `pip install -r requirements_simple.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT simple_app:app`
   - **Environment Variables**:
     - `OPENROUTER_API_KEY`: `your_api_key_here`
     - `MODEL_NAME`: `deepseek/deepseek-r1`

### **Step 4: Test Your Deployment**
1. Render will provide a URL like: `https://your-app-name.onrender.com`
2. Visit the URL
3. Try asking: "What is AyushBridge?"
4. The chatbot should respond with information from your README.md!

## ⚙️ **Configuration Options**

### **Environment Variables**
| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | *Required* | Your OpenRouter API key |
| `MODEL_NAME` | `deepseek/deepseek-r1` | AI model to use |
| `FLASK_SECRET_KEY` | Auto-generated | Session security |
| `FLASK_DEBUG` | `False` | Debug mode |

### **Supported Models (OpenRouter)**
- `deepseek/deepseek-r1` ✅ (Free, recommended)
- `openai/gpt-3.5-turbo` (Paid)
- `anthropic/claude-3-haiku` (Paid)
- `meta-llama/llama-2-70b-chat` (Free)

## 🔧 **Customization**

### **Change the Knowledge Base**
Replace `README.md` with your own documentation:
```bash
# Replace README.md with your content
cp your-documentation.md README.md
# Redeploy
```

### **Modify the UI**
Edit `templates/simple_index.html`:
- Change colors in CSS variables
- Update branding and text
- Add new features

### **Switch AI Models**
Update environment variable:
```
MODEL_NAME=openai/gpt-4  # For better quality
MODEL_NAME=meta-llama/llama-2-70b-chat  # For free alternative
```

## 🐛 **Troubleshooting**

### **Common Issues**

1. **"Chatbot not available"**
   - Check OpenRouter API key is set correctly
   - Verify the API key is valid at openrouter.ai

2. **Slow responses**
   - DeepSeek R1 can be slower than GPT models
   - Consider upgrading to paid models for faster responses

3. **Deployment fails**
   - Check Python version is 3.10+ in `runtime.txt`
   - Verify all files are included in deployment

4. **Out of credits**
   - DeepSeek R1 is free but has rate limits
   - Add payment method on OpenRouter for unlimited usage

### **Logs and Debugging**
- Check Render logs in dashboard
- Look for error messages in "Logs" tab
- Health check endpoint: `https://your-app.onrender.com/health`

## 💰 **Costs**

### **Free Tier Limits**
- **Render**: 750 hours/month free (enough for small projects)
- **OpenRouter**: DeepSeek R1 model is completely free
- **Total**: $0/month for basic usage

### **Scaling Up**
- **Render Pro**: $7/month for better performance
- **OpenRouter Pro**: Pay per usage for premium models
- **Custom domain**: Free with Render

## 🚀 **Performance**

| Metric | Value |
|--------|--------|
| **Cold Start** | ~10-15 seconds |
| **Response Time** | 5-15 seconds (DeepSeek R1) |
| **Memory Usage** | ~50MB |
| **Deploy Time** | 2-3 minutes |

## 📈 **Next Steps**

After successful deployment:

1. **Custom Domain**: Add your own domain in Render
2. **Analytics**: Add Google Analytics to track usage
3. **Monitoring**: Set up uptime monitoring
4. **Scaling**: Upgrade to paid plan for better performance
5. **Features**: Add user authentication, conversation history, etc.

## 🎯 **Success Checklist**

- ✅ OpenRouter account created
- ✅ API key obtained
- ✅ Files uploaded to Render
- ✅ Environment variable set
- ✅ Deployment successful
- ✅ Chatbot responds to questions
- ✅ UI loads properly

## 🆘 **Support**

If you need help:
1. Check Render documentation
2. Review OpenRouter API docs
3. Check the logs for specific error messages
4. Ensure all environment variables are set correctly

**Happy deploying! 🎉**

---

*Your AyushBridge AI Assistant will be live on the internet, ready to help users understand your FHIR R4-compliant terminology microservice!*
