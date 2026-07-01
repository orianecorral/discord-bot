FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Layer de dépendances séparé du code : rebuild plus rapide si seul le code change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Utilisateur non-root, mais propriétaire de /app pour pouvoir écrire gaming_bot.db
RUN useradd --create-home botuser && chown -R botuser:botuser /app
USER botuser

CMD ["python", "bot.py"]