# 👑 Eleição de Líder — Algoritmo do Fracão em Mininet & Dashboard Web

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Mininet](https://img.shields.io/badge/Mininet-Emulated%20Network-green.svg)](http://mininet.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-black.svg)](https://flask.palletsprojects.com/)
[![React](https://img.shields.io/badge/React-18.3-blue.svg)](https://react.dev/)

Projeto prático da disciplina de **Sistemas Distribuídos**: implementação do **Algoritmo do Fracão** (variação do *Bully* / Valentão) com **5 processos** comunicando-se via **UDP** sobre uma rede emulada no **Mininet**. Inclui detecção de falhas por *heartbeat*, auditoria automatizada de logs e uma **interface web interativa em tempo real** (Flask + React) com inspeção em nível de Sistema Operacional.

---

## 📌 Sumário
- [1. Visão Geral e Algoritmo](#1-visão-geral-e-algoritmo)
- [2. Diferença Crucial: Crash (Simulado) vs. Kill (Real)](#2-diferença-crucial-crash-simulado-vs-kill-real)
- [3. Estrutura do Repositório](#3-estrutura-do-repositório)
- [4. Pré-requisitos e Instalação](#4-pré-requisitos-e-instalação)
- [5. Como Executar (Passo a Passo)](#5-como-executar-passo-a-passo)
- [6. Comandos Interativos do CLI](#6-comandos-interativos-do-cli)
- [7. Visualização Web & Dashboard](#7-visualização-web--dashboard)
- [8. Verificação de Logs e Invariante](#8-verificação-de-logs-e-invariante)
- [9. Parâmetros de Tempo](#9-parâmetros-de-tempo)

---

## 1. Visão Geral e Algoritmo

O **Algoritmo do Fracão** é uma variação do clássico algoritmo do *Bully* (Valentão, Tanenbaum & van Steen) com a regra de prioridade invertida:
- **No Valentão:** o processo de **MAIOR ID** é eleito líder.
- **No Fracão:** o processo de **MENOR ID** é eleito líder (Ex: `p1` tem prioridade máxima sobre `p2`…`p5`).

### Tipos de Mensagens

| Mensagem | Descrição |
| :--- | :--- |
| `ELECTION` | Convocação de eleição, enviada **apenas a processos com ID menor**. |
| `OK` | Resposta: *"Estou vivo e tenho maior prioridade que você"*. |
| `COORDINATOR` | Anúncio público do novo líder eleito, enviado a todos os pares. |
| `HEARTBEAT` | Sinal de vida periódico enviado entre todos os nós vivos para detecção de falhas. |

### Ciclo de Vida da Eleição
```text
start_election():
    se NÃO existir nenhum processo ativo de ID menor que o meu:
        assumo a liderança imediatamente e envio COORDINATOR a todos
    senão:
        envio ELECTION a todos os nós de ID menor
        estado = ELECTING (aguardo OK até ELECTION_TIMEOUT)

ao receber ELECTION de q (ID maior):
    respondo OK ("tenho prioridade")
    se estado == NORMAL:
        inicio minha própria eleição

se ELECTION_TIMEOUT estourar sem receber nenhum OK:
    nenhum nó de menor ID está vivo -> assumo a liderança e anuncio COORDINATOR

ao receber COORDINATOR de q (ID menor):
    defino líder = q; estado = NORMAL

````

## 2. Diferença Crucial: Crash (Simulado) vs. Kill (Real)

Uma das principais contribuições deste projeto é demonstrar a diferença entre uma **falha no nível da aplicação** e uma **falha no nível do Sistema Operacional**:

Plaintext

```
               ┌──────────────────────────────────────────────────┐
               │           Host Mininet p1 (10.0.0.2)             │
               │                                                  │
               │   ┌──────────────────────────────────────────┐   │
               │   │      Processo Python (process.py)         │   │
               │   │      - PID: 14205                        │   │
               │   │      - Socket UDP: :5000 (Listening)     │   │
               │   └──────────────────────────────────────────┘   │
               │                         │                        │
               │  Pilha de Rede do Kernel Linux (Responde Ping)   │
               └──────────────────────────────────────────────────┘

```

| **Funcionalidade**         | **Queda Simulada (crash p1)   PY**                       | **Falha Real (kill p1)   PY**                          |                      |      |
| -------------------------- | -------------------------------------------------------- | ------------------------------------------------------ | -------------------- | ---- |
| **Ação**                   | Executa `node.crash()` via mensagem Trigger UDP.   <br>  | Envia `SIGKILL` no Linux via Mininet.   <br>           |                      |      |
| **Processo Python**        | Continua em execução no SO (PID ativo).   <br>           | **Encerrado completamente (Sem PID)**.                 |                      |      |
| **Socket UDP (`:5000`)**   | **Aberto** (o programa apenas ignora os pacotes).   <br> | **Fechado** (Porta liberada no SO).                    |                      |      |
| **Comando de Restauração** | **`recover p1`**<br>                                     | <br>                                                   | **`restart p1`**<br> | <br> |
| **Ping no Host Mininet**   | Responde (Kernel do Linux ativo).                        | Responde (Host/Namespace do Linux ativo).              |                      |      |
| **Detector de Falhas**     | Remove da visão após `PEER_TIMEOUT` (silêncio).   <br>   | Remove da visão após `PEER_TIMEOUT` (silêncio).   <br> |                      |      |

## 3. Estrutura do Repositório

Plaintext

```
.
├── config.py             # Configurações de rede (IPs/portas) e parâmetros temporais
├── messages.py           # Dataclasses das mensagens e (de)serialização JSON
├── bully.py              # Máquina de estados do Fracão (lógica pura, desacoplada)
├── process.py            # Runtime do nó: socket UDP, thread ticker e logs
├── server.py             # Servidor injetor de comandos no canal de controle (porta 9000)
├── command.py            # CLI cliente para interagir com o server.py
├── mininet_topology.py   # Topologia Mininet (5 nós + srv), CLI estendido e runner da demo
├── check_logs.py         # Script de auditoria do invariante e linha do tempo dos logs
├── web_server.py         # Backend Flask (servidor estático e rotas da API)
├── web/                  # Frontend da interface gráfica
│   ├── index.html        # Estrutura base HTML
│   ├── styles.css        # Estilização, temas e layout CSS
│   ├── app.js            # Componente raiz <App/> e polling da API
│   └── components/       # Módulos React desacoplados
│       ├── constants.js  # Geometria e estilos de pacotes
│       ├── utils.js      # Mapeamento de eventos de log
│       ├── Packet.js     # Animação de envio de mensagens
│       ├── Graph.js      # Grafo interativo SVG dos nós
│       ├── NodeInspector.js # Painel de inspeção de SO e Rede
│       ├── Controls.js   # Painel de botões de controle
│       └── Feed.js       # Feed de mensagens em tempo real
├── logs/                 # Arquivos de log gerados em tempo de execução (*.log)
├── requirements.txt      # Dependências Python (Flask)
└── README.md             # Documentação do projeto

```

## 4. Pré-requisitos e Instalação

### Requisitos do Sistema

- **Sistema Operacional:** Linux (Ubuntu 22.04+, Debian, Fedora) com suporte a `sudo`.

- **Ferramentas de Rede:** Mininet, Open vSwitch (`ovs-vsctl`), Python 3.10+.




### Instalação das Dependências

Certifique-se de instalar o **Flask** no Python executado pelo `sudo` (utilizado pelo Mininet):

Bash

```
sudo python3 -m pip install flask --break-system-packages

```

## 5. Como Executar (Passo a Passo)

Sempre limpe a memória da rede emulada antes de iniciar uma nova instância:

Bash

```
sudo mn -c

```

### Opção A: CLI Interativo no Mininet

Para rodar a rede apenas via linha de comando:

Bash

```
sudo python3 mininet_topology.py

```

### Opção B: CLI + Visualização Web (Recomendado)

Para rodar o cluster e habilitar a interface gráfica interativa:

Bash

```
sudo python3 mininet_topology.py --web

```

> Abra no seu navegador: **`http://localhost:5001`**
>
>
>
>
>
>

### Opção C: Roteiro Automatizado de Testes (Demo)

Para executar a suíte de testes que simula quedas, recuperações e valida a eleição automaticamente:

Bash

```
# Executa a demo e abre o CLI no final
sudo python3 mininet_topology.py --web --demo

# Executa a demo e encerra imediatamente
sudo python3 mininet_topology.py --demo --no-cli

```

## 6. Comandos Interativos do CLI

Dentro do prompt do Mininet (`mininet>`), utilize os seguintes comandos estendidos:   

| **Comando**          | **Descrição**                                                                  |
| -------------------- | ------------------------------------------------------------------------------ |
| **`crash p1`**       | Simula a queda do processo `p1` (deixa de responder e para heartbeats).   <br> |
| **`recover p1`**     | Recupera o processo `p1` após um crash simulado.   <br>                        |
| **`kill p1`**        | Encerra o processo Python do `p1` de verdade no Linux (falha real).   <br>     |
| **`restart p1`**     | Inicia uma nova instância do processo `p1` após um `kill`.   <br>              |
| **`elect p4`**       | Força o nó `p4` a convocar uma eleição imediatamente.<br>             |
| **`status all`**     | Solicita que todos os processos escrevam seu estado atual no log.   <br>       |
| **`check`**          | Valida se todos os nós ativos concordam com o líder correto.   <br>            |
| **`check timeline`** | Exibe a linha do tempo completa de eventos extraída dos logs.   <br>           |

## 7. Visualização Web & Dashboard

A interface gráfica foi desenvolvida em React + SVG e oferece sincronização em tempo real (polling a cada 250ms) com o servidor Flask:   

1. **Grafo SVG Interativo:** Exibe a topologia circular. Nós desconectados afastam-se do anel e ficam com bordas tracejadas.

2. **Pacotes e Heartbeats:** Esferas coloridas animadas percorrem as arestas representando mensagens `ELECTION` (roxo), `OK` (azul), `COORDINATOR` (dourado) e `HEARTBEAT` (verde).

3. **Inspeção de SO e Rede (`NodeInspector`):** Ao clicar em qualquer nó, é exibido o seu estado detalhado na infraestrutura:

   - **Processo no SO:** Exibe o **PID real** alocado pelo kernel do Linux (ex: `PID: 14205`).

   - **Socket UDP:** Status da porta `:5000` (`Aberto / Listening` ou `Fechado / Porta Livre`).

   - **Canal de Controle:** Acessibilidade para mensagens Trigger.




4. **Feed de Mensagens com Filtros:** Lista com ajuste de visibilidade para Heartbeats, Mensagens de Eleição e Eventos de Ciclo de Vida (`CRASH` vs `KILLED`).




## 8. Verificação de Logs e Invariante

O projeto conta com o utilitário `check_logs.py` para auditoria dos arquivos gravados na pasta `logs/`:   

Bash

```
# Executável fora do Mininet para checar o resultado
python3 check_logs.py --timeline

```

### Invariante de Segurança

> **Todos os processos ATIVOS devem concordar que o líder é o processo ATIVO com o MENOR ID**.   
>
>
>

O script analisa os logs de cada processo, determina quais estão vivos e valida se a escolha de líder convergiu para o menor ID ativo no sistema.

## 9. Parâmetros de Tempo (`config.py`)

| **Parâmetro**         | **Valor** | **Descrição**                                                           |
| --------------------- | --------- | ----------------------------------------------------------------------- |
| `ELECTION_TIMEOUT`    | `1.0s`    | Tempo máximo de espera por respostas `OK` a uma convocação.   <br>      |
| `COORDINATOR_TIMEOUT` | `3.0s`    | Tempo de espera pelo anúncio `COORDINATOR` após receber um `OK`.   <br> |
| `HEARTBEAT_INTERVAL`  | `0.5s`    | Intervalo de transmissão dos sinais de vida entre os nós.   <br>        |
| `PEER_TIMEOUT`        | `2.0s`    | Tempo sem mensagens para considerar um nó inativo (`PEER_DOWN`).   <br> |
| `TICK_INTERVAL`       | `0.1s`    | Resolução do relógio interno (*ticker*) do processo.           |
