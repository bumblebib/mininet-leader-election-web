# Eleição de Líder — Algoritmo do Fracão (menor ID vence)

Atividade de **Sistemas Distribuídos**: versão minimalista do algoritmo do
**Fracão**, para **5 processos**, sobre **UDP** emulado em **Mininet**, com uma
**visualização web em tempo real** (Flask + React).

O Fracão é a variação do algoritmo do Valentão (*Bully*, Tanenbaum & van Steen)
com a regra invertida: no Valentão vence o **maior** ID; no Fracão vence o
**menor** ID. Por isso o código usa o nome clássico `bully` (arquivo `bully.py`,
classe `BullyNode`), embora a prioridade seja a do Fracão.

Premissas do enunciado:

- não há falhas de canal (nenhuma mensagem se perde);
- há **falhas de processo** (fail-stop: o processo para de responder);
- há um **timeout** pela resposta de convocação de eleição;
- o líder que falhou, ao voltar, **volta a ser líder**;
- processos que falharam são **removidos** do sistema e os que se recuperam são **reinseridos**.

Este projeto é autocontido: não depende do multicast totalmente ordenado nem
da exclusão mútua feitos antes.

---

## 1. Como o algoritmo funciona

Cada processo `pN` tem ID `N`. **Menor ID = maior prioridade.**

### Mensagens

| Mensagem      | Significado |
|---------------|-------------|
| `ELECTION`    | convocação de eleição, enviada **só a processos de ID menor** |
| `OK`          | resposta: "estou vivo e tenho prioridade sobre você" |
| `COORDINATOR` | anúncio do novo líder, enviado a todos |
| `HEARTBEAT`   | sinal de vida (detector de falhas) |

### Estados

`NORMAL`, `ELECTING` (esperando `OK`), `WAIT_COORD` (recebeu `OK`, espera o
`COORDINATOR`) e `DEAD` (falhou).

### Eleição

```text
start_election():
    se não existe ninguém com ID menor: viro líder na hora e envio COORDINATOR a todos
    senão: envio ELECTION a todos os menores; estado = ELECTING; prazo = agora + ELECTION_TIMEOUT

ao receber ELECTION de q (ID maior): respondo OK; se estava NORMAL, começo minha própria eleição
ao receber OK (estando em ELECTING): estado = WAIT_COORD; prazo = agora + COORDINATOR_TIMEOUT
prazo de ELECTING estourou (nenhum OK): assumo a liderança e envio COORDINATOR a todos
prazo de WAIT_COORD estourou:           ninguém anunciou; começo nova eleição
ao receber COORDINATOR de q (ID menor): líder = q; estado = NORMAL