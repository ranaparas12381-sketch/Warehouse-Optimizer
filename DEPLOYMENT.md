RENDER DEPLOYMENT GUIDE

This guide provides step by step instructions for deploying the Warehouse Optimization System on Render.

PREREQUISITES

* GitHub account
* Render account (free tier available at render.com)
* Git repository with this project

DEPLOYMENT STEPS

Step 1: Prepare Your Repository

Ensure your GitHub repository contains:
* render.yaml configuration file
* warehouse_openenv/Dockerfile
* warehouse_openenv/requirements.txt
* All project source code

Step 2: Connect to Render

1. Log in to your Render account at https://render.com
2. Click "New" button in the dashboard
3. Select "Web Service" from the dropdown menu

Step 3: Connect Repository

1. Click "Connect a repository" or use existing connection
2. Authorize Render to access your GitHub account if needed
3. Select the warehouse-optimization repository
4. Click "Connect"

Step 4: Configure Service

Render will automatically detect the render.yaml file. Verify the configuration:

* Name: warehouse-optimization
* Environment: Docker
* Region: Select closest to your target audience
* Branch: main (or your deployment branch)
* Plan: Free
* Dockerfile Path: ./warehouse_openenv/Dockerfile
* Docker Context: ./warehouse_openenv
* Root Directory: leave empty

Step 5: Deploy

1. Click "Create Web Service"
2. Render will begin building your Docker container
3. Monitor the build logs in real time
4. Wait for the deployment to complete (typically 5-10 minutes)

Step 6: Verify Deployment

1. Once deployed, Render provides a URL like: https://warehouse-optimization-xxxx.onrender.com
2. Click the URL to open your application
3. Verify the dashboard loads correctly
4. Test a simulation run to confirm functionality

HEALTH CHECK MONITORING

The application includes health check endpoints:

* Endpoint: /_stcore/health
* Interval: 30 seconds
* Timeout: 10 seconds
* Initial delay: 5 seconds
* Retries: 3

Render will automatically monitor application health and restart if needed.

ENVIRONMENT VARIABLES

The following environment variables are configured automatically via render.yaml:

* STREAMLIT_SERVER_PORT: 8501
* STREAMLIT_SERVER_ADDRESS: 0.0.0.0
* STREAMLIT_SERVER_HEADLESS: true
* STREAMLIT_BROWSER_GATHER_USAGE_STATS: false

No manual configuration required.

CUSTOM DOMAIN (OPTIONAL)

To use a custom domain:

1. Go to your service settings on Render
2. Click "Custom Domain" section
3. Add your domain name
4. Follow DNS configuration instructions provided by Render

UPDATING THE DEPLOYMENT

To update your deployed application:

1. Push changes to your GitHub repository
2. Render automatically detects changes
3. New build and deployment starts automatically
4. Zero downtime deployment with health checks

Or manually trigger deployment:

1. Go to your service dashboard on Render
2. Click "Manual Deploy"
3. Select "Deploy latest commit"

TROUBLESHOOTING

Build Fails

* Check Dockerfile syntax
* Verify requirements.txt has all dependencies
* Review build logs for specific error messages
* Ensure Python 3.11 compatibility

Application Not Starting

* Verify Streamlit is installed correctly
* Check that port 8501 is properly exposed
* Review application logs in Render dashboard
* Ensure health check endpoint is responding

Health Check Failures

* Verify Streamlit is running on correct port
* Check that /_stcore/health endpoint is accessible
* Review application logs for errors
* Ensure curl is installed in Docker image

COST CONSIDERATIONS

Free Tier Limitations:

* Service spins down after 15 minutes of inactivity
* Spin up time: 30-60 seconds on first request after idle
* 750 hours per month of runtime
* Suitable for hackathons and demonstrations

Upgrading to Paid Plan:

* No spin down behavior
* Always on service
* Better performance
* Custom scaling options

MONITORING AND LOGS

Access logs through Render dashboard:

1. Navigate to your service
2. Click "Logs" tab
3. View real time application logs
4. Use filters to search specific events
5. Download logs for offline analysis

SECURITY BEST PRACTICES

1. Never commit secrets or API keys to repository
2. Use Render environment variables for sensitive data
3. Enable XSRF protection (configured in .streamlit/config.toml)
4. Keep dependencies up to date
5. Monitor security advisories for Python packages

PERFORMANCE OPTIMIZATION

For better performance on free tier:

1. Minimize startup time by optimizing dependencies
2. Use caching where appropriate in Streamlit
3. Optimize data processing logic
4. Reduce image size in Dockerfile

SUPPORT AND RESOURCES

* Render Documentation: https://render.com/docs
* Streamlit Documentation: https://docs.streamlit.io
* Project Issues: Use GitHub issue tracker
* Community Support: Render community forums

QUICK REFERENCE COMMANDS

Local Testing Before Deployment:

# Build Docker image locally
docker build -t warehouse-optimization ./warehouse_openenv

# Run locally
docker run -p 8501:8501 warehouse-optimization

# Test with docker-compose
docker-compose up

Verify the application works locally before deploying to Render.

DEPLOYMENT CHECKLIST

Before deploying:
* All code committed and pushed to GitHub
* render.yaml is in repository root
* Dockerfile builds successfully locally
* Application runs correctly in Docker locally
* README and documentation are up to date
* No sensitive data in repository

After successful deployment:
* Test all features on deployed URL
* Verify health checks are passing
* Test with different simulation parameters
* Share the URL for hackathon submission

Your Warehouse Optimization System is now deployed and accessible globally via Render.
