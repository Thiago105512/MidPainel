# Colocando a Tipiti no ar (tipiti.com.br)

Este guia leva a loja do seu computador para um servidor na internet, com HTTPS (cadeado) automático,
backup diário e atualização com um comando. Não precisa ser especialista: siga os passos na ordem.

```
 cliente ──HTTPS──▶ Caddy (portas 80/443) ──HTTP interno──▶ loja Python (porta 8000) ──▶ SQLite + fotos (/dados)
                    certificado automático                  não exposta na internet
```

Há dois jeitos de rodar. **Recomendado: Docker** (seções 1 a 6). Se preferir sem Docker, veja a seção 7.

Arquivos desta pasta:

| Arquivo | Para quê |
|---|---|
| `docker-compose.yml` | sobe a loja + o Caddy (HTTPS) |
| `Caddyfile` | configuração do Caddy na versão Docker |
| `.env.exemplo` | modelo das configurações (copie para `.env`) |
| `backup.sh` / `restaurar.sh` | backup e restauração do banco + fotos |
| `saude.py` | teste "a loja está no ar?" (usado pelo Docker e pelo CI) |
| `tipiti.service`, `tipiti-backup.service`, `tipiti-backup.timer`, `Caddyfile.servidor` | versão sem Docker (systemd) |
| `../Dockerfile`, `../.dockerignore` | como a imagem da loja é montada |

---

## 1. O que você precisa

1. **Um servidor (VPS)** com Ubuntu 24.04 ou Debian 12. Para começar, 1 vCPU, 1 GB de RAM e 20 GB de disco bastam
   (ex.: Hetzner, DigitalOcean, Vultr, Contabo, Magalu Cloud, Locaweb). Anote o **IP** dele (IPv4 e, se houver, IPv6).
2. **Docker** instalado pelo script oficial (o `docker.io` do apt costuma ser antigo demais):
   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker $USER     # depois saia e entre de novo no SSH
   docker compose version            # precisa mostrar v2 ou mais novo
   ```
3. **DNS do domínio** (no Registro.br, em "Editar zona", ou no painel onde o DNS está):

   | Nome | Tipo | Valor |
   |---|---|---|
   | `tipiti.com.br` (vazio/@) | A | IPv4 do servidor |
   | `www.tipiti.com.br` | A | IPv4 do servidor |
   | `tipiti.com.br` (vazio/@) | AAAA | IPv6 do servidor (só se o servidor tiver IPv6) |
   | `www.tipiti.com.br` | AAAA | IPv6 do servidor (só se tiver) |

   Não crie AAAA apontando para um IPv6 que não funciona: o Let's Encrypt usa o IPv6 quando existe e o certificado falha.
   Confira com `dig +short tipiti.com.br` e `dig +short www.tipiti.com.br` (pode levar algumas horas para propagar).
4. **Firewall** do provedor/servidor liberando as portas **22** (SSH), **80** e **443** (TCP) e **443 UDP** (HTTP/3).
   Com `ufw`: `sudo ufw allow OpenSSH && sudo ufw allow 80/tcp && sudo ufw allow 443 && sudo ufw enable`.

## 2. Primeiro deploy (Docker)

No servidor, pelo SSH:

```bash
# 1) baixar o código (o repositório inteiro; a loja fica na pasta tipiti/)
sudo mkdir -p /opt/tipiti && sudo chown $USER /opt/tipiti
git clone https://github.com/Thiago105512/MidPainel.git /opt/tipiti/repo
cd /opt/tipiti/repo/tipiti/deploy

# 2) configurar
cp .env.exemplo .env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # copie o token que aparecer
nano .env        # cole o token em TIPITI_ADMIN_TOKEN, preencha TIPITI_WHATSAPP; salve (Ctrl+O, Enter, Ctrl+X)
chmod 600 .env

# 3) pasta dos backups, com o dono que a loja usa dentro do contêiner (UID 10001)
mkdir -p backups && sudo chown 10001:10001 backups

# 4) subir
docker compose up -d --build
```

Se o repositório for privado, o `git clone` pede usuário e um *token* do GitHub (não a senha);
crie em GitHub → Settings → Developer settings → Fine-grained tokens, só com leitura deste repositório.

Pronto: em um ou dois minutos `https://tipiti.com.br` abre com cadeado, e `https://www.tipiti.com.br` redireciona para ele.
O painel fica em `https://tipiti.com.br/admin` (entre com o token do `.env`).

Na primeira vez a loja cria o banco com **produtos de demonstração** — tire-os do ar no painel (veja o checklist).

### Conferir

```bash
docker compose ps                        # "loja" deve aparecer como (healthy)
curl -I https://tipiti.com.br            # HTTP/2 200
curl -I https://www.tipiti.com.br        # 301 para https://tipiti.com.br/
```

## 3. Logs

```bash
cd /opt/tipiti/repo/tipiti/deploy
docker compose logs -f loja              # requisições e erros da loja (Ctrl+C para sair)
docker compose logs -f caddy             # acessos (JSON) e certificados HTTPS
docker compose logs --since 1h caddy | grep '"status":5'   # erros 5xx da última hora
```

Os logs são girados automaticamente (até 5 arquivos de 10 MB por serviço), para não lotar o disco.
O Caddy não grava o token do painel nos logs (o cabeçalho `Authorization` aparece como `REDACTED`).

## 4. Atualizar a loja

```bash
cd /opt/tipiti/repo/tipiti/deploy
docker compose exec -T loja sh /app/deploy/backup.sh     # backup antes, por garantia
git pull
docker compose up -d --build
docker compose ps                                        # espere ficar (healthy)
```

O banco e as fotos ficam no volume `dados` e **não** são apagados ao atualizar.
Mudou algo no `.env` (token, WhatsApp)? Rode `docker compose up -d` — o `docker compose restart` **não** relê o `.env`.

## 5. Backups

O `backup.sh` gera `tipiti-AAAA-MM-DD-HHMM.tar.gz` com o banco e as fotos. Ele usa a API de backup do SQLite
(cópia consistente mesmo com a loja recebendo pedidos — copiar o `tipiti.db` direto pode perder os dados que ainda estão
no arquivo `-wal`), confere a cópia com `PRAGMA integrity_check`, relê o `.tar.gz` inteiro e mantém os 14 mais recentes
(`TIPITI_BACKUP_MANTER` no `.env`). Se algo falhar, sai com erro e não deixa arquivo pela metade.

Os arquivos ficam em `/opt/tipiti/repo/tipiti/deploy/backups/`. No Docker, o horário do nome é UTC (Manaus = UTC−4).

### Backup na hora

```bash
cd /opt/tipiti/repo/tipiti/deploy
docker compose exec -T loja sh /app/deploy/backup.sh
ls -lh backups/
```

### Backup automático todo dia (escolha UM dos dois)

**a) cron** — `crontab -e` e acrescente a linha (todo dia às 03:15 no horário do servidor):

```cron
15 3 * * * cd /opt/tipiti/repo/tipiti/deploy && docker compose exec -T loja sh /app/deploy/backup.sh >> /opt/tipiti/backup.log 2>&1
```

**b) timer do systemd** — crie `/etc/systemd/system/tipiti-backup-docker.service`:

```ini
[Unit]
Description=Backup da loja Tipiti (Docker)
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
WorkingDirectory=/opt/tipiti/repo/tipiti/deploy
ExecStart=/usr/bin/docker compose exec -T loja sh /app/deploy/backup.sh
```

e `/etc/systemd/system/tipiti-backup-docker.timer`:

```ini
[Unit]
Description=Backup diário da loja Tipiti (Docker)

[Timer]
OnCalendar=*-*-* 03:15:00
RandomizedDelaySec=10min
Persistent=true

[Install]
WantedBy=timers.target
```

Ative: `sudo systemctl daemon-reload && sudo systemctl enable --now tipiti-backup-docker.timer`.
Confira: `systemctl list-timers tipiti-backup-docker.timer` e `journalctl -u tipiti-backup-docker`.

### Guarde uma cópia FORA do servidor

Backup que só existe no próprio servidor some junto com ele. Pelo menos uma vez por semana, copie a pasta `backups/`
para outro lugar — do seu computador:

```bash
scp -r usuario@IP-DO-SERVIDOR:/opt/tipiti/repo/tipiti/deploy/backups ./backups-tipiti
```

(ou automatize com `rclone` para Google Drive/Backblaze/S3). Os backups têm dados pessoais dos clientes (nome, CPF,
endereço): guarde-os em local protegido (LGPD).

### Restaurar um backup

```bash
cd /opt/tipiti/repo/tipiti/deploy
ls backups/                                              # escolha o arquivo
docker compose stop loja                                 # a loja PRECISA estar parada
docker compose run --rm --no-deps loja sh /app/deploy/restaurar.sh /backups/tipiti-2026-10-09-0315.tar.gz
docker compose start loja
```

O script confere o arquivo (conteúdo e `integrity_check`) **antes** de mexer em qualquer coisa, pede que você digite
`SIM`, guarda o banco e as fotos atuais em `/dados/antes-da-restauracao-…` e só então troca. Pedidos feitos depois do
backup escolhido deixam de aparecer (continuam na cópia guardada).

### Ensaio de restauração (faça uma vez por mês)

Um backup só vale se a restauração funciona. Teste sem tocar na loja no ar, num diretório separado:

```bash
cd /opt/tipiti/repo/tipiti/deploy
docker compose run --rm --no-deps -e TIPITI_DB=/tmp/ensaio/tipiti.db loja \
  sh -c 'sh /app/deploy/restaurar.sh "$(ls /backups/tipiti-*.tar.gz | tail -n 1)" --sim && ls -l /tmp/ensaio /tmp/ensaio/fotos'
```

Deve terminar com "pronto" e listar o `tipiti.db` e as fotos. (O `/tmp` do contêiner é descartado no fim.)

## 6. Detalhes técnicos (para quem for mexer)

- **IP do cliente.** Com `TIPITI_TRUST_PROXY=1` a loja usa o **último** valor de `X-Forwarded-For` para os limites de
  tentativas (pedidos, token errado). O Caddy **substitui** esse cabeçalho pelo IP de quem conectou
  (`header_up X-Forwarded-For {remote_host}`), descartando qualquer valor falso enviado pelo cliente — então o último
  (e único) valor é sempre o IP real. Isso só é seguro porque a porta 8000 **não** é publicada: ninguém fala com a loja
  sem passar pelo Caddy. Não acrescente `ports:` ao serviço `loja`. Se um dia usar Cloudflare/CDN na frente, troque por
  `{client_ip}` e configure `trusted_proxies` no Caddyfile, senão todos os clientes terão o IP da CDN.
- **Compressão.** A loja já comprime HTML/CSS/JS/JSON com gzip e calcula ETag por codificação; por isso o Caddyfile
  **não** usa `encode` (o Caddy repassa o gzip da loja e as respostas 304 continuam funcionando).
- **Tamanho das requisições.** A maior é o envio de foto (3 MB + miniatura de 400 KB, em base64 ≈ 4,6 MB).
  O Caddy recusa corpos acima de 6 MB (erro 413); a loja tem seus próprios limites, mais justos, por rota.
- **Tempos.** Cabeçalhos em até 10 s, corpo em até 2 min (upload pelo 4G). O Caddy reaproveita conexões com a loja
  por no máximo 4 s, porque a loja fecha conexões paradas após 5 s (evita erros 502 esporádicos).
- **Contêiner da loja.** Usuário sem privilégios (UID/GID 10001), sistema de arquivos só leitura (exceto `/dados`,
  `/backups` e `/tmp`), sem capabilities, `no-new-privileges`. Para trocar o volume `dados` por uma pasta do servidor,
  dê a posse antes: `sudo chown -R 10001:10001 pasta`.
- **Parada.** O contêiner para com SIGINT (`STOPSIGNAL`): a loja fecha na hora, sem esperar os 10 s do Docker.
- **Saúde.** `deploy/saude.py` faz `GET /api/loja` (que consulta o banco) e deve receber 200;
  `docker compose ps` mostra `(healthy)` ou `(unhealthy)`.
- **Outro domínio** (ex.: testar em `loja-teste.seudominio.com.br`): `TIPITI_DOMINIO` e `TIPITI_SITE_URL` no `.env`.
- **CI.** `.github/workflows/tipiti.yml` (na raiz do repositório) roda os testes em Python 3.10–3.13, confere a sintaxe
  do JavaScript, monta a imagem e faz um teste de fumaça (saúde, página inicial, backup/restauração, parada) a cada
  push/PR que mexa em `tipiti/`.

## 7. Alternativa sem Docker (systemd + Caddy do sistema)

Para um servidor Debian 12/Ubuntu 22.04+ (Python 3.10 ou mais novo, que já vem instalado).

```bash
# usuário da loja e pastas
sudo useradd --system --home-dir /var/lib/tipiti --shell /usr/sbin/nologin tipiti
sudo install -d -o tipiti -g tipiti -m 700 /var/backups/tipiti
sudo mkdir -p /opt/tipiti && sudo git clone https://github.com/Thiago105512/MidPainel.git /opt/tipiti/repo

# configuração (o modelo já vem com os caminhos desta seção: TIPITI_DB=/var/lib/tipiti/tipiti.db etc.)
sudo install -d -m 750 -g tipiti /etc/tipiti
sudo cp /opt/tipiti/repo/tipiti/deploy/.env.exemplo /etc/tipiti/tipiti.env
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
sudo nano /etc/tipiti/tipiti.env          # token, WhatsApp; deixe TIPITI_HOST=127.0.0.1
sudo chown root:tipiti /etc/tipiti/tipiti.env && sudo chmod 640 /etc/tipiti/tipiti.env

# serviço da loja + backup diário
cd /opt/tipiti/repo/tipiti
sudo cp deploy/tipiti.service deploy/tipiti-backup.service deploy/tipiti-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tipiti tipiti-backup.timer
systemctl status tipiti                   # active (running)
python3 deploy/saude.py                   # sem mensagem = ok

# Caddy (HTTPS) pelo repositório oficial: https://caddyserver.com/docs/install#debian-ubuntu-raspbian
sudo cp deploy/Caddyfile.servidor /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

- Logs: `journalctl -u tipiti -f` e `journalctl -u caddy -f`.
- Atualizar: `cd /opt/tipiti/repo && sudo git pull && sudo systemctl restart tipiti`.
- Backup na hora: `sudo systemctl start tipiti-backup.service`; os arquivos ficam em `/var/backups/tipiti`.
- Restaurar:
  ```bash
  sudo systemctl stop tipiti
  sudo -u tipiti env TIPITI_DB=/var/lib/tipiti/tipiti.db \
    sh /opt/tipiti/repo/tipiti/deploy/restaurar.sh /var/backups/tipiti/tipiti-2026-10-09-0315.tar.gz
  sudo systemctl start tipiti
  ```
- Rode backup e restauração **sempre como o usuário `tipiti`** (o timer já faz isso): se o root abrir o banco, os
  arquivos `-wal`/`-shm` podem ficar com dono root e a loja deixa de gravar pedidos.
- O serviço roda isolado: só escreve em `/var/lib/tipiti`, não vê `/home`, tem `/tmp` privado e não pode ganhar
  privilégios. Se mudar `TIPITI_DB` ou `TIPITI_BACKUP_DIR`, ajuste `ReadWritePaths` nos arquivos `.service`.

## 8. Checklist antes de abrir a loja

- [ ] `TIPITI_ADMIN_TOKEN` gerado com o comando do `.env.exemplo` e guardado num gerenciador de senhas
      (a loja nem sobe com o valor de exemplo).
- [ ] `https://tipiti.com.br` abre com cadeado; `www` redireciona; `http://` vira `https://`.
- [ ] Painel → Configurações: **WhatsApp** da loja (55 + DDD + número) e **chave Pix** corretos — teste o botão de
      WhatsApp e copie a chave Pix da página de confirmação para conferir.
- [ ] **Catálogo real** cadastrado (fotos, preços, custos, estoque, opções).
- [ ] **Produtos de demonstração** tirados do ar (Painel → Produtos → desmarcar "Produto no ar" em cada um).
- [ ] Frete e prazos revisados em `loja/frete.py` e `loja/config.py` (os valores atuais são de referência).
- [ ] **Pedido de ponta a ponta**: compre um produto pelo celular, confira o pedido no painel, o estoque baixando,
      a mensagem no WhatsApp e o cancelamento devolvendo o estoque.
- [ ] Backup automático ativo (`ls backups/` mostra o arquivo do dia seguinte) e cópia fora do servidor combinada.
- [ ] **Ensaio de restauração** feito (seção 5) — sem isso, você não sabe se o backup funciona.
- [ ] E-mail de contato (`TIPITI_EMAIL`) existe e alguém lê.
- [ ] Páginas de política de troca/privacidade revisadas (LGPD: a loja guarda nome, CPF, telefone e endereço).

## 9. Problemas comuns

| Sintoma | Causa provável e solução |
|---|---|
| `loja` reinicia sem parar; log diz "Defina TIPITI_ADMIN_TOKEN" ou "muito curto" | Token ausente ou com menos de 24 caracteres no `.env`. Corrija e `docker compose up -d`. |
| Site não abre / erro de certificado | DNS ainda não aponta para o servidor, AAAA errado, ou portas 80/443 fechadas. Veja `docker compose logs caddy`. |
| Erro 502 no site | A loja está parada ou reiniciando: `docker compose ps` e `docker compose logs loja`. |
| `backup: ERRO: sem permissão de escrita em /backups` | Faltou `sudo chown 10001:10001 backups` dentro de `tipiti/deploy`. |
| Erro 413 ao enviar foto | Foto acima do limite; o painel já reduz para 1200 px — tente outra foto ou outro navegador. |
| Disco cheio | `df -h`; apague backups antigos copiados para fora e rode `docker system prune` (não use `-a --volumes`!). |
| Mudou o `.env` e nada aconteceu | Use `docker compose up -d` (o `restart` não relê o `.env`). |

**Nunca rode** `docker compose down -v` nem `docker volume rm`: o `-v` apaga o volume com o banco e as fotos.
