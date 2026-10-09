#!/bin/sh
# Backup da loja Tipiti: banco SQLite + fotos em tipiti-AAAA-MM-DD-HHMM.tar.gz.
#
# Docker (a partir de tipiti/deploy):   docker compose exec -T loja sh /app/deploy/backup.sh
# Servidor comum (systemd):             sudo systemctl start tipiti-backup.service
#                                       (o tipiti-backup.timer já roda todo dia; veja LEIA-ME.md)
#
# Variáveis (todas opcionais):
#   TIPITI_DB              banco da loja (padrão: ../data/tipiti.db, relativo a este script)
#   TIPITI_BACKUP_DIR      onde guardar os backups (padrão: pasta "backups" ao lado do banco)
#   TIPITI_BACKUP_MANTER   quantos backups manter (padrão: 14); os mais antigos são apagados
#   PYTHON                 interpretador Python 3 (padrão: python3, ou python)
#
# Por que não copiar o arquivo .db? A loja usa o modo WAL: parte dos dados recentes fica em tipiti.db-wal
# e uma cópia simples do .db pode sair incompleta ou corrompida se um pedido for gravado no meio.
# Aqui usamos a API de backup online do SQLite, que gera uma cópia consistente com a loja no ar,
# e conferimos a cópia com "PRAGMA integrity_check" antes de guardá-la.
#
# Rode com o MESMO usuário da loja (no Docker isso já acontece): se outro usuário (ex.: root) abrir o banco,
# os arquivos -wal/-shm podem ficar com outro dono e a loja deixa de conseguir gravar.
#
# Sai com código diferente de 0 se algo der errado (o cron/systemd registram a falha).

set -eu
umask 077 # os backups têm dados pessoais dos clientes (nome, CPF, endereço): só o dono lê

erro() {
	echo "backup: ERRO: $*" >&2
	exit 1
}

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
DESTINO=${TIPITI_BACKUP_DIR:-$DADOS/backups}
MANTER=${TIPITI_BACKUP_MANTER:-14}

case $MANTER in
'' | *[!0-9]*) erro "TIPITI_BACKUP_MANTER deve ser um número inteiro (recebido: '$MANTER')" ;;
esac
[ "$MANTER" -ge 1 ] || erro "TIPITI_BACKUP_MANTER deve ser pelo menos 1"
[ -f "$DB" ] || erro "banco não encontrado: $DB (confira TIPITI_DB)"
mkdir -p -- "$DESTINO" 2>/dev/null || erro "não consegui criar a pasta de backups: $DESTINO"
[ -w "$DESTINO" ] || erro "sem permissão de escrita em $DESTINO (no Docker: sudo chown 10001:10001 tipiti/deploy/backups)"

CARIMBO=$(date +%Y-%m-%d-%H%M)
NOME="tipiti-$CARIMBO.tar.gz"
# dois backups no mesmo minuto: acrescenta os segundos (continua em ordem alfabética = cronológica)
[ ! -e "$DESTINO/$NOME" ] || NOME="tipiti-$CARIMBO$(date +%S).tar.gz"
[ ! -e "$DESTINO/$NOME" ] || erro "já existe $DESTINO/$NOME; tente de novo em alguns segundos"

# área de trabalho dentro da pasta de destino: o arquivo final chega lá com um "mv" (nunca pela metade)
TRABALHO=$(mktemp -d "$DESTINO/.backup-XXXXXX") || erro "não consegui criar pasta temporária em $DESTINO"
trap 'rm -rf -- "$TRABALHO"' EXIT
trap 'exit 1' HUP INT TERM

"$PYTHON" - "$DB" "$TRABALHO/tipiti.db" "$DADOS/fotos" "$TRABALHO/$NOME" <<'PY'
import os
import sqlite3
import sys
import tarfile
from pathlib import Path

origem, copia, fotos, arquivo = sys.argv[1:5]

# 1) cópia consistente do banco, com a loja no ar (mode=rw: nunca cria um banco vazio por engano)
src = sqlite3.connect(Path(origem).resolve().as_uri() + "?mode=rw", uri=True, timeout=30)
src.execute("PRAGMA busy_timeout = 30000")
dst = sqlite3.connect(copia)
try:
    src.backup(dst)  # inclui o que ainda está no -wal
finally:
    src.close()
# a cópia vira um arquivo único (sem -wal) e é conferida
dst.execute("PRAGMA journal_mode = DELETE")
resultado = [linha[0] for linha in dst.execute("PRAGMA integrity_check")]
if resultado != ["ok"]:
    sys.exit("backup: ERRO: a cópia do banco falhou no integrity_check: " + "; ".join(resultado[:5]))
tabelas = {linha[0] for linha in dst.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
faltando = {"categorias", "produtos", "pedidos", "itens_pedido"} - tabelas
if faltando:
    sys.exit("backup: ERRO: o banco não parece ser da loja (faltam as tabelas %s)" % ", ".join(sorted(faltando)))
produtos = dst.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
pedidos = dst.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
dst.close()

# 2) empacota banco + fotos
n_fotos = 0


def so_comuns(info):
    """Só pastas e arquivos comuns: links simbólicos, dispositivos etc. ficam de fora."""
    global n_fotos
    if info.isfile():
        n_fotos += 1
        return info
    return info if info.isdir() else None


with tarfile.open(arquivo, "w:gz", compresslevel=6) as tar:
    tar.add(copia, arcname="tipiti.db")
    if os.path.isdir(fotos) and not os.path.islink(fotos):
        tar.add(fotos, arcname="fotos", filter=so_comuns)

# 3) relê o arquivo inteiro: garante que o .tar.gz não está truncado e que o banco está lá
tamanho_db = os.path.getsize(copia)
with tarfile.open(arquivo, "r:gz") as tar:
    membros = tar.getmembers()
    banco = [m for m in membros if m.name == "tipiti.db"]
    if len(banco) != 1 or banco[0].size != tamanho_db:
        sys.exit("backup: ERRO: o arquivo gerado não contém o banco completo")
    for m in membros:
        if m.isfile():
            tar.extractfile(m).read()

print(f"backup: banco ok (integrity_check), {produtos} produtos, {pedidos} pedidos, {n_fotos} arquivos de foto")
PY

mv -- "$TRABALHO/$NOME" "$DESTINO/$NOME"
echo "backup: criado $DESTINO/$NOME ($(wc -c <"$DESTINO/$NOME" | tr -d ' ') bytes)"

# mantém só os $MANTER mais recentes (o nome tem a data, então a ordem alfabética é a cronológica)
set -- "$DESTINO"/tipiti-[0-9]*.tar.gz
if [ -e "$1" ] && [ "$#" -gt "$MANTER" ]; then
	excesso=$(($# - MANTER))
	while [ "$excesso" -gt 0 ]; do
		rm -f -- "$1"
		echo "backup: apagado o antigo $1"
		shift
		excesso=$((excesso - 1))
	done
fi
