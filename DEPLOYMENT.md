# Deployment Guide

This guide explains how to deploy the AI Agent to Render (or similar cloud platforms).

## Prerequisites

- Render account (or similar cloud platform)
- OpenAI API key
- Git repository (GitHub/GitLab)

## Deployment to Render

### Step 1: Prepare Repository

1. Ensure all files are committed to your Git repository
2. Push to GitHub/GitLab

### Step 2: Create Render Service

1. Log in to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your repository
4. Configure the service:
   - **Name**: `ai-agent`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && python manage.py migrate`
   - **Start Command**: `gunicorn app.wsgi:application`
   - **Plan**: Free tier (or paid for production)

### Step 3: Configure Environment Variables

Add these environment variables in Render dashboard:

```
DJANGO_SETTINGS_MODULE=app.settings
SECRET_KEY=<generate-a-secure-secret-key>
DEBUG=False
OPENAI_API_KEY=<your-openai-api-key>
JWT_SECRET_KEY=<generate-a-secure-jwt-secret>
ALLOWED_HOSTS=your-app-name.onrender.com
```

### Step 4: Create Database (Optional)

If using PostgreSQL:

1. In Render Dashboard, click "New +" → "PostgreSQL"
2. Name it `agent-db`
3. Copy the `DATABASE_URL` from the database settings
4. Add it as an environment variable in your web service

### Step 5: Deploy

1. Click "Create Web Service"
2. Render will build and deploy your application
3. Wait for deployment to complete
4. Your app will be available at `https://your-app-name.onrender.com`

## Post-Deployment Steps

### 1. Load CRM Data

Once deployed, you can load the CRM data via Django shell or management command:

```bash
# Via Render shell
python manage.py load_leads "path/to/Mock CRM leads for nurturing.xlsx"
```

### 2. Ingest Brochure Documents

Use the API endpoint to upload brochures:

```bash
curl -X POST https://your-app-name.onrender.com/api/documents/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@brochure.pdf"
```

### 3. Verify Deployment

- Check API docs: `https://your-app-name.onrender.com/api/docs`
- Test authentication: `POST /api/auth/login`
- Test query endpoint: `POST /api/query`

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Django secret key | Yes |
| `DEBUG` | Debug mode (False in production) | Yes |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts | Yes |
| `OPENAI_API_KEY` | OpenAI API key for LLM | Yes |
| `JWT_SECRET_KEY` | Secret key for JWT tokens | Yes |
| `DATABASE_URL` | PostgreSQL connection string (if using PostgreSQL) | Optional |
| `CHROMADB_PATH` | Path for ChromaDB storage | Optional |

## Troubleshooting

### Build Failures

- Check that all dependencies are in `requirements.txt`
- Verify Python version matches `runtime.txt`
- Check build logs in Render dashboard

### Runtime Errors

- Check application logs in Render dashboard
- Verify all environment variables are set
- Ensure database migrations have run

### Static Files Not Loading

- Run `python manage.py collectstatic` during build
- Verify `STATIC_ROOT` is set correctly
- Check WhiteNoise middleware is enabled

## Alternative Deployment Platforms

### Heroku

1. Create `Procfile` (already included)
2. Set environment variables
3. Deploy: `git push heroku main`

### Railway

1. Connect GitHub repository
2. Set environment variables
3. Railway auto-detects Django and deploys

### DigitalOcean App Platform

1. Connect repository
2. Configure build and run commands
3. Set environment variables
4. Deploy

## Production Checklist

- [ ] `DEBUG=False` in production
- [ ] Secure `SECRET_KEY` generated
- [ ] All environment variables set
- [ ] Database migrations run
- [ ] Static files collected
- [ ] HTTPS enabled (automatic on Render)
- [ ] CORS configured for frontend domain
- [ ] Error logging configured
- [ ] Monitoring set up (optional)

## Support

For issues or questions, refer to:
- Render Documentation: https://render.com/docs
- Django Deployment: https://docs.djangoproject.com/en/stable/howto/deployment/

