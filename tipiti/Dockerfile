# Imagem de produção da loja Tipiti (https://tipiti.com.br).
# Só a biblioteca padrão do Python: não há "pip install".
#
#   docker build -t tipiti .                      (a partir da pasta tipiti/)
#   cd deploy && docker compose up -d --build     (jeito recomendado, com HTTPS pelo Caddy)
#
# Versão do Python fixada (patch + Debian) para o build ser reproduzível.
# Para atualizar: troque a tag, rode os testes (CI) e faça o deploy.
FROM python:3.12.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TIPITI_HOST=0.0.0.0 \
    TIPITI_PORT=8000 \
    TIPITI_DB=/dados/tipiti.db \
    TIPITI_TRUST_PROXY=1 \
    TIPITI_BACKUP_DIR=/backups

# Usuário sem privilégios com UID/GID fixos (10001): quem montar pastas do servidor em /dados ou /backups
# precisa dar a posse a esse número (ex.: sudo chown -R 10001:10001 backups).
RUN groupadd --system --gid 10001 tipiti \
 && useradd --system --uid 10001 --gid tipiti --home-dir /app --no-create-home --shell /usr/sbin/nologin tipiti \
 && mkdir -p /app /dados/fotos /backups \
 && chown -R tipiti:tipiti /dados /backups

WORKDIR /app

# O código fica com o dono root e só leitura para o usuário da loja: um invasor não consegue alterá-lo.
COPY loja/ /app/loja/
COPY static/ /app/static/
COPY deploy/backup.sh deploy/restaurar.sh deploy/saude.py /app/deploy/

USER tipiti

# Banco SQLite e fotos enviadas pelo painel (as fotos ficam em /dados/fotos, ao lado do banco).
# Declarado depois do chown: um volume novo herda o dono tipiti.
VOLUME ["/dados"]

EXPOSE 8000

# Saúde: /api/loja precisa responder 200 (usa só Python, sem curl).
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "/app/deploy/saude.py"]

# O servidor trata Ctrl+C (SIGINT) fechando o socket com calma. O SIGTERM padrão seria ignorado
# pelo processo 1 do contêiner e o Docker esperaria 10 s para matá-lo à força.
STOPSIGNAL SIGINT

CMD ["python", "-m", "loja"]
