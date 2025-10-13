# GitHub Management Project

A comprehensive Django-based application for managing GitHub repositories, users, and automating GitHub-related tasks. This project provides a robust backend with GraphQL API, task scheduling with Celery, and secure deployment configurations.

## 🚀 Features

- **GitHub Integration**: Interact with GitHub's API to manage repositories and user data
- **Task Automation**: Schedule and manage background tasks with Celery
- **GraphQL API**: Flexible and efficient data querying with Graphene-Django
- **User Authentication**: Secure authentication system with JWT support
- **Background Processing**: Asynchronous task processing with Redis and Celery
- **REST API**: Traditional REST endpoints for compatibility
- **Deployment Ready**: Includes deployment scripts for production environments

  ---
  # Example of the screenshoot
  
<img width="2562" height="1662" alt="image" src="https://github.com/user-attachments/assets/cfa10b06-9bdb-4a84-bfb0-4528a077e514" />

## 🛠️ Tech Stack

- **Backend**: Django 5.1.6
- **Database**: PostgreSQL
- **Task Queue**: Celery with Redis as broker
- **Authentication**: JWT (JSON Web Tokens)
- **API**: GraphQL (Graphene-Django) & REST
- **Frontend**: (To be implemented or specify if exists)
- **Deployment**: Gunicorn, Nginx, Let's Encrypt

## 📦 Prerequisites

- Python 3.8+
- PostgreSQL
- Redis
- GitHub OAuth App credentials
- Virtual environment (recommended)

## 🚀 Getting Started

### Environment Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd RB
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with the following variables:
   ```env
   DEBUG=True
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=postgres://user:password@localhost:5432/dbname
   REDIS_URL=redis://localhost:6379/0
   GITHUB_ACCESS_TOKEN=your-github-token
   ```

### Database Setup

1. Create a PostgreSQL database
2. Run migrations:
   ```bash
   python manage.py migrate
   ```

### Running the Application

1. Start the development server:
   ```bash
   python manage.py runserver
   ```

2. Start Celery worker (in a new terminal):
   ```bash
   celery -A github_management_project worker -l info
   ```

3. Start Celery beat for scheduled tasks (in another terminal):
   ```bash
   celery -A github_management_project beat -l info
   ```

## 🔐 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DEBUG` | Enable debug mode | Yes |
| `SECRET_KEY` | Django secret key | Yes |
| `DATABASE_URL` | Database connection URL | Yes |
| `REDIS_URL` | Redis connection URL | Yes |
| `GITHUB_ACCESS_TOKEN` | GitHub personal access token | Yes |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts | Yes |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed origins | No |

## 🧪 Running Tests

```bash
python manage.py test
```

## 🚀 Deployment

### Production Setup

1. Set up a production-ready web server (Nginx recommended)
2. Configure Gunicorn as the application server
3. Set up SSL certificates (Let's Encrypt recommended)
4. Use the deployment script:
   ```bash
   sudo ./deploy_django.sh
   ```

### Environment Configuration

For production, ensure these settings are properly configured:
- `DEBUG=False`
- Proper `ALLOWED_HOSTS`
- Secure `SECRET_KEY`
- Production database settings
- Proper CORS configuration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- Django and the Django community
- Celery for task queue management
- All open-source libraries used in this project

## 📧 Contact


Project Link: [https://github.tarxemo.com](https://github.tarxemo.com)
