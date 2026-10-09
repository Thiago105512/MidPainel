#!/bin/sh
# Restaura um backup da loja Tipiti (arquivo tipiti-AAAA-MM-DD-HHMM.tar.gz gerado por backup.sh).
#
# A LOJA PRECISA ESTAR PARADA durante a restauração.
#
# Docker (a partir de tipiti/deploy):
#   docker compose stop loja
#   docker compose run --rm --no-deps loja sh /app/deploy/restaurar.sh /backups/tipiti-2026-10-09-0315.tar.gz
#   docker compose start loja
#
# Servidor comum (systemd):
#   sudo systemctl stop tipiti
#   sudo -u tipiti env TIPITI_DB=/var/lib/tipiti/tipiti.db sh /opt/tipiti/repo/tipiti/deploy/restaurar.sh /var/backups/tipiti/tipiti-....tar.gz
#   sudo systemctl start tipiti
#
# Uso: restaurar.sh ARQUIVO.tar.gz [--sim]
#   --sim  não pergunta a confirmação (para scripts). Sem ele, pede que você digite SIM.
#
# O que acontece, nesta ordem (se qualquer passo falhar, nada do que está no ar é alterado):
#   1. o arquivo é aberto e conferido: só pode conter tipiti.db e a pasta fotos/ (nada de caminhos estranhos);
#   2. o banco do backup é extraído numa pasta temporária e passa pelo PRAGMA integrity_check;
#   3. o banco atual (se existir) é copiado com a API de backup do SQLite, e a pasta fotos atual é movida,
#      para <pasta do banco>/antes-da-restauracao-AAAA-MM-DD-HHMMSS/ — apague essa pasta quando estiver tudo certo;
#   4. o banco e as fotos do backup entram no lugar.
#
# Variáveis: TIPITI_DB (padrão ../data/tipiti.db, relativo a este script), PYTHON (padrão python3).
# Rode com o MESMO usuário da loja, para os arquivos restaurados ficarem com o dono certo.

set -eu
umask 077

erro() {
	echo "restaurar: ERRO: $*" >&2
	exit 1
}

[ "$#" -ge 1 ] || erro "uso: restaurar.sh ARQUIVO.tar.gz [--sim]"
ARQUIVO=$1
CONFIRMADO=nao
[ "${2:-}" = "--sim" ] && CONFIRMADO=sim
[ -f "$ARQUIVO" ] || erro "arquivo não encontrado: $ARQUIVO"
[ -r "$ARQUIVO" ] || erro "sem permissão de leitura: $ARQUIVO"

if [ -z "${PYTHON:-}" ]; then
	if command -v python3 >/dev/null 2>&1; then
		PYTHON=python3
	elif command -v python >/dev/null 2>&1; then
		PYTHON=python
	else
		erro "Python 3 não encontrado (defina PYTHON=/caminho/do/python3)"
	fi
fi

AQUI=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
DB=${TIPITI_DB:-$AQUI/../data/tipiti.db}
DADOS=$(dirname -- "$DB")
mkdir -p -- "$DADOS" || erro "não consegui criar a pasta $DADOS"
[ -w "$DADOS" ] || erro "sem permissão de escrita em $DADOS (rode com o usuário da loja)"

echo "restaurar: backup:  $ARQUIVO"
echo "restaurar: destino: $DB (e $DADOS/fotos)"
echo "restaurar: ATENÇÃO: a loja precisa estar PARADA. Pedidos feitos depois deste backup serão perdidos"
echo "           (o banco atual fica guardado em $DADOS/antes-da-restauracao-…)."
if [ "$CONFIRMADO" != sim ]; then
	if [ -t 0 ]; then
		printf 'Digite SIM para continuar: '
		read -r resposta || resposta=
		[ "$resposta" = SIM ] || erro "cancelado; nada foi alterado"
	else
		erro "sem terminal para confirmar; rode de novo com --sim no final"
	fi
fi

TRABALHO=$(mktemp -d "$DADOS/.restaurar-XXXXXX") || erro "não consegui criar pasta temporária em $DADOS"
trap 'rm -rf -- "$TRABALHO"' EXIT
trap 'exit 1' HUP INT TERM

"$PYTHON" - "$ARQUIVO" "$TRABALHO" "$DB" <<'PY'
import os
import shutil
import sqlite3
import sys
import tarfile
import time
from pathlib import Path, PurePosixPath

arquivo, trabalho, db = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
dados = db.parent


def falha(msg):
    sys.exit("restaurar: ERRO: " + msg + " — nada foi alterado")


# 1) confere o conteúdo antes de extrair qualquer coisa
try:
    tar = tarfile.open(arquivo, "r:gz")
    membros = tar.getmembers()
except (tarfile.TarError, OSError, EOFError) as e:
    falha(f"arquivo ilegível ou incompleto ({e})")
for m in membros:
    partes = PurePosixPath(m.name).parts
    seguro = (
        m.name and not m.name.startswith("/") and ".." not in partes
        and (m.isfile() or m.isdir())
        and (m.name == "tipiti.db" or partes[0] == "fotos")
    )
    if not seguro:
        falha(f"conteúdo inesperado no backup: {m.name!r}")
if [m.name for m in membros].count("tipiti.db") != 1:
    falha("o backup não contém o arquivo tipiti.db")

# 2) extrai na pasta temporária (mesmo disco do banco, para a troca final ser instantânea) e confere o banco
novo = trabalho / "novo"
novo.mkdir()
for m in membros:
    alvo = novo / m.name
    if m.isdir():
        alvo.mkdir(parents=True, exist_ok=True)
        continue
    alvo.parent.mkdir(parents=True, exist_ok=True)
    with tar.extractfile(m) as origem, open(alvo, "wb") as saida:
        shutil.copyfileobj(origem, saida)
tar.close()
(novo / "fotos").mkdir(exist_ok=True)

conn = sqlite3.connect((novo / "tipiti.db").as_uri() + "?mode=rw", uri=True)
try:
    resultado = [linha[0] for linha in conn.execute("PRAGMA integrity_check")]
    tabelas = {linha[0] for linha in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    pedidos = conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0] if "pedidos" in tabelas else 0
    produtos = conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] if "produtos" in tabelas else 0
except sqlite3.DatabaseError as e:
    falha(f"o tipiti.db do backup não é um banco SQLite válido ({e})")
finally:
    conn.close()
if resultado != ["ok"]:
    falha("o banco do backup falhou no integrity_check: " + "; ".join(resultado[:5]))
faltando = {"categorias", "produtos", "pedidos", "itens_pedido"} - tabelas
if faltando:
    falha("o banco do backup não parece ser da loja (faltam as tabelas %s)" % ", ".join(sorted(faltando)))
print(f"restaurar: backup conferido (integrity_check ok): {produtos} produtos, {pedidos} pedidos")

# 3) guarda o que está no ar hoje
guarda = dados / time.strftime("antes-da-restauracao-%Y-%m-%d-%H%M%S")
if db.exists() or (dados / "fotos").exists():
    guarda.mkdir()
    if db.exists():
        try:
            atual = sqlite3.connect(db.resolve().as_uri() + "?mode=rw", uri=True, timeout=30)
            copia = sqlite3.connect(guarda / "tipiti.db")
            try:
                atual.backup(copia)  # cópia consistente, inclusive do que estiver no -wal
                copia.execute("PRAGMA journal_mode = DELETE")
            finally:
                copia.close()
                atual.close()
        except sqlite3.DatabaseError as e:
            # banco atual danificado (talvez o motivo da restauração): guarda os arquivos como estão
            print(f"restaurar: aviso: o banco atual não pôde ser lido ({e}); guardando os arquivos brutos")
            (guarda / "tipiti.db").unlink(missing_ok=True)
            for sufixo in ("", "-wal", "-shm"):
                bruto = Path(str(db) + sufixo)
                if bruto.exists():
                    shutil.copy2(bruto, guarda / (db.name + sufixo))
    if (dados / "fotos").exists():
        os.replace(dados / "fotos", guarda / "fotos")
    print(f"restaurar: dados anteriores guardados em {guarda}")

# 4) troca: remove os arquivos auxiliares do banco antigo e põe o novo no lugar
for sufixo in ("-wal", "-shm", "-journal"):
    auxiliar = Path(str(db) + sufixo)
    if auxiliar.exists():
        auxiliar.unlink()
os.replace(novo / "tipiti.db", db)
os.replace(novo / "fotos", dados / "fotos")
print(f"restaurar: pronto — {db} e {dados / 'fotos'} restaurados. Agora inicie a loja de novo.")
PY
