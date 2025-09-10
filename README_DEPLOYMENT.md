# AyushBridge Simple Chatbot

A lightweight, cloud-ready AI chatbot for AyushBridge documentation. No vector database required!

## ✨ Features

- 🚀 **Cloud-ready**: Optimized for Render.com deployment
- 🆓 **Free AI Model**: Uses DeepSeek R1 via OpenRouter
- 📖 **Documentation-powered**: Answers questions from README.md
- 🎨 **Beautiful UI**: Modern, responsive web interface
- ⚡ **Fast deployment**: Live in under 5 minutes

## 🚀 Quick Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

### 1. Get OpenRouter API Key
- Visit [OpenRouter.ai](https://openrouter.ai)
- Sign up for free
- Get your API key

### 2. Deploy on Render
- Fork this repository
- Connect to Render.com
- Set environment variable: `OPENROUTER_API_KEY`
- Deploy!

## 📁 Project Structure

```
├── simple_app.py              # Flask web application
├── simple_chatbot.py          # Core chatbot logic
├── requirements_simple.txt    # Python dependencies
├── render.yaml                # Render deployment config
├── runtime.txt                # Python version
├── templates/
│   └── simple_index.html      # Web interface
├── README.md                  # AyushBridge documentation (knowledge source)
└── RENDER_DEPLOYMENT_GUIDE.md # Detailed deployment guide
```

## 🔧 Local Development

1. **Clone and setup**:
   ```bash
   git clone <this-repo>
   cd ayushbridge-simple-chatbot
   pip install -r requirements_simple.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENROUTER_API_KEY
   ```

3. **Run locally**:
   ```bash
   python simple_app.py
   # Visit http://localhost:5000
   ```

## 🌐 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key | ✅ Yes |
| `MODEL_NAME` | AI model (default: deepseek/deepseek-r1) | No |
| `FLASK_SECRET_KEY` | Session security key | No |

## 🎯 How It Works

1. **User asks question** → Web interface
2. **App searches README.md** → Finds relevant sections
3. **Sends to DeepSeek R1** → AI generates response
4. **Returns answer** → With context from docs

## 📊 Performance

- **Response time**: 5-15 seconds
- **Memory usage**: ~50MB
- **Cost**: $0 (free model + Render free tier)

## 🔗 Live Demo

Once deployed, your chatbot will be available at:
`https://your-app-name.onrender.com`

## 📚 Documentation

- [Detailed Deployment Guide](RENDER_DEPLOYMENT_GUIDE.md)
- [AyushBridge Docs](README.md)

## 🤝 Contributing

1. Fork the repository
2. Make your changes
3. Test locally
4. Submit a pull request

## 📄 License

MIT License - feel free to use for your own projects!

---

**Built with ❤️ for AyushBridge - FHIR R4-compliant terminology services**
