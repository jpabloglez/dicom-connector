# DICOM Connector

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat&logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-20.10%2B-blue?style=flat&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

Application for DICOM imaging pixel and metadata visualization. This tool provides a user-friendly interface for handling, viewing, and analyzing DICOM medical imaging files.

## Features

- DICOM file loading and parsing
- Pixel data visualization
- Metadata extraction and display
- Network DICOM transfer support
- Database storage for DICOM metadata
- User-friendly GUI interface

## Project Structure

```
dicom_app/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── main.py
├── config.py
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   └── file_viewer.py
├── dicom/
│   ├── __init__.py
│   ├── file_handler.py
│   └── network.py
└── database/
    ├── __init__.py
    └── db_handler.py
```

## Prerequisites

- Python 3.9 or higher
- Docker 20.10 or higher
- Docker Compose 2.0 or higher

## Installation

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/dicom-connector.git
cd dicom-connector
```

2. Build and run the application using Docker Compose:
```bash
docker compose up --build
```

The application will be available at `http://localhost:8000`

### Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/dicom-connector.git
cd dicom-connector
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

4. Run the application:
```bash
python main.py
```

## Configuration

The application can be configured by modifying the `config.py` file or using environment variables:

```python
# config.py
DATABASE_URL = "postgresql://user:password@localhost:5432/dicom_db"
DICOM_PORT = 11112
DEBUG_MODE = False
```

Environment variables override the config file settings:
- `DICOM_DB_URL`: Database connection string
- `DICOM_PORT`: Port for DICOM network operations
- `DEBUG`: Enable debug mode

## Docker Configuration

The `docker-compose.yml` file includes the following services:

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
      - "11112:11112"
    environment:
      - DICOM_DB_URL=postgresql://user:password@db:5432/dicom_db
    depends_on:
      - db

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=dicom_db
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Usage

1. Launch the application
2. Use the File menu to open DICOM files or establish network connections
3. View image data and metadata in the main window
4. Use the toolbar for common operations like zoom, pan, and window/level adjustment

## Development

### Adding New Features

1. Create a new branch for your feature
2. Implement the feature following the project structure
3. Add tests in the appropriate test directory
4. Submit a pull request

### Running Tests

```bash
python -m pytest tests/
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- DICOM standard documentation
- PyDICOM library
- Contributors and maintainers

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.